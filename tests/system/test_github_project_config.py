import json
from pathlib import Path
import subprocess
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LABELS_FILE = PROJECT_ROOT / ".github" / "labels.json"
SETUP_SCRIPT = PROJECT_ROOT / "scripts" / "setup_github_project.py"


class GitHubProjectConfigTests(unittest.TestCase):
    def test_label_catalog_has_unique_valid_entries(self):
        labels = json.loads(LABELS_FILE.read_text(encoding="utf-8"))
        names = [label["name"] for label in labels]

        self.assertTrue(names)
        self.assertEqual(len(names), len(set(names)))

        for label in labels:
            self.assertRegex(label["color"], r"^[0-9A-F]{6}$")
            self.assertTrue(label["description"])
            self.assertLessEqual(len(label["description"]), 100)

    def test_project_setup_dry_run_needs_no_github_connection(self):
        result = subprocess.run(
            [sys.executable, str(SETUP_SCRIPT), "--dry-run"],
            cwd=PROJECT_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

        self.assertIn("Dry run complete. No GitHub changes were made.", result.stdout)
        self.assertIn("Cody Development", result.stdout)


if __name__ == "__main__":
    unittest.main()
