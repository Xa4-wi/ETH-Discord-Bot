"""Defense-in-depth credential redaction shared by every log destination."""

from __future__ import annotations

from collections.abc import Iterable
import os
import re


_DISCORD_TOKEN_PATTERN = re.compile(
    r"\b[A-Za-z0-9_-]{23,30}\.[A-Za-z0-9_-]{6}\.[A-Za-z0-9_-]{25,}\b"
)
_AUTHORIZATION_HEADER_PATTERN = re.compile(
    r"(?i)\b(authorization)\s*[:=]\s*(?:(?:bot|bearer)\s+)?\S+"
)
_SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b([A-Za-z0-9_]*(?:token|secret|password|api_key)"
    r"[A-Za-z0-9_]*)\s*[:=]\s*\S+"
)


def sensitive_environment_values() -> tuple[str, ...]:
    """Return configured secrets that need exact-value redaction."""

    return tuple(
        value
        for value in (
            os.getenv("DISCORD_TOKEN"),
            os.getenv("CODY_BACKEND_SERVICE_TOKEN"),
        )
        if value
    )


def redact_secrets(
    text: str,
    sensitive_values: Iterable[str] = (),
) -> str:
    """Remove known values and common credential shapes from arbitrary text."""

    redacted = text
    for value in sensitive_values:
        if value:
            redacted = redacted.replace(value, "[REDACTED]")
    redacted = _DISCORD_TOKEN_PATTERN.sub("[REDACTED TOKEN]", redacted)
    redacted = _AUTHORIZATION_HEADER_PATTERN.sub(
        lambda match: f"{match.group(1)}=[REDACTED]",
        redacted,
    )
    redacted = _SECRET_ASSIGNMENT_PATTERN.sub(
        lambda match: f"{match.group(1)}=[REDACTED]",
        redacted,
    )
    return redacted
