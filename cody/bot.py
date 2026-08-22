"""Cody client setup and feature extension loading."""

import logging

import discord
from discord.ext import commands

from cody.shared.errors import handle_app_command_error


LOGGER = logging.getLogger(__name__)

EXTENSIONS = (
    "cody.features.system.cog",
    "cody.features.welcome.cog",
)


class CodyBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.members = True

        super().__init__(command_prefix=commands.when_mentioned, intents=intents)
        self.guild_commands_synced = False
        self.tree.on_error = handle_app_command_error

    async def setup_hook(self) -> None:
        for extension in EXTENSIONS:
            await self.load_extension(extension)
            LOGGER.info("Loaded extension %s", extension)

        commands_synced = await self.tree.sync()
        LOGGER.info("Registered %d global slash command(s)", len(commands_synced))

    async def sync_commands_to_guilds(self) -> None:
        """Register commands per guild for immediate development availability."""

        if self.guild_commands_synced:
            return

        for guild in self.guilds:
            self.tree.copy_global_to(guild=guild)
            commands_synced = await self.tree.sync(guild=guild)
            command_names = ", ".join(
                f"/{command.name}" for command in commands_synced
            )
            LOGGER.info(
                "Synced commands to %s (%s): %s",
                guild.name,
                guild.id,
                command_names,
            )

        self.guild_commands_synced = True

    async def on_ready(self) -> None:
        LOGGER.info("Logged in as %s", self.user)
        await self.sync_commands_to_guilds()


def create_bot() -> CodyBot:
    return CodyBot()
