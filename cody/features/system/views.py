"""Responses for Cody's core system commands."""

import discord

from cody.shared.colors import CodyColor
from cody.shared.components import cody_embed


def network_status_embed() -> discord.Embed:
    return cody_embed(
        title="NETWORK STATUS",
        description="Command network operational.",
        color=CodyColor.SUCCESS,
    )


def about_embed() -> discord.Embed:
    return cody_embed(
        title="SYSTEM IDENTIFICATION",
        description="**ETH Battlecode**\n\nBuild. Adapt. Compete.",
        color=CodyColor.SYSTEM,
    )
