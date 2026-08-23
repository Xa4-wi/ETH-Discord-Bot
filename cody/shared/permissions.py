"""Reusable application-command permission checks."""

from __future__ import annotations

import discord
from discord import app_commands

from cody.config import ADMIN_ROLE_ID, PARTICIPANT_ROLE_ID


class CodyRoleRequired(app_commands.CheckFailure):
    """Raised when a member does not have the Cody role required by a command."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def member_has_role(user: discord.User | discord.Member, role_id: int) -> bool:
    """Return whether a Discord interaction user has a configured role."""

    roles = getattr(user, "roles", None)
    return roles is not None and any(role.id == role_id for role in roles)


async def participant_access_check(interaction: discord.Interaction) -> bool:
    """Allow participants and admins to use participant-facing commands."""

    if member_has_role(interaction.user, PARTICIPANT_ROLE_ID) or member_has_role(
        interaction.user,
        ADMIN_ROLE_ID,
    ):
        return True
    raise CodyRoleRequired(
        "The Participant role is required to use this Cody command."
    )


async def admin_access_check(interaction: discord.Interaction) -> bool:
    """Allow only members with Cody's configured Admin role."""

    if member_has_role(interaction.user, ADMIN_ROLE_ID):
        return True
    raise CodyRoleRequired("The configured Admin role is required for this command.")


def participant_only():
    return app_commands.check(participant_access_check)


def admin_only():
    return app_commands.check(admin_access_check)
