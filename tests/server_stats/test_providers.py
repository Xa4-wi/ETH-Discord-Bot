import json
from pathlib import Path
import unittest

from cody.features.server_stats.models import CompetitionStats
from cody.features.server_stats.providers import (
    StaticStatsProvider,
    competition_stats_from_payload,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class StatsProviderTests(unittest.IsolatedAsyncioTestCase):
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


if __name__ == "__main__":
    unittest.main()
