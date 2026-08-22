"""Message content and delivery functions for Cody."""

import discord

from cody_style import CodyColor, cody_embed
from welcome_card import create_welcome_card


WELCOME_CHANNEL_ID = 1540841975320813649
RULES_CHANNEL_ID = 1540846388328275990
WORLD_CHANNEL_ID = 1540846427377373284


def network_status_embed() -> discord.Embed:
    """Build Cody's successful network-status response."""

    return cody_embed(
        title="NETWORK STATUS",
        description="Command network operational.",
        color=CodyColor.SUCCESS,
    )


def about_embed() -> discord.Embed:
    """Build Cody's identification response."""

    return cody_embed(
        title="SYSTEM IDENTIFICATION",
        description="**ETH Battlecode**\n\nBuild. Adapt. Compete.",
        color=CodyColor.SYSTEM,
    )


def welcome_view(
    member: discord.Member,
    card_filename: str,
) -> discord.ui.LayoutView:
    """Build Cody's Components V2 welcome interface for a member."""

    guild_url = f"https://discord.com/channels/{member.guild.id}"

    card = discord.ui.MediaGallery(
        discord.MediaGalleryItem(
            media=f"attachment://{card_filename}",
            description=(
                f"ETH Battlecode arrival registry for {member.display_name}"
            ),
        ),
    )

    routes = discord.ui.TextDisplay(
        "**INITIAL DIRECTIVES**\n"
        f"{member.mention}, review the network rules, then explore the world."
    )

    navigation = discord.ui.ActionRow(
        discord.ui.Button(
            style=discord.ButtonStyle.link,
            label="Rules",
            url=f"{guild_url}/{RULES_CHANNEL_ID}",
        ),
        discord.ui.Button(
            style=discord.ButtonStyle.link,
            label="Explore World",
            url=f"{guild_url}/{WORLD_CHANNEL_ID}",
        ),
    )

    container = discord.ui.Container(
        card,
        discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
        routes,
        navigation,
        accent_color=int(CodyColor.SYSTEM),
    )

    view = discord.ui.LayoutView(timeout=None)
    view.add_item(container)
    return view


async def send_welcome_message(member: discord.Member) -> bool:
    """Send Cody's Components V2 welcome interface to the welcome channel.

    Returns True when the message was sent, or False when the configured
    welcome channel could not be found.
    """

    channel = member.guild.get_channel(WELCOME_CHANNEL_ID)

    if channel is None:
        print(
            f"Welcome channel {WELCOME_CHANNEL_ID} was not found "
            f"in guild {member.guild.id}."
        )
        return False

    card_buffer = await create_welcome_card(member)
    card_filename = f"arrival_{member.id}.png"
    card_file = discord.File(card_buffer, filename=card_filename)

    await channel.send(
        view=welcome_view(member, card_filename),
        file=card_file,
    )
    return True
