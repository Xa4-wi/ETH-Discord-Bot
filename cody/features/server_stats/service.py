"""Collect, format, cache, and publish server statistics."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any

import discord

from cody.features.server_stats.constants import (
    DISCORD_CHANNEL_NAME_LIMIT,
    GRID_OUTPUT_UNIT,
    SERVER_STATS_CONFIG,
)
from cody.features.server_stats.models import (
    CompetitionStats,
    DiscordStats,
    RefreshResult,
    ServerStatsConfig,
    ServerStatsSnapshot,
    StatChannelPermission,
    StatPermissionReport,
)
from cody.features.server_stats.providers import StatsProvider


LOGGER = logging.getLogger(__name__)


class ServerStatsService:
    """Own refresh coordination and the last successful provider values."""

    def __init__(
        self,
        provider: StatsProvider,
        config: ServerStatsConfig = SERVER_STATS_CONFIG,
    ) -> None:
        self.provider = provider
        self.config = config
        self.last_successful_refresh: datetime | None = None
        self._last_competition_stats: CompetitionStats | None = None
        self._refresh_lock = asyncio.Lock()

    async def refresh(self, guild: discord.Guild) -> RefreshResult:
        """Refresh each configured channel, renaming only changed channels."""

        async with self._refresh_lock:
            competition_stats, provider_error = await self._competition_stats()
            discord_stats = collect_discord_stats(guild, self.config)
            refreshed_at = datetime.now(timezone.utc)
            snapshot = ServerStatsSnapshot(
                discord=discord_stats,
                competition=competition_stats,
                refreshed_at=refreshed_at,
            )
            desired_names = build_channel_names(snapshot, self.config)

            updated: list[int] = []
            unchanged: list[int] = []
            missing: list[int] = []
            failed: list[int] = []

            for channel_id, desired_name in desired_names.items():
                channel = guild.get_channel(channel_id)
                if channel is None or not hasattr(channel, "edit"):
                    missing.append(channel_id)
                    LOGGER.error(
                        "Statistics channel %s was not found in guild %s",
                        channel_id,
                        guild.id,
                    )
                    continue
                if channel.name == desired_name:
                    unchanged.append(channel_id)
                    continue

                try:
                    await channel.edit(
                        name=desired_name,
                        reason="Cody server statistics refresh",
                    )
                except Exception:
                    failed.append(channel_id)
                    LOGGER.exception(
                        "Could not rename statistics channel %s in guild %s",
                        channel_id,
                        guild.id,
                    )
                else:
                    updated.append(channel_id)

            return RefreshResult(
                snapshot=snapshot,
                updated_channel_ids=tuple(updated),
                unchanged_channel_ids=tuple(unchanged),
                missing_channel_ids=tuple(missing),
                failed_channel_ids=tuple(failed),
                provider_error=provider_error,
            )

    async def _competition_stats(
        self,
    ) -> tuple[CompetitionStats | None, str | None]:
        try:
            stats = await self.provider.fetch_stats()
        except Exception as error:
            LOGGER.exception(
                "Could not fetch competition statistics. Keeping previous values."
            )
            return self._last_competition_stats, str(error)

        self._last_competition_stats = stats
        self.last_successful_refresh = datetime.now(timezone.utc)
        return stats, None


async def update_server_stats(
    guild: discord.Guild,
    provider: StatsProvider,
    *,
    config: ServerStatsConfig = SERVER_STATS_CONFIG,
) -> RefreshResult:
    """Perform one standalone refresh with the supplied provider."""

    return await ServerStatsService(provider, config).refresh(guild)


def configured_stat_channel_ids(
    config: ServerStatsConfig = SERVER_STATS_CONFIG,
) -> list[int]:
    """Return every configured display channel ID in presentation order."""

    return [
        config.member_channel_id,
        config.umbral_channel_id,
        config.lumen_belt_channel_id,
        config.helio_channel_id,
        config.active_teams_channel_id,
        config.matches_today_channel_id,
        config.grid_output_channel_id,
        config.ladder_leader_channel_id,
    ]


def check_stat_permissions(
    guild: discord.Guild,
    config: ServerStatsConfig = SERVER_STATS_CONFIG,
) -> StatPermissionReport:
    """Inspect the two effective permissions used to update stats channels."""

    bot_member = guild.me
    if bot_member is None:
        return StatPermissionReport(
            bot_member_id=None,
            bot_role_ids=(),
            channels=tuple(
                StatChannelPermission(
                    channel_id=channel_id,
                    channel_name=None,
                    category_name=None,
                    view_channel=False,
                    manage_channels=False,
                )
                for channel_id in configured_stat_channel_ids(config)
            ),
        )

    channel_permissions: list[StatChannelPermission] = []
    for channel_id in configured_stat_channel_ids(config):
        channel = guild.get_channel(channel_id)
        if channel is None:
            channel_permissions.append(
                StatChannelPermission(
                    channel_id=channel_id,
                    channel_name=None,
                    category_name=None,
                    view_channel=False,
                    manage_channels=False,
                )
            )
            continue

        permissions = channel.permissions_for(bot_member)
        category = channel.category
        channel_permissions.append(
            StatChannelPermission(
                channel_id=channel_id,
                channel_name=channel.name,
                category_name=(
                    getattr(category, "name", str(category))
                    if category is not None
                    else None
                ),
                view_channel=permissions.view_channel,
                manage_channels=permissions.manage_channels,
            )
        )

    return StatPermissionReport(
        bot_member_id=bot_member.id,
        bot_role_ids=tuple(role.id for role in bot_member.roles),
        channels=tuple(channel_permissions),
    )


def format_stat_permission_report(report: StatPermissionReport) -> str:
    """Format an admin-only explanation of permissions used by this feature."""

    lines = [
        "CODY // STAT PERMISSIONS",
        "",
        "USED BY SERVER STATS",
        "View Channel   locate each display channel",
        "Manage Channels rename each display channel",
        "",
        "NOT REQUIRED",
        "Administrator, Connect, Speak",
        "",
    ]

    if report.bot_member_id is None:
        lines.extend(
            [
                "❌ Cody's guild member could not be resolved.",
                "Confirm the running token belongs to the bot in this server.",
            ]
        )
    else:
        role_ids = ", ".join(str(role_id) for role_id in report.bot_role_ids)
        lines.extend(
            [
                f"Cody member ID: {report.bot_member_id}",
                f"Assigned role IDs: {role_ids or 'none'}",
                "",
            ]
        )
        for channel in report.channels:
            if channel.channel_name is None:
                lines.append(f"❌ {channel.channel_id} — not found or not visible")
                continue
            marker = "✅" if channel.ready else "❌"
            category = channel.category_name or "No category"
            lines.append(f"{marker} {channel.channel_name} [{category}]")
            lines.append(
                "   "
                f"View Channel={'yes' if channel.view_channel else 'no'} · "
                f"Manage Channels={'yes' if channel.manage_channels else 'no'}"
            )

    lines.extend(
        [
            "",
            "Gateway requirement: Server Members Intent",
        ]
    )
    return "```text\n" + "\n".join(lines) + "\n```"


def collect_discord_stats(
    guild: discord.Guild,
    config: ServerStatsConfig = SERVER_STATS_CONFIG,
) -> DiscordStats:
    """Calculate member and layer counts from Discord's member cache."""

    cached_members = tuple(guild.members)
    eligible_members = tuple(
        member
        for member in cached_members
        if config.include_bots or not getattr(member, "bot", False)
    )

    if config.include_bots and guild.member_count is not None:
        member_count = guild.member_count
    elif cached_members:
        member_count = len(eligible_members)
    else:
        member_count = guild.member_count or 0

    return DiscordStats(
        members=member_count,
        umbral_city=_count_members_with_role(
            eligible_members,
            config.umbral_role_id,
        ),
        lumen_belt=_count_members_with_role(
            eligible_members,
            config.lumen_belt_role_id,
        ),
        helio_citadels=_count_members_with_role(
            eligible_members,
            config.helio_role_id,
        ),
    )


