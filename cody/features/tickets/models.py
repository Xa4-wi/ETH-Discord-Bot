"""Temporary Discord-workflow models for Cody support tickets."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class TicketCategory(str, Enum):
    TECHNICAL = "technical"
    COMPETITION = "competition"
    TEAM = "team"
    ACCOUNT = "account"
    OTHER = "other"

    @property
    def display_name(self) -> str:
        return self.value.title()


class TicketStatus(str, Enum):
    OPEN = "open"
    CLAIMED = "claimed"
    RESOLVED = "resolved"


@dataclass(frozen=True)
class Ticket:
    """One temporary Discord support request; not the future backend DTO."""

    ticket_id: int
    discord_user_id: int
    category: TicketCategory
    subject: str
    description: str
    attempted_solution: str
    status: TicketStatus
    created_at: datetime
    discord_channel_id: int | None = None
    assigned_organizer_id: int | None = None
    resolved_at: datetime | None = None
    resolved_by_id: int | None = None

    @property
    def display_id(self) -> str:
        return f"{self.ticket_id:04d}"
