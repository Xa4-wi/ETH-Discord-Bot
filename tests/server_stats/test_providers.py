import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock

from cody.config import STATS_PROVIDER
from cody.features.server_stats.models import CompetitionStats
from cody.features.server_stats.providers import (
    BackendStatsProvider,
    DiscordOnlyStatsProvider,
    StaticStatsProvider,
    backend_stats_from_payload,
    competition_stats_from_payload,
    create_stats_provider,
)
from cody.integrations.backend import BackendAction


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class StatsProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_safe_default_publishes_no_competition_fixture(self) -> None:
        self.assertEqual(STATS_PROVIDER, "discord")
        provider = create_stats_provider()
        self.assertIsInstance(provider, DiscordOnlyStatsProvider)
        self.assertIsNone(await provider.fetch_stats())

    async def test_static_provider_returns_complete_development_values(self) -> None:
        stats = await StaticStatsProvider().fetch_stats()

        self.assertEqual(
            stats,
            CompetitionStats(
                active_teams=12,
                matches_today=37,
                grid_output=42.8,
                ladder_leader="Team X",
            ),
        )

    def test_mock_endpoint_matches_the_common_model(self) -> None:
        payload = json.loads(
            (PROJECT_ROOT / "docs" / "api" / "server-stats.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            competition_stats_from_payload(payload),
            CompetitionStats(12, 37, 42.8, "Team X"),
        )

    def test_future_ladder_leader_object_is_translated(self) -> None:
        stats = competition_stats_from_payload(
            {
                "active_teams": 54,
                "matches_today": 128,
                "grid_output": 84.7,
                "ladder_leader": {
                    "name": "Neural Knights",
                    "rating": 1842,
                },
            }
        )

        self.assertEqual(stats.ladder_leader, "Neural Knights")

    def test_canonical_summary_requires_identity_and_snapshot_time(self) -> None:
        stats = backend_stats_from_payload(
            {
                "active_teams": 54,
                "matches_today": 128,
                "grid_output": 84.7,
                "ladder_leader": {
                    "team_id": "team_17",
                    "name": "Neural Knights",
                },
                "as_of": "2026-08-26T12:20:00.000Z",
            }
        )

        self.assertEqual(stats.ladder_leader_team_id, "team_17")
        self.assertEqual(
            stats.as_of,
            datetime(2026, 8, 26, 12, 20, tzinfo=timezone.utc),
        )

        invalid_payloads = (
            {
                "active_teams": 1,
                "matches_today": 1,
                "grid_output": 1,
                "ladder_leader": "Team X",
                "as_of": "2026-08-26T12:20:00.000Z",
            },
            {
                "active_teams": 1,
                "matches_today": 1,
                "grid_output": 1,
                "ladder_leader": {"name": "Team X"},
                "as_of": "2026-08-26T12:20:00.000Z",
            },
            {
                "active_teams": 1,
                "matches_today": 1,
                "grid_output": 1,
                "ladder_leader": {"team_id": "team_1", "name": "Team X"},
            },
            {
                "active_teams": 1,
                "matches_today": 1,
                "grid_output": 1,
                "ladder_leader": {"team_id": " team_1", "name": "Team X"},
                "as_of": "2026-08-26T12:20:00.000Z",
            },
        )
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                with self.assertRaises((KeyError, ValueError)):
                    backend_stats_from_payload(payload)

    def test_invalid_numeric_values_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            competition_stats_from_payload(
                {
                    "active_teams": -1,
                    "matches_today": 1,
                    "grid_output": 1.0,
                    "ladder_leader": "Team X",
                }
            )
        with self.assertRaises(ValueError):
            competition_stats_from_payload(
                {
                    "active_teams": 1,
                    "matches_today": 1,
                    "grid_output": float("nan"),
                    "ladder_leader": "Team X",
                }
            )

    async def test_backend_provider_uses_the_canonical_summary_action(self) -> None:
        client = SimpleNamespace(
            call=AsyncMock(
                return_value=SimpleNamespace(
                    data={
                        "active_teams": 54,
                        "matches_today": 128,
                        "grid_output": 84.7,
                        "ladder_leader": {
                            "team_id": "team_17",
                            "name": "Neural Knights",
                        },
                        "as_of": "2026-08-26T12:20:00.000Z",
                    }
                )
            ),
            close=AsyncMock(),
        )
        provider = BackendStatsProvider(client)

        stats = await provider.fetch_stats()

        self.assertEqual(
            stats,
            CompetitionStats(
                54,
                128,
                84.7,
                "Neural Knights",
                ladder_leader_team_id="team_17",
                as_of=datetime(2026, 8, 26, 12, 20, tzinfo=timezone.utc),
            ),
        )
        client.call.assert_awaited_once_with(BackendAction.STATISTICS_SUMMARY)
        await provider.close()
        client.close.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
