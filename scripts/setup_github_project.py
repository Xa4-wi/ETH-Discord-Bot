#!/usr/bin/env python3
"""Create Cody's GitHub labels and development project with GitHub CLI."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
LABELS_FILE = PROJECT_ROOT / ".github" / "labels.json"
DEFAULT_OWNER = "Xa4-wi"
DEFAULT_REPOSITORY = "ETH-Discord-Bot"
DEFAULT_PROJECT_TITLE = "Cody Development"

PROJECT_DESCRIPTION = (
    "Features, bugs, backend integrations, and development tasks for Cody."
)
PROJECT_README = """# Cody Development

Track all ETH Discord Bot work here. Use repository labels for type, area,
priority, size, and blockers. Move work through Backlog, Todo, In Progress,
Review, and Done. See DEVELOPMENT.md in the repository for the complete
triage and board workflow.
"""

PROJECT_FIELDS = (
    ("Priority", "Critical,High,Medium,Low"),
    ("Effort", "Small,Medium,Large"),
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", default=DEFAULT_OWNER)
    parser.add_argument("--repository", default=DEFAULT_REPOSITORY)
    parser.add_argument("--title", default=DEFAULT_PROJECT_TITLE)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the planned GitHub CLI commands without changing GitHub.",
    )
    return parser.parse_args()


def print_command(arguments: list[str]) -> None:
    print(f"$ {shlex.join(['gh', *arguments])}")


def run_gh(
    arguments: list[str],
    *,
    capture: bool = False,
    allow_already_linked: bool = False,
) -> str:
    print_command(arguments)
    result = subprocess.run(
        ["gh", *arguments],
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode == 0:
        if not capture and result.stdout.strip():
            print(result.stdout.strip())
        return result.stdout.strip() if capture else ""

    error_output = result.stderr.strip()
    if allow_already_linked and "already linked" in error_output.lower():
        print("Project is already linked to the repository.")
        return ""

    if error_output:
        print(error_output, file=sys.stderr)
    raise subprocess.CalledProcessError(result.returncode, result.args)


def load_labels() -> list[dict[str, str]]:
    payload: Any = json.loads(LABELS_FILE.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"{LABELS_FILE} must contain a JSON list.")

    labels: list[dict[str, str]] = []
    label_names: set[str] = set()
    for entry in payload:
        if not isinstance(entry, dict):
            raise ValueError("Every label entry must be a JSON object.")
        label = {key: entry.get(key) for key in ("name", "color", "description")}
        if not all(isinstance(value, str) and value for value in label.values()):
            raise ValueError("Every label requires name, color, and description.")
        if label["name"] in label_names:
            raise ValueError(f"Duplicate label name: {label['name']}.")
        if re.fullmatch(r"[0-9A-Fa-f]{6}", label["color"]) is None:
            raise ValueError(f"Invalid label color for {label['name']}.")
        if len(label["description"]) > 100:
            raise ValueError(
                f"Label description for {label['name']} exceeds 100 characters."
            )
        label_names.add(label["name"])
        labels.append(label)
    return labels


def sync_labels(repository: str, labels: list[dict[str, str]], dry_run: bool) -> None:
    print(f"\nSynchronizing {len(labels)} labels for {repository}...")
    for label in labels:
        arguments = [
            "label",
            "create",
            label["name"],
            "--repo",
            repository,
            "--color",
            label["color"],
            "--description",
            label["description"],
            "--force",
        ]
        if dry_run:
            print_command(arguments)
        else:
            run_gh(arguments)


def find_or_create_project(
    owner: str,
    title: str,
    dry_run: bool,
) -> tuple[str, str | None]:
    if dry_run:
        print_command(["project", "list", "--owner", owner, "--format", "json"])
        print_command(
            [
                "project",
                "create",
                "--owner",
                owner,
                "--title",
                title,
                "--format",
                "json",
            ]
        )
        return "<project-number>", None

    project_list = json.loads(
        run_gh(
            ["project", "list", "--owner", owner, "--format", "json"],
            capture=True,
        )
    )
    for project in project_list.get("projects", []):
        if project.get("title") == title:
            print(f"Reusing project {title!r}.")
            return str(project["number"]), project.get("url")

    created_project = json.loads(
        run_gh(
            [
                "project",
                "create",
                "--owner",
                owner,
                "--title",
                title,
                "--format",
                "json",
            ],
            capture=True,
        )
    )
    return str(created_project["number"]), created_project.get("url")


def configure_project(
    owner: str,
    repository_name: str,
    project_number: str,
    dry_run: bool,
) -> None:
    edit_arguments = [
        "project",
        "edit",
        project_number,
        "--owner",
        owner,
        "--description",
        PROJECT_DESCRIPTION,
        "--readme",
        PROJECT_README,
    ]
    link_arguments = [
        "project",
        "link",
        project_number,
        "--owner",
        owner,
        "--repo",
        repository_name,
    ]

    if dry_run:
        print_command(edit_arguments)
        print_command(link_arguments)
        print_command(
            [
                "project",
                "field-list",
                str(project_number),
                "--owner",
                owner,
                "--format",
                "json",
            ]
        )
        existing_fields: set[str] = set()
    else:
        run_gh(edit_arguments)
        run_gh(link_arguments, allow_already_linked=True)
        field_payload = json.loads(
            run_gh(
                [
                    "project",
                    "field-list",
                    project_number,
                    "--owner",
                    owner,
                    "--format",
                    "json",
                ],
                capture=True,
            )
        )
        existing_fields = {
            field["name"] for field in field_payload.get("fields", [])
        }

    for field_name, options in PROJECT_FIELDS:
        if field_name in existing_fields:
            print(f"Project field {field_name!r} already exists.")
            continue
        arguments = [
            "project",
            "field-create",
            project_number,
            "--owner",
            owner,
            "--name",
            field_name,
            "--data-type",
            "SINGLE_SELECT",
            "--single-select-options",
            options,
        ]
        if dry_run:
            print_command(arguments)
        else:
            run_gh(arguments)


def main() -> int:
    arguments = parse_arguments()
    repository = f"{arguments.owner}/{arguments.repository}"

    try:
        labels = load_labels()
    except (json.JSONDecodeError, ValueError) as error:
        print(f"Invalid label configuration: {error}", file=sys.stderr)
        return 2

    if not arguments.dry_run:
        if shutil.which("gh") is None:
            print(
                "GitHub CLI was not found. Install it, run 'gh auth login', "
                "then run this setup utility again.",
                file=sys.stderr,
            )
            return 2
        try:
            run_gh(["auth", "status"])
        except subprocess.CalledProcessError:
            print("Authenticate with 'gh auth login' and try again.", file=sys.stderr)
            return 2

    try:
        sync_labels(repository, labels, arguments.dry_run)
        project_number, project_url = find_or_create_project(
            arguments.owner,
            arguments.title,
            arguments.dry_run,
        )
        configure_project(
            arguments.owner,
            arguments.repository,
            project_number,
            arguments.dry_run,
        )
    except (json.JSONDecodeError, KeyError, ValueError) as error:
        print(f"Invalid project configuration: {error}", file=sys.stderr)
        return 2
    except subprocess.CalledProcessError:
        print(
            "GitHub setup failed. Confirm repository access and run "
            "'gh auth refresh -s project' before retrying.",
            file=sys.stderr,
        )
        return 2

    if arguments.dry_run:
        print("\nDry run complete. No GitHub changes were made.")
    else:
        print(f"\nCody Development project is ready: {project_url or project_number}")
        print("Complete the UI-only board steps in DEVELOPMENT.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
