from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest

from cody.features.server_stats.models import (
    CompetitionStats,
    DiscordStats,
    ServerStatsConfig,
    ServerStatsSnapshot,
)
from cody.features.server_stats.service import (
    ServerStatsService,
    build_channel_names,
    check_stat_permissions,
    collect_discord_stats,
    configured_stat_channel_ids,
    format_channel_name,
    format_stat_permission_report,
)


CONFIG = ServerStatsConfig(
    member_channel_id=1,
    umbral_channel_id=2,
    lumen_belt_channel_id=3,
    helio_channel_id=4,
    active_teams_channel_id=5,
    matches_today_channel_id=6,
    grid_output_channel_id=7,
    ladder_leader_channel_id=8,
    umbral_role_id=101,
    lumen_belt_role_id=102,
    helio_role_id=103,
)


class FakeChannel:
    def __init__(self, channel_id: int, name: str = "outdated") -> None:
        self.id = channel_id
        self.name = name
        self.edit_calls: list[dict[str, str]] = []

    async def edit(self, **kwargs) -> None:
        self.edit_calls.append(kwargs)
        self.name = kwargs["name"]


class FakePermissionChannel(FakeChannel):
    def __init__(self, channel_id: int, name: str, category: str) -> None:
        super().__init__(channel_id, name)
        self.category = category

    def permissions_for(self, member):
        return SimpleNamespace(view_channel=True, manage_channels=False)


class FakeGuild:
    def __init__(self, members, channels) -> None:
        self.id = 999
        self.members = members
        self.member_count = len(members)
        self._channels = {channel.id: channel for channel in channels}

    def get_channel(self, channel_id: int):
        return self._channels.get(channel_id)


class SequenceProvider:
    def __init__(self, *results) -> None:
        self.results = list(results)

    async def fetch_stats(self) -> CompetitionStats:
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    async def close(self) -> None:
        return None


def member(*role_ids: int, bot: bool = False):
    return SimpleNamespace(
        bot=bot,
        roles=[SimpleNamespace(id=role_id) for role_id in role_ids],
    )


