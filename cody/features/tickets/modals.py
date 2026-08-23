"""Native Discord questionnaire for opening a support ticket."""

from __future__ import annotations

from typing import Protocol

import discord

from cody.features.tickets.models import TicketCategory


class TicketModalController(Protocol):
    async def submit_ticket_modal(
        self,
        interaction: discord.Interaction,
        *,
        category: TicketCategory,
        subject: str,
        description: str,
        attempted_solution: str,
    ) -> None: ...


class TicketModal(discord.ui.Modal):
    subject = discord.ui.TextInput(
        label="Subject",
        placeholder="Briefly describe what you need help with",
        min_length=3,
        max_length=100,
    )
    description = discord.ui.TextInput(
        label="What happened?",
        placeholder="Include the details the support team will need",
        style=discord.TextStyle.paragraph,
        min_length=10,
        max_length=1000,
    )
    attempted_solution = discord.ui.TextInput(
        label="What have you already tried?",
        placeholder="Optional",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=750,
    )

    def __init__(
        self,
        controller: TicketModalController,
        category: TicketCategory,
    ) -> None:
        super().__init__(title=f"{category.display_name} support ticket")
        self.controller = controller
        self.category = category

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self.controller.submit_ticket_modal(
            interaction,
            category=self.category,
            subject=str(self.subject).strip(),
            description=str(self.description).strip(),
            attempted_solution=str(self.attempted_solution).strip(),
        )
