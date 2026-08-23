"""Discord log relay and administrator health commands."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging

import discord
from discord import app_commands
from discord.ext import commands

from cody.config import LOG_CHANNEL_ID
from cody.features.monitoring.models import DiscordLogEntry
from cody.features.monitoring.service import DiscordLogHandler, log_entry_embed
from cody.shared.colors import CodyColor
from cody.shared.components import cody_embed
from cody.shared.permissions import admin_only


LOGGER = logging.getLogger(__name__)
QUEUE_LIMIT = 200
RETRY_SECONDS = 30


@app_commands.default_permissions(administrator=True)
class MonitoringCog(
    commands.GroupCog,
    group_name="logs",
    group_description="Inspect Cody's Discord operations log relay.",
):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.queue: asyncio.Queue[DiscordLogEntry] = asyncio.Queue(
            maxsize=QUEUE_LIMIT
        )
        self.dropped_entries = 0
        self._loop = asyncio.get_running_loop()
        self._handler = DiscordLogHandler(self._schedule_entry)
        self._worker: asyncio.Task[None] | None = None

    async def cog_load(self) -> None:
        logging.getLogger().addHandler(self._handler)
        self._worker = asyncio.create_task(
            self._deliver_logs(),
            name="cody-discord-log-relay",
        )

    async def cog_unload(self) -> None:
        logging.getLogger().removeHandler(self._handler)
        if self._worker is None:
            return
        self._worker.cancel()
        try:
            await self._worker
        except asyncio.CancelledError:
            pass

    @app_commands.command(
        name="status",
        description="Check Cody's Discord log channel and delivery health.",
    )
    @admin_only()
    async def status(self, interaction: discord.Interaction) -> None:
        channel = self.bot.get_channel(LOG_CHANNEL_ID)
        channel_guild = getattr(channel, "guild", None)
        if channel is None or channel_guild is None:
            await interaction.response.send_message(
                f"Log channel <#{LOG_CHANNEL_ID}> was not found or is not visible to Cody.",
                ephemeral=True,
            )
            return
        if interaction.guild_id != channel_guild.id:
            await interaction.response.send_message(
                "This command can only be used in Cody's configured server.",
                ephemeral=True,
            )
            return

        bot_member = channel_guild.me
        if bot_member is None:
            await interaction.response.send_message(
                "Cody's guild member could not be resolved.",
                ephemeral=True,
            )
            return

        permissions = channel.permissions_for(bot_member)
        ready = (
            permissions.view_channel
            and permissions.send_messages
            and permissions.embed_links
            and self._worker is not None
            and not self._worker.done()
        )
        embed = cody_embed(
            title="LOG RELAY STATUS",
            description=(
                "Discord log delivery is operational."
                if ready
                else "Discord log delivery needs attention."
            ),
            color=CodyColor.SUCCESS if ready else CodyColor.WARNING,
        )
        embed.add_field(
            name="Channel",
            value=f"<#{LOG_CHANNEL_ID}>",
            inline=False,
        )
        embed.add_field(
            name="Permissions",
            value=(
                f"View Channel: {'yes' if permissions.view_channel else 'no'}\n"
                f"Send Messages: {'yes' if permissions.send_messages else 'no'}\n"
                f"Embed Links: {'yes' if permissions.embed_links else 'no'}"
            ),
            inline=True,
        )
        embed.add_field(
            name="Queue",
            value=(
                f"Waiting: {self.queue.qsize()}\n"
                f"Dropped: {self.dropped_entries}\n"
                f"Worker: {'running' if self._worker and not self._worker.done() else 'stopped'}"
            ),
            inline=True,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="test",
        description="Send a safe test event through Cody's Discord log relay.",
    )
    @admin_only()
    async def test(self, interaction: discord.Interaction) -> None:
        channel = self.bot.get_channel(LOG_CHANNEL_ID)
        channel_guild = getattr(channel, "guild", None)
        if channel is None or channel_guild is None:
            await interaction.response.send_message(
                f"Log channel <#{LOG_CHANNEL_ID}> was not found or is not visible to Cody.",
                ephemeral=True,
            )
            return
        if interaction.guild_id != channel_guild.id:
            await interaction.response.send_message(
                "This command can only be used in Cody's configured server.",
                ephemeral=True,
            )
            return

        self._enqueue_nowait(
            DiscordLogEntry(
                level=logging.INFO,
                level_name="INFO",
                component="Monitoring / Manual Test",
                message=(
                    f"Log delivery test requested by Discord member {interaction.user.id}."
                ),
                created_at=datetime.now(timezone.utc),
            )
        )
        await interaction.response.send_message(
            f"Test event queued for <#{LOG_CHANNEL_ID}>.",
            ephemeral=True,
        )

    def _schedule_entry(self, entry: DiscordLogEntry) -> None:
        self._loop.call_soon_threadsafe(self._enqueue_nowait, entry)

    def _enqueue_nowait(self, entry: DiscordLogEntry) -> None:
        if self.queue.full():
            self.queue.get_nowait()
            self.dropped_entries += 1
            if self.dropped_entries == 1 or self.dropped_entries % 25 == 0:
                LOGGER.warning(
                    "Discord log queue overflow; %d entries dropped",
                    self.dropped_entries,
                )
        self.queue.put_nowait(entry)

    async def _deliver_logs(self) -> None:
        await self.bot.wait_until_ready()
        online_notice_sent = False
        pending_entry: DiscordLogEntry | None = None

        while not self.bot.is_closed():
            channel = self.bot.get_channel(LOG_CHANNEL_ID)
            if channel is None or not hasattr(channel, "send"):
                LOGGER.error(
                    "Discord log channel %s was not found or is not visible",
                    LOG_CHANNEL_ID,
                )
                await asyncio.sleep(RETRY_SECONDS)
                continue

            try:
                if not online_notice_sent:
                    await channel.send(
                        embed=log_entry_embed(
                            DiscordLogEntry(
                                level=logging.INFO,
                                level_name="INFO",
                                component="Monitoring / Relay",
                                message=(
                                    "Discord operations logging is online. "
                                    "Use /logs status if delivery problems occur."
                                ),
                                created_at=datetime.now(timezone.utc),
                            )
                        )
                    )
                    online_notice_sent = True

                if pending_entry is None:
                    pending_entry = await self.queue.get()
                await channel.send(embed=log_entry_embed(pending_entry))
                pending_entry = None
            except (discord.Forbidden, discord.HTTPException) as error:
                LOGGER.error(
                    "Could not deliver logs to channel %s: %s",
                    LOG_CHANNEL_ID,
                    error,
                )
                await asyncio.sleep(RETRY_SECONDS)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MonitoringCog(bot))
