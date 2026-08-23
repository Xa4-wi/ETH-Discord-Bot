"""Core informational slash commands."""

import discord
from discord import app_commands
from discord.ext import commands

from cody.features.system.views import about_embed, network_status_embed
from cody.shared.permissions import participant_only


class SystemCog(commands.Cog):
    @app_commands.command(
        name="ping",
        description="Check whether ETH Battlecode Command is online.",
    )
    @participant_only()
    async def ping(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(embed=network_status_embed())

    @app_commands.command(
        name="about",
        description="Information about ETH Battlecode.",
    )
    @participant_only()
    async def about(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(embed=about_embed())


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SystemCog())
