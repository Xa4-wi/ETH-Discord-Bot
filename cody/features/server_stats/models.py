"""Data models shared by server-statistics services and providers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class CompetitionStats:
    """Competition values supplied by a static or remote provider."""

    active_teams: int
    matches_today: int
    grid_output: float
    ladder_leader: str


@dataclass(frozen=True)
class DiscordStats:
    """Values derived directly from the configured Discord guild."""

    members: int
    umbral_city: int
    lumen_belt: int
    helio_citadels: int


@dataclass(frozen=True)
class ServerStatsConfig:
    """Stable IDs and counting behavior used by the feature."""

    member_channel_id: int
    umbral_channel_id: int
    lumen_belt_channel_id: int
    helio_channel_id: int
    active_teams_channel_id: int
    matches_today_channel_id: int
    grid_output_channel_id: int
    ladder_leader_channel_id: int
    umbral_role_id: int
    lumen_belt_role_id: int
    helio_role_id: int
    include_bots: bool = False


@dataclass(frozen=True)
class ServerStatsSnapshot:
    """Most recently observed Discord and competition statistics."""

    discord: DiscordStats
    competition: CompetitionStats | None
    refreshed_at: datetime


@dataclass(frozen=True)
class RefreshResult:
    """Outcome of one attempt to refresh all configured channels."""

    snapshot: ServerStatsSnapshot
    updated_channel_ids: tuple[int, ...]
    unchanged_channel_ids: tuple[int, ...]
    missing_channel_ids: tuple[int, ...]
    failed_channel_ids: tuple[int, ...]
    provider_error: str | None = None


@dataclass(frozen=True)
class StatChannelPermission:
    """Cody's effective permissions for one statistics display channel."""

    channel_id: int
    channel_name: str | None
    category_name: str | None
    view_channel: bool
    manage_channels: bool

    @property
    def ready(self) -> bool:
        return self.view_channel and self.manage_channels


@dataclass(frozen=True)
class StatPermissionReport:
    """Cody's resolved identity, roles, and effective channel permissions."""

    bot_member_id: int | None
    bot_role_ids: tuple[int, ...]
    channels: tuple[StatChannelPermission, ...]

    @property
    def ready(self) -> bool:
        return self.bot_member_id is not None and all(
            channel.ready for channel in self.channels
        )
