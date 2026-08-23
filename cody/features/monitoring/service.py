"""Sanitize, classify, and present Cody log records for Discord."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import datetime, timezone
import logging
import os
import re

import discord

from cody.features.monitoring.models import DiscordLogEntry
from cody.shared.colors import CodyColor


MAX_DISCORD_LOG_MESSAGE = 3500
MONITORING_LOGGER_PREFIX = "cody.features.monitoring"

_TOKEN_PATTERN = re.compile(
    r"\b[A-Za-z0-9_-]{23,30}\.[A-Za-z0-9_-]{6}\.[A-Za-z0-9_-]{25,}\b"
)
_SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(token|secret|password|authorization)\s*[:=]\s*\S+"
)
_BOT_AUTH_PATTERN = re.compile(
    r"(?i)\b(authorization\s*[:=]\s*Bot)\s+\S+"
)


class DiscordLogHandler(logging.Handler):
    """Convert Cody log records and enqueue them for async Discord delivery."""

    def __init__(self, enqueue: Callable[[DiscordLogEntry], None]) -> None:
        super().__init__(level=logging.INFO)
        self._enqueue = enqueue

    def emit(self, record: logging.LogRecord) -> None:
        if not record.name.startswith("cody"):
            return
        if record.name.startswith(MONITORING_LOGGER_PREFIX):
            return

        try:
            token = os.getenv("DISCORD_TOKEN")
            sensitive_values = (token,) if token else ()
            self._enqueue(log_entry_from_record(record, sensitive_values))
        except Exception:
            self.handleError(record)


def log_entry_from_record(
    record: logging.LogRecord,
    sensitive_values: Iterable[str] = (),
) -> DiscordLogEntry:
    """Create a sanitized Discord log entry without including a traceback."""

    error_type = None
    if record.exc_info is not None and record.exc_info[0] is not None:
        error_type = record.exc_info[0].__name__

    return DiscordLogEntry(
        level=record.levelno,
        level_name=record.levelname,
        component=component_name(record.name),
        message=sanitize_log_message(record.getMessage(), sensitive_values),
        created_at=datetime.fromtimestamp(record.created, tz=timezone.utc),
        error_type=error_type,
    )


def sanitize_log_message(
    message: str,
    sensitive_values: Iterable[str] = (),
) -> str:
    """Redact secrets and fit a log summary within Discord embed limits."""

    sanitized = message
    for value in sensitive_values:
        if value:
            sanitized = sanitized.replace(value, "[REDACTED]")
    sanitized = _TOKEN_PATTERN.sub("[REDACTED TOKEN]", sanitized)
    sanitized = _BOT_AUTH_PATTERN.sub(r"\1 [REDACTED]", sanitized)
    sanitized = _SECRET_ASSIGNMENT_PATTERN.sub(
        lambda match: f"{match.group(1)}=[REDACTED]",
        sanitized,
    )
    sanitized = " ".join(sanitized.split()) or "No message was supplied."
    if len(sanitized) <= MAX_DISCORD_LOG_MESSAGE:
        return sanitized
    return f"{sanitized[: MAX_DISCORD_LOG_MESSAGE - 1].rstrip()}…"


def component_name(logger_name: str) -> str:
    """Turn a Python logger path into a readable Cody component name."""

    parts = logger_name.split(".")
    if len(parts) >= 4 and parts[1] == "features":
        feature = parts[2].replace("_", " ").title()
        layer = parts[3].replace("_", " ").title()
        return f"{feature} / {layer}"
    if logger_name == "cody.bot":
        return "Cody / Startup"
    return " / ".join(part.replace("_", " ").title() for part in parts[1:])


def log_entry_embed(entry: DiscordLogEntry) -> discord.Embed:
    """Build a compact operator-friendly embed for one log entry."""

    title, color = _level_presentation(entry.level)
    embed = discord.Embed(
        title=title,
        description=entry.message,
        color=int(color),
        timestamp=entry.created_at,
    )
    embed.add_field(name="Component", value=entry.component, inline=True)
    embed.add_field(name="Level", value=entry.level_name, inline=True)
    if entry.error_type:
        embed.add_field(name="Error type", value=entry.error_type, inline=False)
    if entry.level >= logging.ERROR:
        embed.add_field(
            name="Suggested action",
            value=(
                "Check `/logs status` and the terminal traceback. For statistics "
                "issues, also run `/stats permissions`."
            ),
            inline=False,
        )
    embed.set_footer(text="CODY // OPERATIONS LOG · Full details remain in terminal")
    return embed


def _level_presentation(level: int) -> tuple[str, CodyColor]:
    if level >= logging.CRITICAL:
        return "🚨 CRITICAL BOT ERROR", CodyColor.ERROR
    if level >= logging.ERROR:
        return "❌ BOT ERROR", CodyColor.ERROR
    if level >= logging.WARNING:
        return "⚠️ ATTENTION REQUIRED", CodyColor.WARNING
    return "✅ SYSTEM UPDATE", CodyColor.SUCCESS
