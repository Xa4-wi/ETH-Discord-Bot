from datetime import datetime, timezone
import logging
import sys
import unittest

from cody.features.monitoring.models import DiscordLogEntry
from cody.features.monitoring.service import (
    DiscordLogHandler,
    MAX_DISCORD_LOG_MESSAGE,
    component_name,
    log_entry_embed,
    log_entry_from_record,
    sanitize_log_message,
)
from cody.shared.colors import CodyColor


def log_record(
    name: str,
    message: str,
    *,
    level: int = logging.INFO,
    exc_info=None,
) -> logging.LogRecord:
    return logging.LogRecord(
        name=name,
        level=level,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=exc_info,
    )


class MonitoringServiceTests(unittest.TestCase):
    def test_sensitive_values_and_assignments_are_redacted(self) -> None:
        secret = "a-very-long-live-discord-token"
        message = (
            f"Connection failed token={secret} password=hunter2 "
            f"Authorization: Bot {secret}"
        )

        sanitized = sanitize_log_message(message, [secret])

        self.assertNotIn(secret, sanitized)
        self.assertNotIn("hunter2", sanitized)
        self.assertIn("[REDACTED]", sanitized)

    def test_long_messages_are_truncated_for_discord(self) -> None:
        sanitized = sanitize_log_message("x" * 5000)

        self.assertEqual(len(sanitized), MAX_DISCORD_LOG_MESSAGE)
        self.assertTrue(sanitized.endswith("…"))

    def test_normal_bot_status_text_is_not_redacted(self) -> None:
        self.assertEqual(
            sanitize_log_message("Bot started successfully"),
            "Bot started successfully",
        )

    def test_component_name_is_readable(self) -> None:
        self.assertEqual(
            component_name("cody.features.server_stats.service"),
            "Server Stats / Service",
        )
        self.assertEqual(component_name("cody.bot"), "Cody / Startup")

    def test_handler_forwards_only_non_monitoring_cody_logs(self) -> None:
        entries = []
        handler = DiscordLogHandler(entries.append)

        handler.emit(log_record("cody.bot", "Cody ready"))
        handler.emit(log_record("discord.client", "Gateway ready"))
        handler.emit(
            log_record("cody.features.monitoring.cog", "Delivery failed")
        )

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].message, "Cody ready")

    def test_traceback_body_stays_out_of_discord_entry(self) -> None:
        try:
            raise ValueError("provider unavailable")
        except ValueError:
            record = log_record(
                "cody.features.server_stats.service",
                "Statistics refresh failed",
                level=logging.ERROR,
                exc_info=sys.exc_info(),
            )

        entry = log_entry_from_record(record)
        embed = log_entry_embed(entry)

        self.assertEqual(entry.error_type, "ValueError")
        self.assertEqual(embed.description, "Statistics refresh failed")
        self.assertNotIn("Traceback", embed.description)
        self.assertEqual(embed.color.value, int(CodyColor.ERROR))
        self.assertTrue(any(field.name == "Suggested action" for field in embed.fields))

    def test_warning_embed_uses_warning_presentation(self) -> None:
        embed = log_entry_embed(
            DiscordLogEntry(
                level=logging.WARNING,
                level_name="WARNING",
                component="Welcome / Quotes",
                message="Quote data is unavailable.",
                created_at=datetime.now(timezone.utc),
            )
        )

        self.assertEqual(embed.title, "⚠️ ATTENTION REQUIRED")
        self.assertEqual(embed.color.value, int(CodyColor.WARNING))


if __name__ == "__main__":
    unittest.main()
