"""Discord embeds and persistent controls for the ticket workflow."""

from __future__ import annotations

from typing import Protocol

import discord

from cody.config import PARTICIPANT_ROLE_ID
from cody.features.tickets.modals import TicketModal, TicketModalController
from cody.features.tickets.models import Ticket, TicketCategory, TicketStatus
from cody.shared.colors import CodyColor
from cody.shared.components import cody_embed
from cody.shared.permissions import is_ticket_staff, member_has_role


PANEL_MARKER = "CODY // SUPPORT INTERFACE"


class TicketController(TicketModalController, Protocol):
    async def show_existing_ticket(
        self,
        interaction: discord.Interaction,
    ) -> bool: ...

    async def claim_ticket(self, interaction: discord.Interaction) -> None: ...

    async def release_ticket(self, interaction: discord.Interaction) -> None: ...

    async def resolve_ticket(self, interaction: discord.Interaction) -> None: ...


def support_panel_embed() -> discord.Embed:
    embed = cody_embed(
        title="SUPPORT UPLINK",
        description=(
            "Open a private ticket for technical, competition, team, account, "
            "or other support. You can keep one active ticket at a time."
        ),
        color=CodyColor.SYSTEM,
    )
    embed.add_field(
        name="How it works",
        value=(
            "1. Select **Open Ticket**\n"
            "2. Choose a category and answer the short form\n"
            "3. Continue privately with the support team"
        ),
        inline=False,
    )
    embed.set_footer(text=PANEL_MARKER)
    return embed


def ticket_embed(ticket: Ticket) -> discord.Embed:
    embed = cody_embed(
        title=f"SUPPORT TICKET // {ticket.display_id}",
        description="A private support channel has been established.",
        color=CodyColor.WARNING,
    )
    embed.add_field(
        name="Opened by",
        value=f"<@{ticket.discord_user_id}>",
        inline=True,
    )
    embed.add_field(
        name="Category",
        value=ticket.category.display_name,
        inline=True,
    )
    embed.add_field(name="Status", value="OPEN", inline=True)
    embed.add_field(name="Subject", value=ticket.subject, inline=False)
    embed.add_field(name="Description", value=ticket.description, inline=False)
    embed.add_field(
        name="Already tried",
        value=ticket.attempted_solution or "Nothing provided.",
        inline=False,
    )
    embed.add_field(name="Assigned to", value="Unclaimed", inline=False)
    return embed


def update_ticket_embed(
    ticket: Ticket,
    current: discord.Embed | None,
) -> discord.Embed:
    """Update status fields without rebuilding or persisting submitted content."""

    embed = (
        discord.Embed.from_dict(current.to_dict())
        if current is not None
        else ticket_embed(ticket)
    )
    status = ticket.status.value.upper()
    assigned = (
        f"<@{ticket.assigned_organizer_id}>"
        if ticket.assigned_organizer_id is not None
        else "Unclaimed"
    )
    for index, field in enumerate(embed.fields):
        if field.name == "Status":
            embed.set_field_at(index, name="Status", value=status, inline=True)
        elif field.name == "Assigned to":
            embed.set_field_at(
                index,
                name="Assigned to",
                value=assigned,
                inline=False,
            )
    embed.color = (
        int(CodyColor.SUCCESS)
        if ticket.status is TicketStatus.RESOLVED
        else int(CodyColor.WARNING)
    )
    return embed


class SupportPanelView(discord.ui.View):
    def __init__(self, controller: TicketController) -> None:
        super().__init__(timeout=None)
        self.controller = controller

    @discord.ui.button(
        label="Open Ticket",
        style=discord.ButtonStyle.primary,
        emoji="🎫",
        custom_id="cody:tickets:open",
    )
    async def open_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        del button
        if not (
            member_has_role(interaction.user, PARTICIPANT_ROLE_ID)
            or is_ticket_staff(interaction.user)
        ):
            await interaction.response.send_message(
                "The Participant role is required to open a support ticket.",
                ephemeral=True,
            )
            return
        if await self.controller.show_existing_ticket(interaction):
            return
        await interaction.response.send_message(
            "Choose the category that best matches your request.",
            view=TicketCategoryView(self.controller),
            ephemeral=True,
        )


class TicketCategorySelect(discord.ui.Select):
    def __init__(self, controller: TicketController) -> None:
        options = [
            discord.SelectOption(
                label=category.display_name,
                value=category.value,
                description={
                    TicketCategory.TECHNICAL: "Bot, Discord, or technical problems",
                    TicketCategory.COMPETITION: "Matches, rules, or competition questions",
                    TicketCategory.TEAM: "Team membership and coordination",
                    TicketCategory.ACCOUNT: "Account and access help",
                    TicketCategory.OTHER: "Anything not covered above",
                }[category],
            )
            for category in TicketCategory
        ]
        super().__init__(
            placeholder="Select a support category",
            min_values=1,
            max_values=1,
            options=options,
        )
        self.controller = controller

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(
            TicketModal(self.controller, TicketCategory(self.values[0]))
        )


class TicketCategoryView(discord.ui.View):
    def __init__(self, controller: TicketController) -> None:
        super().__init__(timeout=300)
        self.add_item(TicketCategorySelect(controller))


class TicketActionsView(discord.ui.View):
    def __init__(
        self,
        controller: TicketController,
        status: TicketStatus | None = None,
    ) -> None:
        super().__init__(timeout=None)
        self.controller = controller
        for child in self.children:
            if not isinstance(child, discord.ui.Button):
                continue
            if status is None:
                continue
            if child.custom_id == "cody:tickets:claim":
                child.disabled = status is TicketStatus.CLAIMED
            elif child.custom_id == "cody:tickets:release":
                child.disabled = status is not TicketStatus.CLAIMED

    @discord.ui.button(
        label="Claim",
        style=discord.ButtonStyle.success,
        custom_id="cody:tickets:claim",
    )
    async def claim(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        del button
        await self.controller.claim_ticket(interaction)

    @discord.ui.button(
        label="Release",
        style=discord.ButtonStyle.secondary,
        custom_id="cody:tickets:release",
    )
    async def release(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        del button
        await self.controller.release_ticket(interaction)

    @discord.ui.button(
        label="Resolve",
        style=discord.ButtonStyle.danger,
        custom_id="cody:tickets:resolve",
    )
    async def resolve(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        del button
        if not is_ticket_staff(interaction.user):
            await interaction.response.send_message(
                "Only the Admin or Organiser role can resolve tickets.",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            "Resolve this ticket and delete its private channel? No transcript will be saved.",
            view=ResolveConfirmationView(self.controller),
            ephemeral=True,
        )


class ResolveConfirmationView(discord.ui.View):
    def __init__(self, controller: TicketController) -> None:
        super().__init__(timeout=60)
        self.controller = controller

    @discord.ui.button(label="Resolve ticket", style=discord.ButtonStyle.danger)
    async def confirm(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        del button
        await self.controller.resolve_ticket(interaction)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        del button
        await interaction.response.edit_message(
            content="Ticket resolution cancelled.",
            view=None,
        )
