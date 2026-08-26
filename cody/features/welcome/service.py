"""Welcome-message orchestration."""

import logging

import discord

from cody.config import (
    PARTICIPANT_ROLE_ID,
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
