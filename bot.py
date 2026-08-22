import os
import discord
from discord import app_commands

TOKEN = os.environ["DISCORD_TOKEN"]

class BattlecodeBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()

        super().__init__(intents=intents)

        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()


bot = BattlecodeBot()


@bot.event
async def on_ready():
    print(f"ETH Battlecode online as {bot.user}")


@bot.tree.command(
    name="ping",
    description="Check whether ETH Battlecode Command is online."
)
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(
        "Command network operational."
    )


@bot.tree.command(
    name="about",
    description="Information about ETH Battlecode."
)
async def about(interaction: discord.Interaction):

    embed = discord.Embed(
        title="ETH Battlecode",
        description=(
            "Welcome to ETH Battlecode.\n\n"
            "Build. Adapt. Compete."
        )
    )

    await interaction.response.send_message(embed=embed)


bot.run(TOKEN)