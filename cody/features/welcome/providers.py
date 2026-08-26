"""Backend gateway for participant linkage checks during onboarding."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from cody.features.welcome.models import ParticipantLink
from cody.integrations.backend import MainBackendClient
from cody.integrations.backend.actions import BackendAction
from cody.integrations.backend.errors import (
    BackendActionError,
    BackendIntegrationError,
    BackendProtocolError,
)


MAX_BACKEND_ID_BYTES = 128


class ParticipantNotLinked(RuntimeError):
    """The backend has no participant associated with the Discord actor."""


class ParticipantVerificationUnavailable(RuntimeError):
    """The backend could not provide a trustworthy linkage answer."""

    def __init__(self, *, request_id: str | None = None) -> None:
        super().__init__(
            "Battlecode account verification is currently unavailable. "
            "Please try again shortly."
        )
        self.request_id = request_id


class ParticipantLinkProvider(Protocol):
    async def get_link(
        self,
        *,
        discord_user_id: int,
        discord_guild_id: int,
        discord_interaction_id: int,
    ) -> ParticipantLink: ...


class BackendParticipantLinkProvider:
    """Resolve participant linkage through Cody's authenticated backend client."""

    def __init__(self, client: MainBackendClient) -> None:
        self.client = client

    @classmethod
    def from_environment(cls) -> "BackendParticipantLinkProvider":
        return cls(MainBackendClient.from_environment())

    async def get_link(
        self,
        *,
        discord_user_id: int,
        discord_guild_id: int,
        discord_interaction_id: int,
    ) -> ParticipantLink:
        try:
            result = await self.client.call(
                BackendAction.PARTICIPANT_GET,
                actor_discord_user_id=discord_user_id,
                discord_guild_id=discord_guild_id,
                discord_interaction_id=discord_interaction_id,
                payload={},
            )
        except BackendActionError as error:
            if error.code in {"USER_NOT_LINKED", "USER_NOT_FOUND"}:
                raise ParticipantNotLinked from error
            raise ParticipantVerificationUnavailable(
                request_id=error.request_id
            ) from error
        except BackendIntegrationError as error:
            raise ParticipantVerificationUnavailable(
                request_id=getattr(error, "request_id", None)
            ) from error

        try:
            return participant_link_from_data(result.data)
        except ValueError as error:
            raise BackendProtocolError(
                "participant.get returned an invalid participant object.",
                request_id=result.request_id,
            ) from error

    async def close(self) -> None:
        await self.client.close()


def participant_link_from_data(data: Mapping[str, Any]) -> ParticipantLink:
    """Strictly translate the proposed participant.get success contract."""

    participant_id = _backend_id(data.get("participant_id"), "participant_id")
    display_name = data.get("display_name")
    if (
        not isinstance(display_name, str)
        or not display_name.strip()
        or len(display_name) > 200
    ):
        raise ValueError("display_name must be a non-empty string of at most 200 characters")

    raw_team_id = data.get("team_id")
    team_id = (
        None
        if raw_team_id is None
        else _backend_id(raw_team_id, "team_id")
    )
    return ParticipantLink(
        participant_id=participant_id,
        display_name=display_name.strip(),
        team_id=team_id,
    )


def _backend_id(value: Any, field: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value.encode("utf-8")) > MAX_BACKEND_ID_BYTES
    ):
        raise ValueError(f"{field} must be a non-empty backend ID")
    return value
