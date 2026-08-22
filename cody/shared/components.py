"""Reusable Discord components and traditional embeds."""

import discord

from cody.shared.colors import CodyColor


def cody_embed(
    title: str,
    description: str,
    *,
    color: CodyColor = CodyColor.SYSTEM,
) -> discord.Embed:
    embed = discord.Embed(
        title=title.upper(),
        description=description,
        color=int(color),
    )
    embed.set_footer(text="CODY // NETWORK INTERFACE")
    return embed


def channel_link_button(
    label: str,
    *,
    guild_id: int,
    channel_id: int,
) -> discord.ui.Button:
    return discord.ui.Button(
        style=discord.ButtonStyle.link,
        label=label,
        url=f"https://discord.com/channels/{guild_id}/{channel_id}",
    )
