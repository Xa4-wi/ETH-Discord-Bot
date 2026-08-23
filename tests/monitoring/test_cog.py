import asyncio
from datetime import datetime, timezone
import logging
from types import SimpleNamespace
import unittest

import discord

from cody.config import LOG_CHANNEL_ID
from cody.features.monitoring.cog import MonitoringCog
from cody.features.monitoring.models import DiscordLogEntry


def entry(message: str) -> DiscordLogEntry:
    return DiscordLogEntry(
        level=logging.INFO,
        level_name="INFO",
        component="Monitoring / Test",
        message=message,
        created_at=datetime.now(timezone.utc),
    )


class MonitoringCogTests(unittest.IsolatedAsyncioTestCase):
    def test_supplied_log_channel_is_the_default(self) -> None:
        self.assertEqual(LOG_CHANNEL_ID, 1541131430682431518)

    def test_admin_commands_and_visibility_are_configured(self) -> None:
        command_checks = {
            command.name: [check.__name__ for check in command.checks]
            for command in MonitoringCog.__cog_app_commands__
        }
        permissions = getattr(
            MonitoringCog,
            "__discord_app_commands_default_permissions__",
        )

        self.assertEqual(
            command_checks,
            {
                "status": ["admin_access_check"],
                "test": ["admin_access_check"],
            },
        )
        self.assertEqual(
            permissions,
            discord.Permissions(administrator=True),
        )

    async def test_queue_overflow_keeps_newest_entries(self) -> None:
        cog = MonitoringCog(SimpleNamespace())
        cog.queue = asyncio.Queue(maxsize=2)

        cog._enqueue_nowait(entry("first"))
        cog._enqueue_nowait(entry("second"))
        cog._enqueue_nowait(entry("third"))

        self.assertEqual(cog.dropped_entries, 1)
        self.assertEqual((await cog.queue.get()).message, "second")
        self.assertEqual((await cog.queue.get()).message, "third")


if __name__ == "__main__":
    unittest.main()
