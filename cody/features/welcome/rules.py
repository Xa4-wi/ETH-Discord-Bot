"""Validated, repository-owned server-rule content."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from cody.config import SERVER_RULES


MAX_RULES = 20
MAX_TOTAL_CHARACTERS = 5_500


class ServerRulesError(RuntimeError):
    """The configured server-rules document is missing or malformed."""


@dataclass(frozen=True)
class ServerRule:
    heading: str
    text: str


@dataclass(frozen=True)
class ServerRules:
    version: str
    updated: str
    title: str
    introduction: str
    rules: tuple[ServerRule, ...]
    acknowledgement: str


def load_server_rules(path: Path = SERVER_RULES) -> ServerRules:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ServerRulesError(f"Server rules could not be loaded from {path}.") from error
    if not isinstance(raw, dict):
        raise ServerRulesError("Server rules must be a JSON object.")

    version = _required_text(raw, "version", 32)
    updated = _required_text(raw, "updated", 32)
    title = _required_text(raw, "title", 100)
    introduction = _required_text(raw, "introduction", 700)
    acknowledgement = _required_text(raw, "acknowledgement", 700)
    raw_rules = raw.get("rules")
    if not isinstance(raw_rules, list) or not 1 <= len(raw_rules) <= MAX_RULES:
        raise ServerRulesError(f"Server rules must contain 1–{MAX_RULES} entries.")

    rules: list[ServerRule] = []
    for index, raw_rule in enumerate(raw_rules, start=1):
        if not isinstance(raw_rule, dict):
            raise ServerRulesError(f"Server rule {index} must be an object.")
        rules.append(
            ServerRule(
                heading=_required_text(raw_rule, "heading", 100),
                text=_required_text(raw_rule, "text", 900),
            )
        )

    total_characters = sum(
        len(value)
        for value in (
            title,
            introduction,
            acknowledgement,
            *(rule.heading for rule in rules),
            *(rule.text for rule in rules),
        )
    )
    if total_characters > MAX_TOTAL_CHARACTERS:
        raise ServerRulesError(
            f"Server rules exceed the {MAX_TOTAL_CHARACTERS}-character message budget."
        )

    return ServerRules(
        version=version,
        updated=updated,
        title=title,
        introduction=introduction,
        rules=tuple(rules),
        acknowledgement=acknowledgement,
    )


def _required_text(source: dict[str, Any], field: str, maximum: int) -> str:
    value = source.get(field)
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ServerRulesError(
            f"Server rules field {field!r} must contain 1–{maximum} characters."
        )
    return value.strip()
