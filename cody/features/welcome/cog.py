"""Discord triggers and test command for member welcomes."""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from cody.config import WELCOME_CHANNEL_ID
from cody.features.welcome.service import send_welcome_message
from cody.shared.permissions import administrator_only


LOGGER = logging.getLogger(__name__)


class WelcomeCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        await send_welcome_message(member)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        channel = self.bot.get_channel(WELCOME_CHANNEL_ID)
        if channel is None:
            LOGGER.error("Welcome channel %s was not found", WELCOME_CHANNEL_ID)
            return

        bot_member = channel.guild.me
        if bot_member is None:
            LOGGER.error("Cody's guild member could not be resolved")
            return

        permissions = channel.permissions_for(bot_member)
        LOGGER.info(
            "Welcome permissions | view=%s send=%s embeds=%s files=%s history=%s",
            permissions.view_channel,
            permissions.send_messages,
            permissions.embed_links,
            permissions.attach_files,
            permissions.read_message_history,
        )

    @app_commands.command(
        name="test_welcome",
        description="Test Cody's welcome message in the configured welcome channel.",
    )
    @app_commands.default_permissions(administrator=True)
    @administrator_only()
    async def test_welcome(self, interaction: discord.Interaction) -> None:
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "This command can only be used inside a server.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)
        sent = await send_welcome_message(interaction.user)

        if sent:
            result = f"Welcome test sent to <#{WELCOME_CHANNEL_ID}>."
        else:
            result = f"Welcome channel <#{WELCOME_CHANNEL_ID}> was not found."

        await interaction.edit_original_response(content=result)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(WelcomeCog(bot))
