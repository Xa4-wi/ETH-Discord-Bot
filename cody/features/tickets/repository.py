"""Temporary Discord ticket workflow state and in-memory implementation."""

from __future__ import annotations

import asyncio
from datetime import datetime
from dataclasses import replace
from typing import Protocol

from cody.features.tickets.models import Ticket, TicketCategory, TicketStatus


class TicketRepositoryError(RuntimeError):
    """Base class for ticket state errors."""


class OpenTicketExists(TicketRepositoryError):
    def __init__(self, ticket: Ticket) -> None:
        super().__init__("The member already has an open ticket.")
        self.ticket = ticket


class TicketNotFound(TicketRepositoryError):
    pass


class TicketAlreadyClaimed(TicketRepositoryError):
    def __init__(self, ticket: Ticket) -> None:
        super().__init__("The ticket is already claimed.")
        self.ticket = ticket


class TicketNotAssignedToOrganizer(TicketRepositoryError):
    pass


class TicketRepository(Protocol):
    """Local workflow-state contract, including Discord channel recovery.

    This deliberately is not the canonical Main Backend ticket gateway. The
    backend and Discord-routing responsibilities will be split before durable
    ticket integration.
    """

    async def create(
        self,
        *,
        discord_user_id: int,
        category: TicketCategory,
        subject: str,
        description: str,
        attempted_solution: str,
        created_at: datetime,
    ) -> Ticket: ...

    async def bind_channel(self, ticket_id: int, channel_id: int) -> Ticket: ...

    async def get_by_channel(self, channel_id: int) -> Ticket | None: ...

    async def get_open_by_user(self, user_id: int) -> Ticket | None: ...

    async def claim(self, ticket_id: int, organizer_id: int) -> Ticket: ...

    async def release(self, ticket_id: int, organizer_id: int) -> Ticket: ...

    async def resolve(self, ticket_id: int, organizer_id: int, at: datetime) -> Ticket: ...

    async def discard(self, ticket_id: int) -> None: ...

    async def restore(self, ticket: Ticket) -> Ticket: ...

    async def active_count(self) -> int: ...


class InMemoryTicketRepository:
    """Temporary ticket state; intentionally writes nothing to disk."""

    def __init__(self) -> None:
        self._tickets: dict[int, Ticket] = {}
        self._next_id = 1
        self._lock = asyncio.Lock()

    async def create(
        self,
        *,
        discord_user_id: int,
        category: TicketCategory,
        subject: str,
        description: str,
        attempted_solution: str,
        created_at: datetime,
    ) -> Ticket:
        async with self._lock:
            existing = self._open_for_user(discord_user_id)
            if existing is not None:
                raise OpenTicketExists(existing)

            ticket = Ticket(
                ticket_id=self._next_id,
                discord_user_id=discord_user_id,
                category=category,
                subject=subject,
                description=description,
                attempted_solution=attempted_solution,
                status=TicketStatus.OPEN,
                created_at=created_at,
            )
            self._tickets[ticket.ticket_id] = ticket
            self._next_id += 1
            return ticket

    async def bind_channel(self, ticket_id: int, channel_id: int) -> Ticket:
        async with self._lock:
            ticket = self._required(ticket_id)
            updated = replace(ticket, discord_channel_id=channel_id)
            self._tickets[ticket_id] = updated
            return updated

    async def get_by_channel(self, channel_id: int) -> Ticket | None:
        async with self._lock:
            return next(
                (
                    ticket
                    for ticket in self._tickets.values()
                    if ticket.discord_channel_id == channel_id
                    and ticket.status is not TicketStatus.RESOLVED
                ),
                None,
            )

    async def get_open_by_user(self, user_id: int) -> Ticket | None:
        async with self._lock:
            return self._open_for_user(user_id)

    async def claim(self, ticket_id: int, organizer_id: int) -> Ticket:
        async with self._lock:
            ticket = self._required(ticket_id)
            if ticket.status is TicketStatus.CLAIMED:
                if ticket.assigned_organizer_id == organizer_id:
                    return ticket
                raise TicketAlreadyClaimed(ticket)
            if ticket.status is TicketStatus.RESOLVED:
                raise TicketNotFound("The ticket is already resolved.")

            updated = replace(
                ticket,
                status=TicketStatus.CLAIMED,
                assigned_organizer_id=organizer_id,
            )
            self._tickets[ticket_id] = updated
            return updated

    async def release(self, ticket_id: int, organizer_id: int) -> Ticket:
        async with self._lock:
            ticket = self._required(ticket_id)
            if ticket.assigned_organizer_id != organizer_id:
                raise TicketNotAssignedToOrganizer(
                    "Only the assigned organizer can release this ticket."
                )
            updated = replace(
                ticket,
                status=TicketStatus.OPEN,
                assigned_organizer_id=None,
            )
            self._tickets[ticket_id] = updated
            return updated

    async def resolve(
        self,
        ticket_id: int,
        organizer_id: int,
        at: datetime,
    ) -> Ticket:
        async with self._lock:
            ticket = self._required(ticket_id)
            if ticket.status is TicketStatus.RESOLVED:
                return ticket
            updated = replace(
                ticket,
                status=TicketStatus.RESOLVED,
                assigned_organizer_id=(
                    ticket.assigned_organizer_id or organizer_id
                ),
                resolved_at=at,
                resolved_by_id=organizer_id,
            )
            # This temporary provider retains no closed form content. A future
            # backend provider can persist the returned RESOLVED state.
            self._tickets.pop(ticket_id, None)
            return updated

    async def discard(self, ticket_id: int) -> None:
        async with self._lock:
            self._tickets.pop(ticket_id, None)

    async def restore(self, ticket: Ticket) -> Ticket:
        async with self._lock:
            existing = self._tickets.get(ticket.ticket_id)
            if existing is not None:
                return existing
            self._tickets[ticket.ticket_id] = ticket
            self._next_id = max(self._next_id, ticket.ticket_id + 1)
            return ticket

    async def active_count(self) -> int:
        async with self._lock:
            return sum(
                ticket.status is not TicketStatus.RESOLVED
                for ticket in self._tickets.values()
            )

    def _required(self, ticket_id: int) -> Ticket:
        try:
            return self._tickets[ticket_id]
        except KeyError as error:
            raise TicketNotFound(f"Ticket {ticket_id} was not found.") from error

    def _open_for_user(self, user_id: int) -> Ticket | None:
        return next(
            (
                ticket
                for ticket in self._tickets.values()
                if ticket.discord_user_id == user_id
                and ticket.status is not TicketStatus.RESOLVED
            ),
            None,
        )
