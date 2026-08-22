import os

import discord
from discord import app_commands

from cody_messages import (
    WELCOME_CHANNEL_ID,
    about_embed,
    network_status_embed,
    send_welcome_message,
)

TOKEN = os.environ["DISCORD_TOKEN"]


class BattlecodeBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True

        super().__init__(intents=intents)

        self.tree = app_commands.CommandTree(self)
        self.guild_commands_synced = False

    async def setup_hook(self):
        commands = await self.tree.sync()
        print(f"Registered {len(commands)} global slash command(s).")

    async def sync_commands_to_guilds(self):
        """Register commands per guild for immediate development availability."""

        if self.guild_commands_synced:
            return

        for guild in self.guilds:
            self.tree.copy_global_to(guild=guild)
            commands = await self.tree.sync(guild=guild)
            command_names = ", ".join(f"/{command.name}" for command in commands)
            print(f"Synced commands to {guild.name} ({guild.id}): {command_names}")

        self.guild_commands_synced = True


bot = BattlecodeBot()


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await bot.sync_commands_to_guilds()

    channel = bot.get_channel(WELCOME_CHANNEL_ID)

    if channel is None:
        print("ERROR: Welcome channel not found")
        return

    me = channel.guild.me
    perms = channel.permissions_for(me)

    print("\n=== CODY PERMISSIONS IN #welcome ===")
    print(f"View Channel:        {perms.view_channel}")
    print(f"Send Messages:       {perms.send_messages}")
    print(f"Embed Links:         {perms.embed_links}")
    print(f"Attach Files:        {perms.attach_files}")
    print(f"Read History:        {perms.read_message_history}")
    print("====================================\n")


@bot.event
async def on_member_join(member: discord.Member):
    await send_welcome_message(member)


@bot.tree.command(
    name="test_welcome",
    description="Test Cody's welcome message in the configured welcome channel.",
)
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
async def test_welcome(interaction: discord.Interaction):
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


@bot.tree.command(
    name="ping",
    description="Check whether ETH Battlecode Command is online."
)
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(embed=network_status_embed())


@bot.tree.command(
    name="about",
    description="Information about ETH Battlecode."
)
async def about(interaction: discord.Interaction):
    await interaction.response.send_message(embed=about_embed())


bot.run(TOKEN)
