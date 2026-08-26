"""Typed state used by the welcome and access-selection workflow."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class ParticipantLink:
    """Backend-confirmed participant identity for one Discord actor."""

    participant_id: str
    display_name: str
    team_id: str | None


class SponsorDecision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"

