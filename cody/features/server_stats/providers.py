"""Competition-statistics providers independent of Discord integration."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any, Protocol

import aiohttp

from cody.config import STATS_ENDPOINT, STATS_PROVIDER
from cody.features.server_stats.constants import HTTP_TIMEOUT_SECONDS
from cody.features.server_stats.models import CompetitionStats


class StatsProviderError(RuntimeError):
    """Raised when competition statistics cannot be retrieved or validated."""


class StatsProvider(Protocol):
    """Source of backend-owned competition values."""

    async def fetch_stats(self) -> CompetitionStats:
        """Return the latest complete competition-statistics snapshot."""

    async def close(self) -> None:
        """Release any resources owned by the provider."""


class StaticStatsProvider:
    """Development provider used until an official backend is available."""

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


class HttpStatsProvider:
    """Fetch and translate an aggregate JSON statistics endpoint."""

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
                f"Could not fetch competition statistics from {self.endpoint}."
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


def competition_stats_from_payload(payload: Any) -> CompetitionStats:
    """Translate either the mock or future API representation into the model."""

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


def create_stats_provider() -> StatsProvider:
    """Build the configured provider without leaking selection into the cog."""

    if STATS_PROVIDER == "static":
        return StaticStatsProvider()
    if STATS_PROVIDER == "http":
        if not STATS_ENDPOINT:
            raise RuntimeError(
                "CODY_STATS_ENDPOINT is required when CODY_STATS_PROVIDER=http."
            )
        return HttpStatsProvider(STATS_ENDPOINT)
    raise RuntimeError("CODY_STATS_PROVIDER must be 'static' or 'http'.")


def _nonnegative_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer.")
    return value


def _nonnegative_number(value: Any, field: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
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
