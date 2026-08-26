"""Logging defaults and terminal credential redaction for Cody processes."""

import logging

from cody.shared.redaction import redact_secrets, sensitive_environment_values


class RedactingFormatter(logging.Formatter):
    """Redact credentials from the complete rendered record and traceback."""

    def format(self, record: logging.LogRecord) -> str:
        rendered = super().format(record)
        return redact_secrets(rendered, sensitive_environment_values())


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(
        RedactingFormatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
    )
    logging.basicConfig(
        level=logging.INFO,
        handlers=[handler],
        # Cody owns the process logging configuration. Replacing an inherited
        # root handler guarantees that every terminal record uses redaction.
        force=True,
    )
