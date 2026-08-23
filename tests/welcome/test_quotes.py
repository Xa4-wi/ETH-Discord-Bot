import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from cody.features.welcome.quotes import (
    FALLBACK_WELCOME_QUOTE,
    load_welcome_quotes,
    random_welcome_quote,
)


class WelcomeQuoteTests(unittest.TestCase):
    def _write_quotes(
        self,
        directory: str,
        filename: str,
        payload: object,
    ) -> Path:
        path = Path(directory) / filename
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_project_quote_asset_is_available(self) -> None:
        quotes = load_welcome_quotes()

        self.assertGreater(len(quotes), 1)
        self.assertTrue(all(quote.strip() for quote in quotes))

    def test_loads_and_normalizes_nonempty_quotes(self) -> None:
        with TemporaryDirectory() as directory:
            path = self._write_quotes(
                directory,
                "valid.json",
                {"quotes": ["  First quote.  ", "", 42, "Second\nquote."]},
            )

            self.assertEqual(
                load_welcome_quotes(path),
                ("First quote.", "Second quote."),
            )

    def test_random_quote_uses_loaded_entries(self) -> None:
        with TemporaryDirectory() as directory:
            path = self._write_quotes(
                directory,
                "selectable.json",
                {"quotes": ["One", "Two"]},
            )

            with patch(
                "cody.features.welcome.quotes.random.choice",
                return_value="Two",
            ) as choice:
                result = random_welcome_quote(path)

            self.assertEqual(result, "Two")
            choice.assert_called_once_with(("One", "Two"))

    def test_missing_or_malformed_quote_data_uses_fallback(self) -> None:
        with TemporaryDirectory() as directory:
            invalid_json = Path(directory) / "invalid.json"
            invalid_json.write_text("{", encoding="utf-8")
            invalid_encoding = Path(directory) / "invalid-encoding.json"
            invalid_encoding.write_bytes(b"\xff")
            cases = (
                Path(directory) / "missing.json",
                invalid_json,
                invalid_encoding,
                self._write_quotes(directory, "wrong-root.json", []),
                self._write_quotes(
                    directory,
                    "wrong-type.json",
                    {"quotes": "not-a-list"},
                ),
                self._write_quotes(
                    directory,
                    "empty.json",
                    {"quotes": [" ", 42]},
                ),
            )

            for index, path in enumerate(cases):
                with self.subTest(index=index), self.assertLogs(
                    "cody.features.welcome.quotes",
                    level="WARNING",
                ):
                    self.assertEqual(
                        load_welcome_quotes(path),
                        (FALLBACK_WELCOME_QUOTE,),
                    )


if __name__ == "__main__":
    unittest.main()
