"""Ticket-channel orchestration independent of Discord interaction layouts."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import re

import discord
from discord.ext import commands

from cody.config import ADMIN_ROLE_ID, ORGANIZER_ROLE_ID, TICKET_CATEGORY_ID
from cody.features.tickets.models import Ticket, TicketCategory, TicketStatus
from cody.features.tickets.repository import TicketRepository
from cody.features.tickets.views import ticket_embed


LOGGER = logging.getLogger(__name__)
TOPIC_PREFIX = "cody-ticket:v1"


class TicketSetupError(RuntimeError):
    """Raised when Cody cannot resolve the configured ticket resources."""


class TicketService:
    """Create and update private ticket channels using replaceable storage."""

    def __init__(self, bot: commands.Bot, repository: TicketRepository) -> None:
        self.bot = bot
        self.repository = repository

    async def create_ticket(
        self,
        *,
        guild: discord.Guild,
        member: discord.Member,
        category: TicketCategory,
        subject: str,
        description: str,
        attempted_solution: str,
        action_view: discord.ui.View,
    ) -> tuple[Ticket, discord.TextChannel]:
        ticket_category = self._ticket_category(guild)
        admin_role = self._required_role(guild, ADMIN_ROLE_ID, "Admin")
        organizer_role = self._required_role(guild, ORGANIZER_ROLE_ID, "Organiser")
        bot_member = guild.me
        if bot_member is None:
            raise TicketSetupError("Cody could not resolve its server member.")

        created_at = datetime.now(timezone.utc)
        ticket = await self.repository.create(
            discord_user_id=member.id,
            category=category,
            subject=subject,
            description=description,
            attempted_solution=attempted_solution,
            created_at=created_at,
        )

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: self._member_overwrite(),
            admin_role: self._staff_overwrite(),
            organizer_role: self._staff_overwrite(),
            bot_member: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True,
                manage_channels=True,
                manage_messages=True,
            ),
        }

        channel: discord.TextChannel | None = None
        try:
            channel = await guild.create_text_channel(
                self._channel_name(ticket, subject),
                category=ticket_category,
                overwrites=overwrites,
                topic=ticket_topic(ticket),
                reason=f"Cody support ticket {ticket.display_id} opened by {member.id}",
            )
            ticket = await self.repository.bind_channel(ticket.ticket_id, channel.id)
            await channel.send(
                content=(
                    f"{member.mention} {admin_role.mention} {organizer_role.mention}"
                ),
                embed=ticket_embed(ticket),
                view=action_view,
                allowed_mentions=discord.AllowedMentions(
                    users=True,
                    roles=True,
                    everyone=False,
                ),
            )
        except Exception:
            await self.repository.discard(ticket.ticket_id)
            if channel is not None:
                try:
                    await channel.delete(reason="Ticket setup did not complete")
                except (discord.Forbidden, discord.HTTPException):
                    LOGGER.exception(
                        "Could not remove incomplete ticket channel %s",
                        channel.id,
                    )
            raise

        LOGGER.info(
            "Ticket %s opened | member=%s category=%s channel=%s",
            ticket.display_id,
            member.id,
            ticket.category.value,
            channel.id,
        )
        return ticket, channel

    async def ticket_for_channel(self, channel: discord.TextChannel) -> Ticket | None:
        ticket = await self.repository.get_by_channel(channel.id)
        if ticket is not None:
            return ticket

        restored = ticket_from_topic(channel.topic, channel.id)
        if restored is None:
            return None
        return await self.repository.restore(restored)

    async def open_ticket_for_user(self, user_id: int) -> Ticket | None:
        return await self.repository.get_open_by_user(user_id)

    async def claim(
        self,
        channel: discord.TextChannel,
        organizer_id: int,
    ) -> Ticket:
        ticket = await self._required_ticket(channel)
        updated = await self.repository.claim(ticket.ticket_id, organizer_id)
        await self._update_topic(channel, updated)
        LOGGER.info(
            "Ticket %s claimed | staff=%s channel=%s",
            updated.display_id,
            organizer_id,
            channel.id,
        )
        return updated

    async def release(
        self,
        channel: discord.TextChannel,
        organizer_id: int,
    ) -> Ticket:
        ticket = await self._required_ticket(channel)
        updated = await self.repository.release(ticket.ticket_id, organizer_id)
        await self._update_topic(channel, updated)
        LOGGER.info(
            "Ticket %s released | staff=%s channel=%s",
            updated.display_id,
            organizer_id,
            channel.id,
        )
        return updated

    async def resolve(
        self,
        channel: discord.TextChannel,
        organizer_id: int,
    ) -> Ticket:
        ticket = await self._required_ticket(channel)
        updated = await self.repository.resolve(
            ticket.ticket_id,
            organizer_id,
            datetime.now(timezone.utc),
        )
        await self._update_topic(channel, updated)
        LOGGER.info(
            "Ticket %s RESOLVED | member=%s category=%s staff=%s channel=%s; no transcript saved",
            updated.display_id,
            updated.discord_user_id,
            updated.category.value,
            organizer_id,
            channel.id,
        )
        return updated

    async def recover_active_tickets(self, guild: discord.Guild) -> int:
        category = self._ticket_category(guild)
        recovered = 0
        for channel in category.text_channels:
            ticket = ticket_from_topic(channel.topic, channel.id)
            if ticket is None or ticket.status is TicketStatus.RESOLVED:
                continue
            await self.repository.restore(ticket)
            recovered += 1

        if recovered:
            LOGGER.info("Recovered %d active ticket channel(s)", recovered)
        return recovered

    async def active_count(self) -> int:
        return await self.repository.active_count()

    async def _required_ticket(self, channel: discord.TextChannel) -> Ticket:
        ticket = await self.ticket_for_channel(channel)
        if ticket is None:
            raise TicketSetupError("This is not an active Cody ticket channel.")
        return ticket

    async def _update_topic(
        self,
        channel: discord.TextChannel,
        ticket: Ticket,
    ) -> None:
        try:
            await channel.edit(
                topic=ticket_topic(ticket),
                reason=f"Cody ticket {ticket.display_id} state changed",
            )
        except (discord.Forbidden, discord.HTTPException):
            LOGGER.exception(
                "Ticket %s state changed but channel topic %s could not be updated",
                ticket.display_id,
                channel.id,
            )

    @staticmethod
    def _ticket_category(guild: discord.Guild) -> discord.CategoryChannel:
        channel = guild.get_channel(TICKET_CATEGORY_ID)
        if not isinstance(channel, discord.CategoryChannel):
            raise TicketSetupError(
                f"Ticket category {TICKET_CATEGORY_ID} was not found or is not visible to Cody."
            )
        return channel

    @staticmethod
    def _required_role(guild: discord.Guild, role_id: int, name: str) -> discord.Role:
        role = guild.get_role(role_id)
        if role is None:
            raise TicketSetupError(
                f"The configured {name} role {role_id} was not found."
            )
        return role

    @staticmethod
    def _channel_name(ticket: Ticket, subject: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", subject.lower()).strip("-")
        return f"ticket-{ticket.display_id}-{slug[:55] or 'support'}"

    @staticmethod
    def _member_overwrite() -> discord.PermissionOverwrite:
        return discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True,
        )

    @staticmethod
    def _staff_overwrite() -> discord.PermissionOverwrite:
        return discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True,
            manage_messages=True,
        )


def ticket_topic(ticket: Ticket) -> str:
    """Encode only temporary routing/state metadata in a channel topic."""

    assigned = ticket.assigned_organizer_id or 0
    created = int(ticket.created_at.timestamp())
    return (
        f"{TOPIC_PREFIX};id={ticket.ticket_id};owner={ticket.discord_user_id};"
        f"category={ticket.category.value};status={ticket.status.value};"
        f"assigned={assigned};created={created}"
    )


def ticket_from_topic(topic: str | None, channel_id: int) -> Ticket | None:
    """Rebuild active state after restart without storing ticket content."""

    if not topic or not topic.startswith(f"{TOPIC_PREFIX};"):
        return None
    try:
        values = dict(part.split("=", 1) for part in topic.split(";")[1:])
        assigned = int(values["assigned"])
        return Ticket(
            ticket_id=int(values["id"]),
            discord_user_id=int(values["owner"]),
            category=TicketCategory(values["category"]),
            subject="",
            description="",
            attempted_solution="",
            status=TicketStatus(values["status"]),
            created_at=datetime.fromtimestamp(
                int(values["created"]),
                tz=timezone.utc,
            ),
            discord_channel_id=channel_id,
            assigned_organizer_id=assigned or None,
        )
    except (KeyError, TypeError, ValueError):
        LOGGER.warning("Ignored malformed ticket metadata on channel %s", channel_id)
        return None
