from datetime import datetime, timezone
import unittest

from cody.features.tickets.models import Ticket, TicketCategory, TicketStatus
from cody.features.tickets.service import ticket_from_topic, ticket_topic


class TicketTopicTests(unittest.TestCase):
    def test_topic_recovers_active_state_without_form_content(self) -> None:
        ticket = Ticket(
            ticket_id=42,
            discord_user_id=100,
            category=TicketCategory.COMPETITION,
            subject="Private subject",
            description="Private description",
            attempted_solution="Private attempted solution",
            status=TicketStatus.CLAIMED,
            created_at=datetime(2026, 8, 23, 12, 30, tzinfo=timezone.utc),
            discord_channel_id=200,
            assigned_organizer_id=300,
        )

        topic = ticket_topic(ticket)
        restored = ticket_from_topic(topic, 201)

        self.assertNotIn(ticket.subject, topic)
        self.assertNotIn(ticket.description, topic)
        self.assertNotIn(ticket.attempted_solution, topic)
        self.assertIsNotNone(restored)
        assert restored is not None
        self.assertEqual(restored.ticket_id, ticket.ticket_id)
        self.assertEqual(restored.discord_user_id, ticket.discord_user_id)
        self.assertEqual(restored.category, ticket.category)
        self.assertEqual(restored.status, TicketStatus.CLAIMED)
        self.assertEqual(restored.assigned_organizer_id, 300)
        self.assertEqual(restored.discord_channel_id, 201)
        self.assertEqual(restored.subject, "")

    def test_unrelated_or_malformed_topics_are_ignored(self) -> None:
        self.assertIsNone(ticket_from_topic(None, 1))
        self.assertIsNone(ticket_from_topic("ordinary channel", 1))
        self.assertIsNone(ticket_from_topic("cody-ticket:v1;id=bad", 1))


if __name__ == "__main__":
    unittest.main()
