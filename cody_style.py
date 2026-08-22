"""Shared visual language for messages sent by Cody."""

from enum import IntEnum

import discord


class CodyColor(IntEnum):
    """Accent colors for Cody's standard message types."""

    SYSTEM = 0xE8A13C
    SUCCESS = 0x7BD389
    WARNING = 0xD8A14A
    ERROR = 0x8C3F22
    UMBRAL = 0x244D3B
    MIDLEVELS = 0x8F8066
    CITADELS = 0xF1C75B


def cody_embed(
    title: str,
    description: str,
    *,
    color: CodyColor = CodyColor.SYSTEM,
) -> discord.Embed:
    """Create an embed with Cody's consistent system-interface styling."""

    embed = discord.Embed(
        title=title.upper(),
        description=description,
        color=int(color),
    )
    embed.set_footer(text="CODY // NETWORK INTERFACE")
    return embed
