"""Provider-neutral request and response envelopes for the backend client."""

from __future__ import annotations

from dataclasses import dataclass
import math
from types import MappingProxyType
from typing import Any, Mapping
from uuid import UUID, uuid4

from cody.config import BACKEND_API_VERSION
from cody.integrations.backend.actions import BackendAction


MAX_DISCORD_SNOWFLAKE = (2**64) - 1


def _uuid_text(value: str | None) -> str:
    if value is None:
        return str(uuid4())
    try:
        parsed = UUID(value)
    except (TypeError, ValueError, AttributeError) as error:
        raise ValueError("Request and idempotency identifiers must be UUIDv4.") from error
    if parsed.version != 4:
        raise ValueError("Request and idempotency identifiers must be UUIDv4.")
    return str(parsed)


def discord_snowflake_text(value: int | str) -> str:
    """Return a lossless JSON string for an immutable Discord snowflake."""

    if isinstance(value, bool):
        raise ValueError("Discord user IDs must be positive integers.")
    try:
        normalized = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError("Discord user IDs must be positive integers.") from error
    if (
        normalized <= 0
        or normalized > MAX_DISCORD_SNOWFLAKE
        or str(value) != str(normalized)
    ):
        raise ValueError(
            "Discord IDs must be base-10 integers in the unsigned 64-bit range."
        )
    return str(normalized)


def _freeze_json(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Backend request numbers must be finite.")
        return value
    if isinstance(value, Mapping):
        frozen = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("Backend request object keys must be strings.")
            frozen[key] = _freeze_json(item)
        return MappingProxyType(frozen)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item) for item in value)
    raise ValueError("Backend request payload contains a non-JSON value.")


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


@dataclass(frozen=True)
class BackendRequest:
    """One logical call; reuse this object when an idempotent write is retried."""

    action: BackendAction
    request_id: str
    actor_discord_user_id: str | None
    discord_guild_id: str | None
    discord_interaction_id: str | None
    payload: Mapping[str, Any]
    idempotency_key: str | None = None
    api_version: str = BACKEND_API_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.action, BackendAction):
            raise ValueError("Backend requests require an allow-listed action.")
        if self.api_version != BACKEND_API_VERSION:
            raise ValueError("Backend requests require Cody's configured API version.")
        if _uuid_text(self.request_id) != self.request_id:
            raise ValueError("request_id must be a canonical lowercase UUIDv4.")
        if not isinstance(self.payload, Mapping):
            raise ValueError("Backend request payload must be an object.")
        object.__setattr__(self, "payload", _freeze_json(self.payload))
        if self.actor_discord_user_id is not None:
            if discord_snowflake_text(self.actor_discord_user_id) != self.actor_discord_user_id:
                raise ValueError("Actor Discord ID must be a canonical snowflake string.")
        if self.action.requires_actor and self.actor_discord_user_id is None:
            raise ValueError(f"{self.action.value} requires a Discord actor ID.")
        if (self.discord_guild_id is None) != (self.discord_interaction_id is None):
            raise ValueError("Discord context IDs must be supplied together.")
        for value in (self.discord_guild_id, self.discord_interaction_id):
            if value is not None and discord_snowflake_text(value) != value:
                raise ValueError("Discord context IDs must be canonical snowflake strings.")
        if self.actor_discord_user_id is not None and self.discord_guild_id is None:
            raise ValueError("Actor requests require Discord interaction context.")
        if self.action.changes_state:
            if self.idempotency_key is None:
                raise ValueError(f"{self.action.value} requires an idempotency key.")
            if _uuid_text(self.idempotency_key) != self.idempotency_key:
                raise ValueError("idempotency_key must be a canonical UUIDv4.")
        elif self.idempotency_key is not None:
            raise ValueError("Read-only actions must not include idempotency keys.")

    @classmethod
    def create(
        cls,
        action: BackendAction,
        *,
        actor_discord_user_id: int | str | None = None,
        discord_guild_id: int | str | None = None,
        discord_interaction_id: int | str | None = None,
        payload: Mapping[str, Any] | None = None,
        request_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> "BackendRequest":
        if not isinstance(action, BackendAction):
            raise ValueError("Backend requests require an allow-listed action.")
        if payload is not None and not isinstance(payload, Mapping):
            raise ValueError("Backend request payload must be an object.")
        actor = (
            discord_snowflake_text(actor_discord_user_id)
            if actor_discord_user_id is not None
            else None
        )
        if action.requires_actor and actor is None:
            raise ValueError(f"{action.value} requires a Discord actor ID.")
        guild_id = (
            discord_snowflake_text(discord_guild_id)
            if discord_guild_id is not None
            else None
        )
        interaction_id = (
            discord_snowflake_text(discord_interaction_id)
            if discord_interaction_id is not None
            else None
        )
        if actor is not None and (guild_id is None or interaction_id is None):
            raise ValueError(
                "Actor requests require Discord guild and interaction context IDs."
            )
        if (guild_id is None) != (interaction_id is None):
            raise ValueError(
                "Discord guild and interaction context IDs must be supplied together."
            )
        if action.changes_state:
            if idempotency_key is None:
                raise ValueError(
                    f"{action.value} requires an explicit UUIDv4 idempotency key."
                )
            idempotency_key = _uuid_text(idempotency_key)
        elif idempotency_key is not None:
            raise ValueError("Read-only actions must not include an idempotency key.")

        return cls(
            action=action,
            request_id=_uuid_text(request_id),
            actor_discord_user_id=actor,
            discord_guild_id=guild_id,
            discord_interaction_id=interaction_id,
            payload=payload or {},
            idempotency_key=idempotency_key,
        )

    def to_json(self) -> dict[str, Any]:
        envelope: dict[str, Any] = {
            "api_version": self.api_version,
            "request_id": self.request_id,
            "action": self.action.value,
            "payload": _thaw_json(self.payload),
        }
        if self.actor_discord_user_id is not None:
            envelope["actor"] = {
                "discord_user_id": self.actor_discord_user_id,
            }
        if self.discord_guild_id is not None:
            envelope["context"] = {
                "discord_guild_id": self.discord_guild_id,
                "discord_interaction_id": self.discord_interaction_id,
            }
        if self.idempotency_key is not None:
            envelope["idempotency_key"] = self.idempotency_key
        return envelope


@dataclass(frozen=True)
class BackendResult:
    """Validated success response returned to a feature service."""

    request_id: str
    data: Mapping[str, Any]
    server_time: str

    def __post_init__(self) -> None:
        if not isinstance(self.data, Mapping):
            raise ValueError("Backend result data must be an object.")
        object.__setattr__(self, "data", _freeze_json(self.data))
