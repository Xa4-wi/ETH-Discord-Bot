"""Persistent Discord ticket entry point and staff actions."""

from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from cody.config import (
    ADMIN_ROLE_ID,
    ORGANIZER_ROLE_ID,
    SUPPORT_CHANNEL_ID,
    TICKET_CATEGORY_ID,
)
from cody.features.tickets.models import Ticket, TicketCategory, TicketStatus
from cody.features.tickets.repository import (
    InMemoryTicketRepository,
    OpenTicketExists,
    TicketAlreadyClaimed,
    TicketNotAssignedToOrganizer,
    TicketNotFound,
)
from cody.features.tickets.service import TicketService, TicketSetupError
from cody.features.tickets.views import (
    PANEL_MARKER,
    SupportPanelView,
    TicketActionsView,
    support_panel_embed,
    update_ticket_embed,
)
from cody.shared.colors import CodyColor
from cody.shared.components import cody_embed
from cody.shared.permissions import admin_only, is_ticket_staff


LOGGER = logging.getLogger(__name__)


@app_commands.default_permissions(administrator=True)
class TicketCog(
    commands.GroupCog,
    group_name="tickets",
    group_description="Configure and inspect Cody's support tickets.",
):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.repository = InMemoryTicketRepository()
        self.service = TicketService(bot, self.repository)
        self._ready_initialised = False

        # Stable custom IDs keep both entry and staff actions alive after restarts.
        self.bot.add_view(SupportPanelView(self))
        self.bot.add_view(TicketActionsView(self))

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if self._ready_initialised:
            return

        channel = self._support_channel()
        if channel is None:
            LOGGER.error(
                "Support channel %s was not found or is not visible",
                SUPPORT_CHANNEL_ID,
            )
            return

        try:
            await self.service.recover_active_tickets(channel.guild)
            await self.ensure_support_panel(channel)
        except TicketSetupError as error:
            LOGGER.error("Ticket setup is incomplete: %s", error)
            return
        except (discord.Forbidden, discord.HTTPException):
            LOGGER.exception("Could not initialise the Discord ticket system")
            return

        self._ready_initialised = True
        LOGGER.info(
            "Ticket system online | support=%s category=%s",
            SUPPORT_CHANNEL_ID,
            TICKET_CATEGORY_ID,
        )

    async def show_existing_ticket(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "Tickets can only be opened inside the configured server.",
                ephemeral=True,
            )
            return True
        if not self._interaction_uses_configured_guild(interaction):
            await interaction.response.send_message(
                "This ticket panel does not belong to Cody's configured support server.",
                ephemeral=True,
            )
            return True

        ticket = await self.service.open_ticket_for_user(interaction.user.id)
        if ticket is None:
            return False

        channel_reference = (
            f"<#{ticket.discord_channel_id}>"
            if ticket.discord_channel_id is not None
            else "your existing ticket"
        )
        await interaction.response.send_message(
            f"You already have an active ticket: {channel_reference}.",
            ephemeral=True,
        )
        return True

    async def submit_ticket_modal(
        self,
        interaction: discord.Interaction,
        *,
        category: TicketCategory,
        subject: str,
        description: str,
        attempted_solution: str,
    ) -> None:
        if (
            not isinstance(interaction.user, discord.Member)
            or interaction.guild is None
            or not self._interaction_uses_configured_guild(interaction)
        ):
            await interaction.response.send_message(
                "Tickets can only be opened inside Cody's configured support server.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            ticket, channel = await self.service.create_ticket(
                guild=interaction.guild,
                member=interaction.user,
                category=category,
                subject=subject,
                description=description,
                attempted_solution=attempted_solution,
                action_view=TicketActionsView(self, status=TicketStatus.OPEN),
            )
        except OpenTicketExists as error:
            existing = error.ticket
            channel_reference = (
                f"<#{existing.discord_channel_id}>"
                if existing.discord_channel_id is not None
                else "your current ticket"
            )
            await interaction.edit_original_response(
                content=f"You already have an active ticket: {channel_reference}."
            )
            return
        except TicketSetupError as error:
            LOGGER.error("Ticket could not be opened: %s", error)
            await interaction.edit_original_response(
                content=f"Cody's ticket setup needs attention: {error}"
            )
            return
        except (discord.Forbidden, discord.HTTPException):
            LOGGER.exception("Discord rejected creation of a support ticket")
            await interaction.edit_original_response(
                content=(
                    "Cody could not create the private ticket channel. "
                    "An Admin can run `/tickets status` to check the setup."
                )
            )
            return
        except Exception:
            LOGGER.exception("Unexpected failure while opening a support ticket")
            await interaction.edit_original_response(
                content="Cody could not open the ticket. The failure was sent to the operations log."
            )
            return

        await interaction.edit_original_response(
            content=f"Ticket **{ticket.display_id}** is ready: {channel.mention}"
        )

    async def claim_ticket(self, interaction: discord.Interaction) -> None:
        if not await self._require_staff(interaction):
            return
        channel = self._interaction_ticket_channel(interaction)
        if channel is None:
            await interaction.response.send_message(
                "Ticket controls can only be used inside a ticket channel.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            ticket = await self.service.claim(channel, interaction.user.id)
        except TicketAlreadyClaimed as error:
            await interaction.edit_original_response(
                content=(
                    "This ticket is already claimed by "
                    f"<@{error.ticket.assigned_organizer_id}>."
                )
            )
            return
        except (TicketNotFound, TicketSetupError) as error:
            await interaction.edit_original_response(content=str(error))
            return

        refreshed = await self._refresh_ticket_message(interaction, ticket)
        await interaction.edit_original_response(
            content=(
                f"Ticket **{ticket.display_id}** is now assigned to you."
                if refreshed
                else (
                    f"Ticket **{ticket.display_id}** was assigned, but Cody could "
                    "not refresh the ticket card. The issue was logged."
                )
            )
        )

    async def release_ticket(self, interaction: discord.Interaction) -> None:
        if not await self._require_staff(interaction):
            return
        channel = self._interaction_ticket_channel(interaction)
        if channel is None:
            await interaction.response.send_message(
                "Ticket controls can only be used inside a ticket channel.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            ticket = await self.service.release(channel, interaction.user.id)
        except TicketNotAssignedToOrganizer:
            await interaction.edit_original_response(
                content="Only the staff member assigned to this ticket can release it."
            )
            return
        except (TicketNotFound, TicketSetupError) as error:
            await interaction.edit_original_response(content=str(error))
            return

        refreshed = await self._refresh_ticket_message(interaction, ticket)
        await interaction.edit_original_response(
            content=(
                f"Ticket **{ticket.display_id}** is unclaimed again."
                if refreshed
                else (
                    f"Ticket **{ticket.display_id}** was released, but Cody could "
                    "not refresh the ticket card. The issue was logged."
                )
            )
        )

    async def resolve_ticket(self, interaction: discord.Interaction) -> None:
        if not await self._require_staff(interaction):
            return
        channel = self._interaction_ticket_channel(interaction)
        if channel is None:
            await interaction.response.send_message(
                "Ticket controls can only be used inside a ticket channel.",
                ephemeral=True,
            )
            return

        try:
            ticket = await self.service.resolve(channel, interaction.user.id)
        except (TicketNotFound, TicketSetupError) as error:
            await interaction.response.edit_message(content=str(error), view=None)
            return

        await interaction.response.edit_message(
            content=(
                f"Ticket **{ticket.display_id}** tagged **RESOLVED**. "
                "The private channel is being removed; no transcript was saved."
            ),
            view=None,
        )
        try:
            await channel.delete(
                reason=(
                    f"Cody ticket {ticket.display_id} resolved by {interaction.user.id}; "
                    "no transcript retained"
                )
            )
        except (discord.Forbidden, discord.HTTPException):
            LOGGER.exception(
                "Ticket %s was resolved but channel %s could not be deleted",
                ticket.display_id,
                channel.id,
            )
            await interaction.followup.send(
                "The ticket is resolved, but Cody could not delete the channel. "
                "Please ask an Admin to remove it manually.",
                ephemeral=True,
            )

    @app_commands.command(
        name="setup",
        description="Create or refresh Cody's support ticket panel.",
    )
    @admin_only()
    async def setup_panel(self, interaction: discord.Interaction) -> None:
        channel = self._support_channel()
        if channel is None or interaction.guild_id != channel.guild.id:
            await interaction.response.send_message(
                "The configured support channel could not be resolved.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            await self.service.recover_active_tickets(channel.guild)
            message = await self.ensure_support_panel(channel)
        except (TicketSetupError, discord.Forbidden, discord.HTTPException) as error:
            LOGGER.exception("Ticket panel setup failed")
            await interaction.edit_original_response(
                content=f"Ticket panel setup failed: {error}"
            )
            return
        self._ready_initialised = True
        await interaction.edit_original_response(
            content=f"Ticket panel is ready in {channel.mention}: {message.jump_url}"
        )

    @app_commands.command(
        name="status",
        description="Check Cody's ticket channels, roles, and permissions.",
    )
    @admin_only()
    async def status(self, interaction: discord.Interaction) -> None:
        support = self._support_channel()
        if support is None or interaction.guild_id != support.guild.id:
            await interaction.response.send_message(
                "The configured support channel could not be resolved.",
                ephemeral=True,
            )
            return

        guild = support.guild
        category = guild.get_channel(TICKET_CATEGORY_ID)
        admin_role = guild.get_role(ADMIN_ROLE_ID)
        organizer_role = guild.get_role(ORGANIZER_ROLE_ID)
        bot_member = guild.me
        permissions = (
            support.permissions_for(bot_member) if bot_member is not None else None
        )
        category_permissions = (
            category.permissions_for(bot_member)
            if isinstance(category, discord.CategoryChannel)
            and bot_member is not None
            else None
        )
        active = await self.service.active_count()
        ready = (
            isinstance(category, discord.CategoryChannel)
            and admin_role is not None
            and organizer_role is not None
            and permissions is not None
            and permissions.view_channel
            and permissions.send_messages
            and permissions.embed_links
            and permissions.read_message_history
            and category_permissions is not None
            and category_permissions.view_channel
            and category_permissions.manage_channels
        )
        embed = cody_embed(
            title="TICKET SYSTEM STATUS",
            description=(
                "Ticket setup is operational."
                if ready
                else "Ticket setup needs attention."
            ),
            color=CodyColor.SUCCESS if ready else CodyColor.WARNING,
        )
        embed.add_field(
            name="Destinations",
            value=(
                f"Support: <#{SUPPORT_CHANNEL_ID}>\n"
                f"Ticket category: <#{TICKET_CATEGORY_ID}>\n"
                f"Active tickets: {active}"
            ),
            inline=False,
        )
        embed.add_field(
            name="Roles",
            value=(
                f"Admin: {'found' if admin_role else 'missing'}\n"
                f"Organiser: {'found' if organizer_role else 'missing'}"
            ),
            inline=True,
        )
        embed.add_field(
            name="Support permissions",
            value=(
                "Cody member missing"
                if permissions is None
                else (
                    f"View: {'yes' if permissions.view_channel else 'no'}\n"
                    f"Send: {'yes' if permissions.send_messages else 'no'}\n"
                    f"Embeds: {'yes' if permissions.embed_links else 'no'}\n"
                    f"History: {'yes' if permissions.read_message_history else 'no'}\n"
                    "Ticket category: "
                    + (
                        "missing"
                        if category_permissions is None
                        else (
                            "view=yes, manage=yes"
                            if category_permissions.view_channel
                            and category_permissions.manage_channels
                            else (
                                f"view={'yes' if category_permissions.view_channel else 'no'}, "
                                f"manage={'yes' if category_permissions.manage_channels else 'no'}"
                            )
                        )
                    )
                )
            ),
            inline=True,
        )
        embed.add_field(
            name="Retention",
            value=(
                "Temporary memory only. Closing tags the ticket RESOLVED, emits safe "
                "metadata to Cody's log, deletes the channel, and saves no transcript."
            ),
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def ensure_support_panel(
        self,
        channel: discord.TextChannel,
    ) -> discord.Message:
        panel: discord.Message | None = None
        async for message in channel.history(limit=50):
            if self.bot.user is None or message.author.id != self.bot.user.id:
                continue
            if any(
                embed.footer.text == PANEL_MARKER
                for embed in message.embeds
                if embed.footer is not None
            ):
                panel = message
                break

        view = SupportPanelView(self)
        if panel is not None:
            await panel.edit(embed=support_panel_embed(), view=view)
            return panel
        return await channel.send(embed=support_panel_embed(), view=view)

    async def _require_staff(self, interaction: discord.Interaction) -> bool:
        if is_ticket_staff(interaction.user):
            return True
        message = "Only the configured Admin or Organiser role can manage tickets."
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
        return False

    def _interaction_ticket_channel(
        self,
        interaction: discord.Interaction,
    ) -> discord.TextChannel | None:
        if isinstance(interaction.channel, discord.TextChannel):
            return interaction.channel
        return None

    async def _refresh_ticket_message(
        self,
        interaction: discord.Interaction,
        ticket: Ticket,
    ) -> bool:
        message = interaction.message
        if message is None:
            return False
        current = message.embeds[0] if message.embeds else None
        try:
            await message.edit(
                embed=update_ticket_embed(ticket, current),
                view=TicketActionsView(self, status=ticket.status),
            )
        except (discord.Forbidden, discord.HTTPException):
            LOGGER.exception(
                "Ticket %s state changed but message card could not be refreshed",
                ticket.display_id,
            )
            return False
        return True

    def _support_channel(self) -> discord.TextChannel | None:
        channel = self.bot.get_channel(SUPPORT_CHANNEL_ID)
        return channel if isinstance(channel, discord.TextChannel) else None

    def _interaction_uses_configured_guild(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        support = self._support_channel()
        return support is not None and interaction.guild_id == support.guild.id


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TicketCog(bot))
