from datetime import datetime, timezone
import unittest

from cody.features.tickets.models import TicketCategory, TicketStatus
from cody.features.tickets.repository import (
    InMemoryTicketRepository,
    OpenTicketExists,
    TicketAlreadyClaimed,
    TicketNotAssignedToOrganizer,
)


NOW = datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc)


async def create_ticket(
    repository: InMemoryTicketRepository,
    user_id: int = 10,
):
    return await repository.create(
        discord_user_id=user_id,
        category=TicketCategory.TECHNICAL,
        subject="Cody cannot connect",
        description="The connection fails after startup.",
        attempted_solution="Restarted Cody.",
        created_at=NOW,
    )


class InMemoryTicketRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.repository = InMemoryTicketRepository()

    async def test_ticket_lifecycle_is_temporary_and_explicit(self) -> None:
        created = await create_ticket(self.repository)
        bound = await self.repository.bind_channel(created.ticket_id, 100)
        claimed = await self.repository.claim(bound.ticket_id, 20)
        released = await self.repository.release(claimed.ticket_id, 20)
        reclaimed = await self.repository.claim(released.ticket_id, 21)
        resolved = await self.repository.resolve(reclaimed.ticket_id, 21, NOW)

        self.assertEqual(created.display_id, "0001")
        self.assertEqual(bound.discord_channel_id, 100)
        self.assertEqual(claimed.status, TicketStatus.CLAIMED)
        self.assertEqual(claimed.assigned_organizer_id, 20)
        self.assertEqual(released.status, TicketStatus.OPEN)
        self.assertIsNone(released.assigned_organizer_id)
        self.assertEqual(resolved.status, TicketStatus.RESOLVED)
        self.assertEqual(resolved.resolved_by_id, 21)
        self.assertEqual(await self.repository.active_count(), 0)
        self.assertIsNone(await self.repository.get_by_channel(100))
        self.assertIsNone(await self.repository.get_open_by_user(10))

    async def test_only_one_active_ticket_is_allowed_per_member(self) -> None:
        first = await create_ticket(self.repository)

        with self.assertRaises(OpenTicketExists) as context:
            await create_ticket(self.repository)

        self.assertEqual(context.exception.ticket, first)

        await self.repository.resolve(first.ticket_id, 20, NOW)
        second = await create_ticket(self.repository)
        self.assertEqual(second.ticket_id, 2)

    async def test_another_staff_member_cannot_take_a_claimed_ticket(self) -> None:
        ticket = await create_ticket(self.repository)
        await self.repository.claim(ticket.ticket_id, 20)

        with self.assertRaises(TicketAlreadyClaimed):
            await self.repository.claim(ticket.ticket_id, 21)

        with self.assertRaises(TicketNotAssignedToOrganizer):
            await self.repository.release(ticket.ticket_id, 21)


if __name__ == "__main__":
    unittest.main()
