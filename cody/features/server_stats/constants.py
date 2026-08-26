"""Configuration and presentation constants for server statistics."""

from cody.config import (
    STATS_ACTIVE_TEAMS_CHANNEL_ID,
    STATS_GRID_OUTPUT_CHANNEL_ID,
    STATS_HELIO_CHANNEL_ID,
    STATS_HELIO_ROLE_ID,
    STATS_INCLUDE_BOTS,
    STATS_LADDER_LEADER_CHANNEL_ID,
    STATS_LUMEN_CHANNEL_ID,
    STATS_LUMEN_ROLE_ID,
    STATS_MATCHES_TODAY_CHANNEL_ID,
    STATS_MEMBERS_CHANNEL_ID,
    STATS_UMBRAL_CHANNEL_ID,
    STATS_UMBRAL_ROLE_ID,
)
from cody.features.server_stats.models import ServerStatsConfig


REFRESH_INTERVAL_MINUTES = 10
HTTP_TIMEOUT_SECONDS = 10
DISCORD_CHANNEL_NAME_LIMIT = 100
GRID_OUTPUT_UNIT = "GW"
# Canonical values disappear after three missed ten-minute refreshes. This is
# deliberately a fixed safety ceiling rather than an operator-expandable TTL.
MAX_COMPETITION_STALE_SECONDS = 30 * 60
MAX_BACKEND_CLOCK_SKEW_SECONDS = 5 * 60

SERVER_STATS_CONFIG = ServerStatsConfig(
    member_channel_id=STATS_MEMBERS_CHANNEL_ID,
    umbral_channel_id=STATS_UMBRAL_CHANNEL_ID,
    lumen_belt_channel_id=STATS_LUMEN_CHANNEL_ID,
    helio_channel_id=STATS_HELIO_CHANNEL_ID,
    active_teams_channel_id=STATS_ACTIVE_TEAMS_CHANNEL_ID,
    matches_today_channel_id=STATS_MATCHES_TODAY_CHANNEL_ID,
    grid_output_channel_id=STATS_GRID_OUTPUT_CHANNEL_ID,
    ladder_leader_channel_id=STATS_LADDER_LEADER_CHANNEL_ID,
    umbral_role_id=STATS_UMBRAL_ROLE_ID,
    lumen_belt_role_id=STATS_LUMEN_ROLE_ID,
    helio_role_id=STATS_HELIO_ROLE_ID,
    include_bots=STATS_INCLUDE_BOTS,
)
