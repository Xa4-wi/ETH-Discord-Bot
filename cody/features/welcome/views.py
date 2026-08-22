"""Components V2 layouts for the welcome feature."""

import discord

from cody.config import RULES_CHANNEL_ID, WORLD_CHANNEL_ID
from cody.shared.colors import CodyColor
from cody.shared.components import channel_link_button


def welcome_view(
    member: discord.Member,
    card_filename: str,
) -> discord.ui.LayoutView:
    card = discord.ui.MediaGallery(
        discord.MediaGalleryItem(
            media=f"attachment://{card_filename}",
            description=(
                f"ETH Battlecode arrival registry for {member.display_name}"
            ),
        ),
    )
    directives = discord.ui.TextDisplay(
        "**INITIAL DIRECTIVES**\n"
        f"{member.mention}, review the network rules, then explore the world."
    )
    navigation = discord.ui.ActionRow(
        channel_link_button(
            "Rules",
            guild_id=member.guild.id,
            channel_id=RULES_CHANNEL_ID,
        ),
        channel_link_button(
            "Explore World",
            guild_id=member.guild.id,
            channel_id=WORLD_CHANNEL_ID,
        ),
    )
    container = discord.ui.Container(
        card,
        discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
        directives,
        navigation,
        accent_color=int(CodyColor.SYSTEM),
    )

    view = discord.ui.LayoutView(timeout=None)
    view.add_item(container)
    return view
