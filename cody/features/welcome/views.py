"""Discord layouts and persistent controls for welcome and role onboarding."""

from __future__ import annotations

import re
from typing import Protocol
from urllib.parse import urlsplit

import discord

from cody.config import ROLE_CHANNEL_ID, RULES_CHANNEL_ID
from cody.features.welcome.models import SponsorDecision
from cody.features.welcome.rules import ServerRules
from cody.shared.colors import CodyColor
from cody.shared.components import channel_link_button, cody_embed


ROLE_PANEL_MARKER = "CODY // ACCESS REGISTRY"
RULES_PANEL_PREFIX = "CODY // SERVER RULES // VERSION"
SPONSOR_REVIEW_PREFIX = "CODY // SPONSOR REVIEW"
SPONSOR_REVIEW_PATTERN = re.compile(
    rf"^{re.escape(SPONSOR_REVIEW_PREFIX)} // PENDING // USER ([1-9][0-9]{{0,19}})$"
)


class OnboardingController(Protocol):
    async def accept_rules(self, interaction: discord.Interaction) -> None: ...

    async def select_participant(self, interaction: discord.Interaction) -> None: ...

    async def select_sponsor(self, interaction: discord.Interaction) -> None: ...

    async def select_visitor(self, interaction: discord.Interaction) -> None: ...

    async def review_sponsor(
        self,
        interaction: discord.Interaction,
        decision: SponsorDecision,
    ) -> None: ...


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
        f"{member.mention}, read and accept the rules, then choose your access role."
    )
    navigation = discord.ui.ActionRow(
        channel_link_button(
            "Read & Accept Rules",
            guild_id=member.guild.id,
            channel_id=RULES_CHANNEL_ID,
        ),
        channel_link_button(
            "Choose Role",
            guild_id=member.guild.id,
            channel_id=ROLE_CHANNEL_ID,
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


def role_panel_embed(image_filename: str) -> discord.Embed:
    embed = cody_embed(
        title="ACCESS REGISTRY",
        description=(
            "After accepting the server rules, choose the option that describes "
            "how you are joining ETH Battlecode. Cody will configure your access."
        ),
        color=CodyColor.SYSTEM,
    )
    embed.add_field(
        name="Participant",
        value=(
            "For competitors. Cody verifies that your Discord account is linked "
            "to a participant on the official website."
        ),
        inline=False,
    )
    embed.add_field(
        name="Sponsor",
        value=(
            "Receive temporary Under Review access while an Admin or Organiser "
            "reviews the request."
        ),
        inline=False,
    )
    embed.add_field(
        name="Visitor",
        value="Join the public community areas without participating.",
        inline=False,
    )
    embed.set_image(url=f"attachment://{image_filename}")
    embed.set_footer(text=ROLE_PANEL_MARKER)
    return embed


def rules_panel_embed(rules: ServerRules, image_filename: str) -> discord.Embed:
    embed = cody_embed(
        title=rules.title,
        description=(
            f"{rules.introduction}\n\n"
            f"**Version {rules.version} · Updated {rules.updated}**"
        ),
        color=CodyColor.SYSTEM,
    )
    embed.set_image(url=f"attachment://{image_filename}")
    for rule in rules.rules:
        embed.add_field(name=rule.heading, value=rule.text, inline=False)
    embed.add_field(
        name="Acceptance",
        value=rules.acknowledgement,
        inline=False,
    )
    embed.set_footer(text=f"{RULES_PANEL_PREFIX} {rules.version}")
    return embed


class RulesAcceptanceView(discord.ui.View):
    def __init__(self, controller: OnboardingController) -> None:
        super().__init__(timeout=None)
        self.controller = controller

    @discord.ui.button(
        label="Accept Rules",
        style=discord.ButtonStyle.success,
        emoji="✅",
        custom_id="cody:onboarding:rules:accept",
    )
    async def accept(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        del button
        await self.controller.accept_rules(interaction)


class RoleSelectionView(discord.ui.View):
    def __init__(self, controller: OnboardingController) -> None:
        super().__init__(timeout=None)
        self.controller = controller

    @discord.ui.button(
        label="Participant",
        style=discord.ButtonStyle.primary,
        custom_id="cody:onboarding:participant",
    )
    async def participant(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        del button
        await self.controller.select_participant(interaction)

    @discord.ui.button(
        label="Sponsor",
        style=discord.ButtonStyle.secondary,
        custom_id="cody:onboarding:sponsor",
    )
    async def sponsor(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        del button
        await self.controller.select_sponsor(interaction)

    @discord.ui.button(
        label="Visitor",
        style=discord.ButtonStyle.success,
        custom_id="cody:onboarding:visitor",
    )
    async def visitor(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        del button
        await self.controller.select_visitor(interaction)


class SponsorReviewView(discord.ui.View):
    def __init__(self, controller: OnboardingController) -> None:
        super().__init__(timeout=None)
        self.controller = controller

    @discord.ui.button(
        label="Approve Sponsor",
        style=discord.ButtonStyle.success,
        custom_id="cody:onboarding:sponsor:approve",
    )
    async def approve(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        del button
        await self.controller.review_sponsor(
            interaction,
            SponsorDecision.APPROVED,
        )

    @discord.ui.button(
        label="Reject",
        style=discord.ButtonStyle.danger,
        custom_id="cody:onboarding:sponsor:reject",
    )
    async def reject(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        del button
        await self.controller.review_sponsor(
            interaction,
            SponsorDecision.REJECTED,
        )


def sponsor_review_embed(member: discord.Member) -> discord.Embed:
    embed = cody_embed(
        title="SPONSOR ACCESS REVIEW",
        description=(
            f"{member.mention} requested Sponsor access and now has the "
            "**Under Review** role."
        ),
        color=CodyColor.WARNING,
    )
    embed.add_field(name="Applicant", value=member.mention, inline=True)
    embed.add_field(name="Discord user ID", value=str(member.id), inline=True)
    embed.add_field(name="Status", value="PENDING", inline=True)
    embed.add_field(
        name="Decision",
        value=(
            "Approve to replace Under Review with Sponsor. Reject to replace it "
            "with Visitor access."
        ),
        inline=False,
    )
    embed.set_footer(text=pending_sponsor_marker(member.id))
    return embed


def resolved_sponsor_review_embed(
    current: discord.Embed,
    *,
    applicant_id: int,
    reviewer_id: int,
    decision: SponsorDecision,
) -> discord.Embed:
    embed = discord.Embed.from_dict(current.to_dict())
    status = decision.value.upper()
    for index, field in enumerate(embed.fields):
        if field.name == "Status":
            embed.set_field_at(index, name="Status", value=status, inline=True)
    embed.color = (
        int(CodyColor.SUCCESS)
        if decision is SponsorDecision.APPROVED
        else int(CodyColor.ERROR)
    )
    embed.add_field(name="Reviewed by", value=f"<@{reviewer_id}>", inline=False)
    embed.set_footer(
        text=(
            f"{SPONSOR_REVIEW_PREFIX} // {status} // USER {applicant_id}"
        )
    )
    return embed


def pending_sponsor_marker(user_id: int) -> str:
    return f"{SPONSOR_REVIEW_PREFIX} // PENDING // USER {user_id}"


def sponsor_applicant_id(message: discord.Message | None) -> int | None:
    if message is None or not message.embeds:
        return None
    footer = message.embeds[0].footer
    match = SPONSOR_REVIEW_PATTERN.fullmatch(footer.text or "")
    return int(match.group(1)) if match is not None else None


def website_signup_view(url: str) -> discord.ui.View | None:
    """Build a safe website link without accepting credentials or non-HTTPS URLs."""

    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        return None
    view = discord.ui.View()
    view.add_item(
        discord.ui.Button(
            label="Open ETH Battlecode Website",
            style=discord.ButtonStyle.link,
            url=url,
        )
    )
    return view


def role_channel_link_view(guild_id: int) -> discord.ui.View:
    view = discord.ui.View()
    view.add_item(
        channel_link_button(
            "Choose Access Role",
            guild_id=guild_id,
            channel_id=ROLE_CHANNEL_ID,
        )
    )
    return view


def rules_channel_link_view(guild_id: int) -> discord.ui.View:
    view = discord.ui.View()
    view.add_item(
        channel_link_button(
            "Read & Accept Rules",
            guild_id=guild_id,
            channel_id=RULES_CHANNEL_ID,
        )
    )
    return view
