import logging
import os
from unittest.mock import patch
import unittest

from cody.shared.logging import RedactingFormatter, configure_logging
from cody.shared.redaction import redact_secrets


class LoggingRedactionTests(unittest.TestCase):
    def test_bearer_bot_and_assignment_credentials_are_redacted(self) -> None:
        message = (
            "Authorization: Bearer backend-value "
            "Authorization=Bot discord-value "
            "CODY_BACKEND_SERVICE_TOKEN=backend-value password=hunter2"
        )

        redacted = redact_secrets(message)

        self.assertNotIn("backend-value", redacted)
        self.assertNotIn("discord-value", redacted)
        self.assertNotIn("hunter2", redacted)

    def test_terminal_formatter_redacts_environment_secrets_and_traceback(self) -> None:
        formatter = RedactingFormatter("%(levelname)s %(message)s")
        secret = "backend-service-token-exact-value"
        with patch.dict(
            os.environ,
            {"CODY_BACKEND_SERVICE_TOKEN": secret},
            clear=False,
        ):
            try:
                raise RuntimeError(f"request failed with {secret}")
            except RuntimeError:
                record = logging.LogRecord(
                    name="cody.test",
                    level=logging.ERROR,
                    pathname=__file__,
                    lineno=1,
                    msg=f"token was {secret}",
                    args=(),
                    exc_info=__import__("sys").exc_info(),
                )
            rendered = formatter.format(record)

        self.assertNotIn(secret, rendered)
        self.assertIn("[REDACTED]", rendered)

    def test_configuration_replaces_inherited_unredacted_handlers(self) -> None:
        root = logging.getLogger()
        original_handlers = root.handlers[:]
        original_level = root.level
        inherited = logging.StreamHandler()
        inherited.setFormatter(logging.Formatter("UNSAFE %(message)s"))
        try:
            root.handlers = [inherited]

            configure_logging()

            self.assertNotIn(inherited, root.handlers)
            self.assertTrue(root.handlers)
            self.assertTrue(
                all(
                    isinstance(handler.formatter, RedactingFormatter)
                    for handler in root.handlers
                )
            )
        finally:
            for handler in root.handlers:
                if handler not in original_handlers:
                    handler.close()
            root.handlers = original_handlers
            root.setLevel(original_level)


if __name__ == "__main__":
    unittest.main()
