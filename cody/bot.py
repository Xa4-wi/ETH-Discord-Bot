"""Cody client setup and feature extension loading."""

import logging

import discord
from discord.ext import commands

from cody.shared.errors import handle_app_command_error


LOGGER = logging.getLogger(__name__)

EXTENSIONS = (
    "cody.features.monitoring.cog",
    "cody.features.system.cog",
    "cody.features.server_stats.cog",
    "cody.features.welcome.cog",
    "cody.features.tickets.cog",
)


class CodyBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.members = True

        super().__init__(command_prefix=commands.when_mentioned, intents=intents)
        self.guild_command_copies_cleared = False
        self.tree.on_error = handle_app_command_error

    async def setup_hook(self) -> None:
        for extension in EXTENSIONS:
            await self.load_extension(extension)
            LOGGER.info("Loaded extension %s", extension)

        commands_synced = await self.tree.sync()
        LOGGER.info("Registered %d global slash command(s)", len(commands_synced))

    async def clear_legacy_guild_command_copies(self) -> None:
        """Remove old guild copies so each global command appears only once."""

        if self.guild_command_copies_cleared:
            return

        for guild in self.guilds:
            self.tree.clear_commands(guild=guild)
            commands_synced = await self.tree.sync(guild=guild)
            LOGGER.info(
                "Cleared legacy guild command copies from %s (%s); %d remain",
                guild.name,
                guild.id,
                len(commands_synced),
            )

        self.guild_command_copies_cleared = True

    async def on_ready(self) -> None:
        LOGGER.info("Logged in as %s", self.user)
        await self.clear_legacy_guild_command_copies()


def create_bot() -> CodyBot:
    return CodyBot()