def build_channel_names(
    snapshot: ServerStatsSnapshot,
    config: ServerStatsConfig = SERVER_STATS_CONFIG,
) -> dict[int, str]:
    """Build the complete channel-ID-to-name mapping for a snapshot."""

    discord_stats = snapshot.discord
    names = {
        config.member_channel_id: format_channel_name(
            "👥",
            "Members",
            discord_stats.members,
        ),
        config.umbral_channel_id: format_channel_name(
            "🌑",
            "Umbral City",
            discord_stats.umbral_city,
        ),
        config.lumen_belt_channel_id: format_channel_name(
            "🪞",
            "The Lumen Belt",
            discord_stats.lumen_belt,
        ),
        config.helio_channel_id: format_channel_name(
            "☀️",
            "Helio-Citadels",
            discord_stats.helio_citadels,
        ),
    }

    competition = snapshot.competition
    if competition is not None:
        names.update(
            {
                config.active_teams_channel_id: format_channel_name(
                    "⚔️",
                    "Active Teams",
                    competition.active_teams,
                ),
                config.matches_today_channel_id: format_channel_name(
                    "🎮",
                    "Matches Today",
                    competition.matches_today,
                ),
                config.grid_output_channel_id: format_channel_name(
                    "☀️",
                    "Grid Output",
                    format_grid_output(competition.grid_output),
                ),
                config.ladder_leader_channel_id: format_channel_name(
                    "🏆",
                    "Ladder Leader",
                    competition.ladder_leader,
                ),
            }
        )
    return names


def format_grid_output(value: float) -> str:
    """Keep the display unit independent from provider parsing."""

    return f"{value:.1f} {GRID_OUTPUT_UNIT}"


def format_channel_name(icon: str, label: str, value: Any) -> str:
    """Normalize and safely truncate a Discord statistics channel name."""

    normalized_value = " ".join(str(value).split())
    name = f"{icon} {label} · {normalized_value}"
    if len(name) <= DISCORD_CHANNEL_NAME_LIMIT:
        return name
    return f"{name[: DISCORD_CHANNEL_NAME_LIMIT - 1].rstrip()}…"


def _count_members_with_role(members: tuple[Any, ...], role_id: int) -> int:
    return sum(
        1
        for member in members
        if any(getattr(role, "id", None) == role_id for role in member.roles)
    )
