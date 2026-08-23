"""Data models for Discord log delivery."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class DiscordLogEntry:
    """Sanitized application-log information safe for a Discord embed."""

    level: int
    level_name: str
    component: str
    message: str
    created_at: datetime
    error_type: str | None = None
