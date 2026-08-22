"""Welcome-message orchestration."""

import logging

import discord

from cody.config import WELCOME_CHANNEL_ID
from cody.features.welcome.renderer import create_welcome_card
from cody.features.welcome.views import welcome_view


LOGGER = logging.getLogger(__name__)


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