class ServerStatsServiceTests(unittest.IsolatedAsyncioTestCase):
    def test_configured_channel_ids_follow_display_order(self) -> None:
        self.assertEqual(configured_stat_channel_ids(CONFIG), list(range(1, 9)))

    def test_discord_counts_exclude_bots_and_use_role_ids(self) -> None:
        guild = FakeGuild(
            [
                member(101),
                member(102),
                member(103),
                member(101, 102),
                member(101, bot=True),
            ],
            [],
        )

        stats = collect_discord_stats(guild, CONFIG)

        self.assertEqual(stats.members, 4)
        self.assertEqual(stats.umbral_city, 2)
        self.assertEqual(stats.lumen_belt, 2)
        self.assertEqual(stats.helio_citadels, 1)

    def test_bot_only_cache_reports_zero_human_members(self) -> None:
        guild = FakeGuild([member(101, bot=True)], [])

        stats = collect_discord_stats(guild, CONFIG)

        self.assertEqual(stats.members, 0)
        self.assertEqual(stats.umbral_city, 0)

    def test_missing_member_cache_does_not_use_bot_inclusive_total(self) -> None:
        guild = FakeGuild([], [])
        guild.member_count = 25

        stats = collect_discord_stats(guild, CONFIG)

        self.assertEqual(stats.members, 0)

    def test_channel_names_follow_the_documented_format(self) -> None:
        snapshot = ServerStatsSnapshot(
            discord=DiscordStats(123, 64, 41, 18),
            competition=CompetitionStats(27, 143, 84.7, "Team X"),
            refreshed_at=SimpleNamespace(),
        )

        names = build_channel_names(snapshot, CONFIG)

        self.assertEqual(names[1], "👥 Members · 123")
        self.assertEqual(names[2], "🌑 Umbral City · 64")
        self.assertEqual(names[3], "🪞 The Lumen Belt · 41")
        self.assertEqual(names[4], "☀️ Helio-Citadels · 18")
        self.assertEqual(names[5], "⚔️ Active Teams · 27")
        self.assertEqual(names[6], "🎮 Matches Today · 143")
        self.assertEqual(names[7], "☀️ Grid Output · 84.7 GW")
        self.assertEqual(names[8], "🏆 Ladder Leader · Team X")

    def test_long_channel_names_are_truncated_cleanly(self) -> None:
        name = format_channel_name("🏆", "Ladder Leader", "A" * 150)

        self.assertEqual(len(name), 100)
        self.assertTrue(name.endswith("…"))

    async def test_refresh_only_edits_changed_names(self) -> None:
        stats = CompetitionStats(27, 143, 84.7, "Team X")
        channels = [FakeChannel(channel_id) for channel_id in range(1, 9)]
        guild = FakeGuild([member(101), member(102), member(103)], channels)
        service = ServerStatsService(SequenceProvider(stats, stats), CONFIG)

        first = await service.refresh(guild)
        second = await service.refresh(guild)

        self.assertEqual(len(first.updated_channel_ids), 8)
        self.assertEqual(second.updated_channel_ids, ())
        self.assertEqual(len(second.unchanged_channel_ids), 8)
        self.assertTrue(all(len(channel.edit_calls) == 1 for channel in channels))

    async def test_provider_failure_keeps_last_competition_values(self) -> None:
        refreshed_at = datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc)
        stats = CompetitionStats(
            27,
            143,
            84.7,
            "Team X",
            as_of=refreshed_at,
        )
        channels = [FakeChannel(channel_id) for channel_id in range(1, 9)]
        guild = FakeGuild([member(101), member(102), member(103)], channels)
        clock_values = iter((refreshed_at, refreshed_at + timedelta(minutes=10)))
        service = ServerStatsService(
            SequenceProvider(stats, RuntimeError("backend unavailable")),
            CONFIG,
            clock=lambda: next(clock_values),
        )

        await service.refresh(guild)
        with self.assertLogs(
            "cody.features.server_stats.service",
            level="ERROR",
        ):
            result = await service.refresh(guild)

        self.assertEqual(result.snapshot.competition, stats)
        self.assertTrue(result.snapshot.competition_stale)
        self.assertEqual(result.provider_error, "backend unavailable")
        self.assertEqual(
            channels[4].name,
            "⚔️ Active Teams · 27 · stale 12:00Z",
        )
        self.assertEqual(len(channels[4].edit_calls), 2)

    async def test_expired_competition_fallback_is_marked_unavailable(self) -> None:
        refreshed_at = datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc)
        stats = CompetitionStats(
            27,
            143,
            84.7,
            "Team X",
            as_of=refreshed_at,
        )
        channels = [FakeChannel(channel_id) for channel_id in range(1, 9)]
        guild = FakeGuild([member(101)], channels)
        clock_values = iter((refreshed_at, refreshed_at + timedelta(minutes=31)))
        service = ServerStatsService(
            SequenceProvider(stats, RuntimeError("backend unavailable")),
            CONFIG,
            clock=lambda: next(clock_values),
        )

        await service.refresh(guild)
        with self.assertLogs(
            "cody.features.server_stats.service",
            level="ERROR",
        ):
            result = await service.refresh(guild)

        self.assertIsNone(result.snapshot.competition)
        self.assertFalse(result.snapshot.competition_stale)
        self.assertEqual(channels[4].name, "⚔️ Active Teams · Unavailable")

    async def test_discord_only_mode_clears_old_competition_values(self) -> None:
        channels = [FakeChannel(channel_id) for channel_id in range(1, 9)]
        channels[4].name = "⚔️ Active Teams · 12"
        channels[5].name = "🎮 Matches Today · 37"
        channels[6].name = "☀️ Grid Output · 42.8 GW"
        channels[7].name = "🏆 Ladder Leader · Team X"
        guild = FakeGuild([member(101)], channels)
        service = ServerStatsService(SequenceProvider(None), CONFIG)

        result = await service.refresh(guild)

        self.assertIsNone(result.snapshot.competition)
        self.assertEqual(channels[4].name, "⚔️ Active Teams · Unavailable")
        self.assertEqual(channels[5].name, "🎮 Matches Today · Unavailable")
        self.assertEqual(channels[6].name, "☀️ Grid Output · Unavailable")
        self.assertEqual(channels[7].name, "🏆 Ladder Leader · Unavailable")

    def test_permission_report_shows_effective_access_and_roles(self) -> None:
        channel = FakePermissionChannel(1, "Members", "Server Status")
        guild = FakeGuild([], [channel])
        guild.me = SimpleNamespace(
            id=123,
            roles=[SimpleNamespace(id=999), SimpleNamespace(id=1540833847225352242)],
        )

        report = check_stat_permissions(guild, CONFIG)
        output = format_stat_permission_report(report)

        self.assertEqual(report.bot_member_id, 123)
        self.assertIn(1540833847225352242, report.bot_role_ids)
        self.assertIn("Members", output)
        self.assertIn("View Channel=yes", output)
        self.assertIn("Manage Channels=no", output)
        self.assertIn("[Server Status]", output)
        self.assertIn("2 — not found or not visible", output)
        self.assertIn("Administrator, Connect, Speak", output)

    def test_permission_report_handles_missing_bot_member(self) -> None:
        guild = FakeGuild([], [])
        guild.me = None

        report = check_stat_permissions(guild, CONFIG)
        output = format_stat_permission_report(report)

        self.assertFalse(report.ready)
        self.assertIn("Cody's guild member could not be resolved", output)


if __name__ == "__main__":
    unittest.main()
