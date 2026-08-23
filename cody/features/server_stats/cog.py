"""Scheduled updates and admin commands for server statistics."""

from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands, tasks

from cody.features.server_stats.constants import (
    REFRESH_INTERVAL_MINUTES,
    SERVER_STATS_CONFIG,
)
from cody.features.server_stats.providers import create_stats_provider
from cody.features.server_stats.service import (
    ServerStatsService,
    check_stat_permissions,
    format_stat_permission_report,
)
from cody.shared.permissions import admin_only


LOGGER = logging.getLogger(__name__)


class ServerStatsCog(
    commands.GroupCog,
    group_name="stats",
    group_description="Inspect and refresh Cody's server statistics.",
):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.provider = create_stats_provider()
        self.service = ServerStatsService(self.provider)
        self.refresh_stats_task.start()

    async def cog_unload(self) -> None:
        self.refresh_stats_task.cancel()
        await self.provider.close()

    @tasks.loop(minutes=REFRESH_INTERVAL_MINUTES)
    async def refresh_stats_task(self) -> None:
        guild = self._target_guild()
        if guild is None:
            LOGGER.error(
                "Server statistics guild could not be resolved from channel %s",
                SERVER_STATS_CONFIG.member_channel_id,
            )
            return
        await self.service.refresh(guild)

    @refresh_stats_task.before_loop
    async def before_refresh_stats(self) -> None:
        await self.bot.wait_until_ready()

    @app_commands.command(
        name="refresh",
        description="Immediately refresh all configured server statistics.",
    )
    @admin_only()
    async def refresh(self, interaction: discord.Interaction) -> None:
        guild = self._target_guild()
        if guild is None or interaction.guild_id != guild.id:
            await interaction.response.send_message(
                "The configured statistics server could not be resolved.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)
        result = await self.service.refresh(guild)
        message = f"Server statistics refreshed; {len(result.updated_channel_ids)} channel(s) updated."
        if result.provider_error is not None:
            message += " The provider failed, so Cody kept its previous competition values."
        if result.missing_channel_ids or result.failed_channel_ids:
            message += " Some channels could not be updated; check Cody's logs."
        await interaction.edit_original_response(content=message)

    @app_commands.command(
        name="permissions",
        description="Check the permissions Cody uses for statistics channels.",
    )
    @admin_only()
    async def permissions(self, interaction: discord.Interaction) -> None:
        guild = self._target_guild()
        if guild is None or interaction.guild_id != guild.id:
            await interaction.response.send_message(
                "The configured statistics server could not be resolved.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            format_stat_permission_report(check_stat_permissions(guild)),
            ephemeral=True,
        )

    def _target_guild(self) -> discord.Guild | None:
        channel = self.bot.get_channel(SERVER_STATS_CONFIG.member_channel_id)
        guild = getattr(channel, "guild", None)
        return guild if isinstance(guild, discord.Guild) else None


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ServerStatsCog(bot))
