from pathlib import Path
import unittest

from cody.bot import EXTENSIONS


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FEATURES_ROOT = PROJECT_ROOT / "cody" / "features"
FEATURE_INDEX = FEATURES_ROOT / "README.md"
REQUIRED_SECTIONS = (
    "## Status",
    "## Purpose",
    "## Current implementation",
    "## Intended scope",
    "## Dependencies and boundaries",
    "## Development checklist",
    "## Testing",
    "## Operational notes",
)


class FeatureDocumentationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.feature_directories = sorted(
            path
            for path in FEATURES_ROOT.iterdir()
            if path.is_dir() and not path.name.startswith("__")
        )

    def test_every_feature_has_complete_documentation(self) -> None:
        for feature_directory in self.feature_directories:
            with self.subTest(feature=feature_directory.name):
                readme = feature_directory / "README.md"
                self.assertTrue(readme.is_file(), f"Missing {readme}")
                documentation = readme.read_text(encoding="utf-8")
                for section in REQUIRED_SECTIONS:
                    self.assertIn(section, documentation)

    def test_feature_index_lists_every_feature(self) -> None:
        index = FEATURE_INDEX.read_text(encoding="utf-8")

        for feature_directory in self.feature_directories:
            with self.subTest(feature=feature_directory.name):
                self.assertIn(
                    f"({feature_directory.name}/README.md)",
                    index,
                )

    def test_documented_extension_state_matches_bot_configuration(self) -> None:
        loaded_features = {
            extension.split(".")[2]
            for extension in EXTENSIONS
            if extension.startswith("cody.features.")
        }

        for feature_directory in self.feature_directories:
            with self.subTest(feature=feature_directory.name):
                documentation = (feature_directory / "README.md").read_text(
                    encoding="utf-8"
                )
                expected = (
                    "Extension loaded: **Yes**"
                    if feature_directory.name in loaded_features
                    else "Extension loaded: **No**"
                )
                self.assertIn(expected, documentation)


if __name__ == "__main__":
    unittest.main()
