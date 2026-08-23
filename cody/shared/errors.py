"""Central application-command error responses."""

import logging

import discord
from discord import app_commands

from cody.shared.permissions import CodyRoleRequired


LOGGER = logging.getLogger(__name__)


async def handle_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError,
) -> None:
    if isinstance(error, CodyRoleRequired):
        message = error.message
    elif isinstance(error, app_commands.MissingPermissions):
        message = "Administrator permission is required for this command."
    else:
        LOGGER.exception("Unhandled application command error", exc_info=error)
        message = "Cody could not complete that command. Check the bot logs."

    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)
