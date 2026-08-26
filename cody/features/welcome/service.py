"""Welcome-message orchestration."""

from __future__ import annotations

import logging

import discord

from cody.config import (
    PARTICIPANT_ROLE_ID,
    RULES_ACCEPTED_ROLE_ID,
    SPONSOR_ROLE_ID,
    SPONSOR_UNDER_REVIEW_ROLE_ID,
    VISITOR_ROLE_ID,
    WELCOME_CHANNEL_ID,
)
from cody.features.welcome.renderer import create_welcome_card
from cody.features.welcome.views import welcome_view


LOGGER = logging.getLogger(__name__)
ACCESS_ROLE_IDS = frozenset(
    {
        PARTICIPANT_ROLE_ID,
        SPONSOR_ROLE_ID,
        SPONSOR_UNDER_REVIEW_ROLE_ID,
        VISITOR_ROLE_ID,
    }
)


class OnboardingSetupError(RuntimeError):
    """Cody cannot resolve or assign a configured onboarding resource."""


def find_rules_accepted_role(guild: discord.Guild) -> discord.Role | None:
    """Resolve and validate the durable acceptance marker by configured ID."""

    role = guild.get_role(RULES_ACCEPTED_ROLE_ID)
    if role is not None:
        _validate_rules_accepted_role(guild, role)
    return role


async def ensure_rules_accepted_role(guild: discord.Guild) -> discord.Role:
    """Require Cody's configured non-access-granting rules marker role."""

    role = find_rules_accepted_role(guild)
    if role is not None:
        return role
    raise OnboardingSetupError(
        f"The configured Rules Accepted role {RULES_ACCEPTED_ROLE_ID} was not found."
    )


async def accept_server_rules(member: discord.Member) -> discord.Role:
    """Persist rules acceptance without granting any server-area permission."""

    role = await ensure_rules_accepted_role(member.guild)
    if not any(current.id == role.id for current in member.roles):
        await member.add_roles(role, reason="Member accepted Cody's server rules")
    return role


def _validate_rules_accepted_role(
    guild: discord.Guild,
    role: discord.Role,
) -> None:
    if role.managed or role.permissions != discord.Permissions.none():
        raise OnboardingSetupError(
            "The Rules Accepted marker must be an unmanaged role with no "
            "server permissions."
        )
    channels_with_overwrites = []
    for channel in guild.channels:
        allow, deny = channel.overwrites_for(role).pair()
        if allow.value or deny.value:
            channels_with_overwrites.append(channel.id)
    if channels_with_overwrites:
        raise OnboardingSetupError(
            "The Rules Accepted marker must not have channel permission "
            "overwrites."
        )


async def replace_access_role(
    member: discord.Member,
    target_role_id: int,
    *,
    reason: str,
) -> discord.Role:
    """Atomically replace Cody-managed access roles while preserving all others."""

    role = member.guild.get_role(target_role_id)
    if role is None:
        raise OnboardingSetupError(
            f"The configured access role {target_role_id} was not found."
        )

    retained_roles = [
        current
        for current in member.roles
        if current.id != member.guild.id and current.id not in ACCESS_ROLE_IDS
    ]
    await member.edit(roles=[*retained_roles, role], reason=reason)
    return role


async def remove_access_roles(
    member: discord.Member,
    *,
    reason: str,
) -> None:
    """Remove every Cody-managed access role while preserving unrelated roles."""

    retained_roles = [
        current
        for current in member.roles
        if current.id != member.guild.id and current.id not in ACCESS_ROLE_IDS
    ]
    await member.edit(roles=retained_roles, reason=reason)


async def send_welcome_message(member: discord.Member) -> bool:
    """Generate and send Cody's welcome interface for a member."""

    channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
    if channel is None:
        LOGGER.error(
            "Welcome channel %s was not found in guild %s",
            WELCOME_CHANNEL_ID,
            member.guild.id,
        )
        return False

    card_buffer = await create_welcome_card(member)
    card_filename = f"arrival-{member.id}.png"
    card_file = discord.File(card_buffer, filename=card_filename)

    await channel.send(
        view=welcome_view(member, card_filename),
        file=card_file,
    )
    return True
