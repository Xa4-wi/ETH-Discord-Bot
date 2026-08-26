"""Competition-statistics providers independent of Discord integration."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from datetime import datetime, timezone
import logging
import math
import re
from typing import Any, Protocol

import aiohttp

from cody.config import STATS_ENDPOINT, STATS_PROVIDER
from cody.features.server_stats.constants import HTTP_TIMEOUT_SECONDS
from cody.features.server_stats.models import CompetitionStats
from cody.integrations.backend import (
    BackendAction,
    BackendIntegrationError,
    MainBackendClient,
)


LOGGER = logging.getLogger(__name__)


class StatsProviderError(RuntimeError):
    """Raised when competition statistics cannot be retrieved or validated."""


class StatsProvider(Protocol):
    """Source of backend-owned competition values."""

    async def fetch_stats(self) -> CompetitionStats | None:
        """Return canonical aggregates, or none for Discord-only operation."""

    async def close(self) -> None:
        """Release any resources owned by the provider."""


class StaticStatsProvider:
    """Explicit development fixture; never a canonical production provider."""

    def __init__(self, stats: CompetitionStats | None = None) -> None:
        self._stats = stats or CompetitionStats(
            active_teams=12,
            matches_today=37,
            grid_output=42.8,
            ladder_leader="Team X",
        )

    async def fetch_stats(self) -> CompetitionStats:
        return self._stats

    async def close(self) -> None:
        return None


class DiscordOnlyStatsProvider:
    """Safe default that never publishes invented competition values."""

    async def fetch_stats(self) -> None:
        return None

    async def close(self) -> None:
        return None


class DevelopmentHttpStatsProvider:
    """Development-only provider for an unauthenticated aggregate mock."""

    def __init__(
        self,
        endpoint: str,
        *,
        session: aiohttp.ClientSession | None = None,
        timeout_seconds: float = HTTP_TIMEOUT_SECONDS,
    ) -> None:
        if not endpoint:
            raise ValueError("An HTTP statistics endpoint is required.")
        self.endpoint = endpoint
        self._session = session
        self._owns_session = session is None
        self._timeout = aiohttp.ClientTimeout(total=timeout_seconds)

    async def fetch_stats(self) -> CompetitionStats:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
            self._owns_session = True

        try:
            async with self._session.get(self.endpoint) as response:
                response.raise_for_status()
                payload = await response.json()
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as error:
            raise StatsProviderError(
                "Could not fetch competition statistics from the development mock."
            ) from error

        try:
            return competition_stats_from_payload(payload)
        except (KeyError, TypeError, ValueError) as error:
            raise StatsProviderError(
                "The competition statistics response has an invalid schema."
            ) from error

    async def close(self) -> None:
        if (
            self._owns_session
            and self._session is not None
            and not self._session.closed
        ):
            await self._session.close()


class BackendStatsProvider:
    """Fetch canonical aggregates through Cody's one Main Backend client."""

    def __init__(self, client: MainBackendClient) -> None:
        self._client = client

    async def fetch_stats(self) -> CompetitionStats:
        try:
            result = await self._client.call(BackendAction.STATISTICS_SUMMARY)
            return backend_stats_from_payload(result.data)
        except BackendIntegrationError as error:
            raise StatsProviderError(
                "The Main Backend could not provide competition statistics."
            ) from error
        except (KeyError, TypeError, ValueError) as error:
            raise StatsProviderError(
                "The Main Backend statistics payload has an invalid schema."
            ) from error

    async def close(self) -> None:
        await self._client.close()


def competition_stats_from_payload(payload: Any) -> CompetitionStats:
    """Translate the explicit development fixture representation."""

    if not isinstance(payload, Mapping):
        raise TypeError("Statistics response must be a JSON object.")

    active_teams = _nonnegative_int(payload["active_teams"], "active_teams")
    matches_today = _nonnegative_int(payload["matches_today"], "matches_today")
    grid_output = _nonnegative_number(payload["grid_output"], "grid_output")
    ladder_leader = _ladder_leader_name(payload["ladder_leader"])

    return CompetitionStats(
        active_teams=active_teams,
        matches_today=matches_today,
        grid_output=grid_output,
        ladder_leader=ladder_leader,
    )


def backend_stats_from_payload(payload: Any) -> CompetitionStats:
    """Validate the canonical ``statistics.summary`` data object."""

    if not isinstance(payload, Mapping):
        raise TypeError("Statistics response must be a JSON object.")

    leader = payload["ladder_leader"]
    if not isinstance(leader, Mapping):
        raise ValueError("ladder_leader must be an object.")
    team_id = _opaque_id(leader.get("team_id"), "ladder_leader.team_id")
    leader_name = _required_text(leader.get("name"), "ladder_leader.name")

    return CompetitionStats(
        active_teams=_nonnegative_int(payload["active_teams"], "active_teams"),
        matches_today=_nonnegative_int(
            payload["matches_today"],
            "matches_today",
        ),
        grid_output=_nonnegative_number(payload["grid_output"], "grid_output"),
        ladder_leader=leader_name,
        ladder_leader_team_id=team_id,
        as_of=_rfc3339_utc_milliseconds(payload["as_of"], "as_of"),
    )


def create_stats_provider() -> StatsProvider:
    """Build the configured provider without leaking selection into the cog."""

    if STATS_PROVIDER == "discord":
        return DiscordOnlyStatsProvider()
    if STATS_PROVIDER == "static":
        LOGGER.warning(
            "CODY_STATS_PROVIDER=static publishes development fixtures; do not "
            "use it for canonical production values"
        )
        return StaticStatsProvider()
    if STATS_PROVIDER == "http":
        if not STATS_ENDPOINT:
            raise RuntimeError(
                "CODY_STATS_ENDPOINT is required when CODY_STATS_PROVIDER=http."
            )
        LOGGER.warning(
            "CODY_STATS_PROVIDER=http is development-only; use backend for "
            "canonical production data"
        )
        return DevelopmentHttpStatsProvider(STATS_ENDPOINT)
    if STATS_PROVIDER == "backend":
        return BackendStatsProvider(MainBackendClient.from_environment())
    raise RuntimeError(
        "CODY_STATS_PROVIDER must be 'discord', 'static', 'http', or 'backend'."
    )


def _nonnegative_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer.")
    return value


def _nonnegative_number(value: Any, field: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
    ):
        raise ValueError(f"{field} must be a non-negative number.")
    return float(value)


def _ladder_leader_name(value: Any) -> str:
    if isinstance(value, Mapping):
        value = value.get("name")
    if not isinstance(value, str) or not value.strip():
        raise ValueError("ladder_leader must contain a team name.")
    return " ".join(value.split())


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string.")
    return " ".join(value.split())


def _opaque_id(value: Any, field: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value.encode("utf-8")) > 128
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise ValueError(f"{field} must be an opaque ID of at most 128 bytes.")
    return value


def _rfc3339_utc_milliseconds(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z",
        value,
    ):
        raise ValueError(
            f"{field} must be RFC3339 UTC with milliseconds and Z."
        )
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError as error:
        raise ValueError(
            f"{field} must be RFC3339 UTC with milliseconds and Z."
        ) from error
    return parsed.replace(tzinfo=timezone.utc)
