"""Authenticated, versioned HTTP client for Cody's single backend endpoint."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from datetime import datetime
import json
import logging
import re
import time
from typing import Any
from urllib.parse import urlsplit

import aiohttp

from cody.config import (
    BACKEND_ALLOW_INSECURE_LOCALHOST,
    BACKEND_API_VERSION,
    BACKEND_MAX_REQUEST_BYTES,
    BACKEND_MAX_RESPONSE_BYTES,
    BACKEND_READ_RETRIES,
    BACKEND_TIMEOUT_SECONDS,
    get_backend_endpoint,
    get_backend_service_token,
)
from cody.integrations.backend.actions import BackendAction
from cody.integrations.backend.errors import (
    SAFE_ERROR_MESSAGES,
    BackendActionError,
    BackendConfigurationError,
    BackendProtocolError,
    BackendTransportError,
)
from cody.integrations.backend.models import BackendRequest, BackendResult


LOGGER = logging.getLogger(__name__)
TRANSIENT_HTTP_STATUSES = frozenset({502, 503, 504})
LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
MAX_TIMEOUT_SECONDS = 60.0
MAX_READ_RETRIES = 5
MAX_REQUEST_BYTES = 1_048_576
MAX_RESPONSE_BYTES = 10_485_760
RESPONSE_CHUNK_BYTES = 65_536
TLS_ERRORS = (
    aiohttp.ClientSSLError,
    aiohttp.ServerFingerprintMismatch,
)


class _TransientResponse(RuntimeError):
    def __init__(self, status: int) -> None:
        super().__init__(f"Transient backend HTTP status {status}")
        self.status = status


class MainBackendClient:
    """Send allow-listed actions without exposing HTTP details to features."""

    def __init__(
        self,
        endpoint: str,
        service_token: str,
        *,
        session: aiohttp.ClientSession | None = None,
        timeout_seconds: float = BACKEND_TIMEOUT_SECONDS,
        read_retries: int = BACKEND_READ_RETRIES,
        max_response_bytes: int = BACKEND_MAX_RESPONSE_BYTES,
        max_request_bytes: int = BACKEND_MAX_REQUEST_BYTES,
        allow_insecure_localhost: bool = BACKEND_ALLOW_INSECURE_LOCALHOST,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.endpoint = _validated_endpoint(endpoint, allow_insecure_localhost)
        if (
            len(service_token) < 32
            or len(service_token) > 4096
            or not service_token.isascii()
            or any(
                character.isspace() or ord(character) < 33 or ord(character) > 126
                for character in service_token
            )
        ):
            raise BackendConfigurationError(
                "CODY_BACKEND_SERVICE_TOKEN must be 32–4096 printable ASCII "
                "characters without whitespace."
            )
        if not 0 < timeout_seconds <= MAX_TIMEOUT_SECONDS:
            raise BackendConfigurationError(
                "Backend timeout must be greater than zero and at most "
                f"{MAX_TIMEOUT_SECONDS:g} seconds."
            )
        if not 0 <= read_retries <= MAX_READ_RETRIES:
            raise BackendConfigurationError(
                f"Backend read retries must be between zero and {MAX_READ_RETRIES}."
            )
        if not 0 < max_response_bytes <= MAX_RESPONSE_BYTES:
            raise BackendConfigurationError(
                f"Backend response limit must be between 1 and {MAX_RESPONSE_BYTES} bytes."
            )
        if not 0 < max_request_bytes <= MAX_REQUEST_BYTES:
            raise BackendConfigurationError(
                f"Backend request limit must be between 1 and {MAX_REQUEST_BYTES} bytes."
            )

        self._service_token = service_token
        self._session = session
        self._owns_session = session is None
        self._timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self._read_retries = read_retries
        self._max_response_bytes = max_response_bytes
        self._max_request_bytes = max_request_bytes
        self._sleep = sleep

    @classmethod
    def from_environment(cls) -> "MainBackendClient":
        try:
            endpoint = get_backend_endpoint()
            token = get_backend_service_token()
        except RuntimeError as error:
            raise BackendConfigurationError(str(error)) from error
        return cls(endpoint, token)

    async def call(
        self,
        action: BackendAction,
        *,
        actor_discord_user_id: int | str | None = None,
        discord_guild_id: int | str | None = None,
        discord_interaction_id: int | str | None = None,
        payload: Mapping[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> BackendResult:
        request = BackendRequest.create(
            action,
            actor_discord_user_id=actor_discord_user_id,
            discord_guild_id=discord_guild_id,
            discord_interaction_id=discord_interaction_id,
            payload=payload,
            idempotency_key=idempotency_key,
        )
        return await self.execute(request)

    async def execute(self, request: BackendRequest) -> BackendResult:
        """Execute one logical request, preserving its IDs across safe retries."""

        attempts = 1 if request.action.changes_state else self._read_retries + 1
        last_failure: Exception | None = None

        for attempt in range(1, attempts + 1):
            started = time.monotonic()
            try:
                result, status = await self._send_once(request)
            except TLS_ERRORS as error:
                # Certificate, TLS-handshake, and fingerprint failures are
                # configuration/security failures, not transient reads.
                LOGGER.error(
                    "Backend TLS validation failed | request_id=%s action=%s",
                    request.request_id,
                    request.action.value,
                )
                raise BackendTransportError(
                    request_id=request.request_id,
                    retryable=False,
                    outcome_uncertain=False,
                ) from error
            except (_TransientResponse, aiohttp.ClientError, asyncio.TimeoutError) as error:
                last_failure = error
                should_retry = attempt < attempts
                status = (
                    error.status if isinstance(error, _TransientResponse) else "none"
                )
                LOGGER.warning(
                    "Backend call failed transiently | request_id=%s action=%s "
                    "status=%s attempt=%d retry=%s",
                    request.request_id,
                    request.action.value,
                    status,
                    attempt,
                    should_retry,
                )
                if should_retry:
                    await self._sleep(min(0.25 * (2 ** (attempt - 1)), 2.0))
                    continue
                raise BackendTransportError(
                    request_id=request.request_id,
                    retryable=not request.action.changes_state,
                    outcome_uncertain=request.action.changes_state,
                ) from error
            except BackendActionError as error:
                latency_ms = round((time.monotonic() - started) * 1000)
                LOGGER.warning(
                    "Backend action rejected | request_id=%s action=%s status=%s "
                    "error_code=%s latency_ms=%s",
                    request.request_id,
                    request.action.value,
                    error.http_status,
                    error.code,
                    latency_ms,
                )
                raise
            except BackendProtocolError:
                latency_ms = round((time.monotonic() - started) * 1000)
                LOGGER.error(
                    "Backend protocol validation failed | request_id=%s action=%s "
                    "latency_ms=%s",
                    request.request_id,
                    request.action.value,
                    latency_ms,
                )
                raise

            latency_ms = round((time.monotonic() - started) * 1000)
            LOGGER.info(
                "Backend call completed | request_id=%s action=%s status=%s latency_ms=%s",
                request.request_id,
                request.action.value,
                status,
                latency_ms,
            )
            return result

        raise BackendTransportError(
            request_id=request.request_id,
            retryable=True,
        ) from last_failure

    async def close(self) -> None:
        if (
            self._owns_session
            and self._session is not None
            and not self._session.closed
        ):
            await self._session.close()

    async def _send_once(
        self,
        request: BackendRequest,
    ) -> tuple[BackendResult, int]:
        envelope = request.to_json()
        try:
            encoded_body = json.dumps(
                envelope,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        except (TypeError, ValueError) as error:
            raise BackendProtocolError(
                "The backend request payload is not JSON serializable.",
                request_id=request.request_id,
            ) from error
        if len(encoded_body) > self._max_request_bytes:
            raise BackendProtocolError(
                "The backend request exceeded Cody's size limit.",
                request_id=request.request_id,
            )
        session = await self._get_session()
        headers = {
            "Authorization": f"Bearer {self._service_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Cody-Discord-Bot/backend-v1",
            "X-Request-ID": request.request_id,
        }
        async with session.post(
            self.endpoint,
            # Send the exact bytes that were measured. Passing ``json=`` would
            # make aiohttp serialize the envelope again with different Unicode
            # and whitespace defaults, bypassing the configured wire limit.
            data=encoded_body,
            headers=headers,
            allow_redirects=False,
            timeout=self._timeout,
        ) as response:
            if response.status in TRANSIENT_HTTP_STATUSES:
                raise _TransientResponse(response.status)
            try:
                body = await self._read_response(response, request.request_id)
                result = _response_result(body, request, response.status)
            except BackendProtocolError as error:
                if request.action.changes_state:
                    error.outcome_uncertain = True
                raise
            return result, response.status

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
            self._owns_session = True
        return self._session

    async def _read_response(
        self,
        response: aiohttp.ClientResponse,
        request_id: str,
    ) -> Any:
        content_type = response.headers.get("Content-Type", "")
        if content_type.split(";", 1)[0].strip().lower() != "application/json":
            raise BackendProtocolError(
                "The backend response must use application/json.",
                request_id=request_id,
            )
        if (
            response.content_length is not None
            and response.content_length > self._max_response_bytes
        ):
            raise BackendProtocolError(
                "The backend response exceeded Cody's size limit.",
                request_id=request_id,
            )
        raw = bytearray()
        async for chunk in response.content.iter_chunked(
            min(RESPONSE_CHUNK_BYTES, self._max_response_bytes + 1)
        ):
            raw.extend(chunk)
            if len(raw) > self._max_response_bytes:
                raise BackendProtocolError(
                    "The backend response exceeded Cody's size limit.",
                    request_id=request_id,
                )
        try:
            return json.loads(
                bytes(raw).decode("utf-8"),
                parse_constant=_reject_nonfinite_json,
            )
        except (UnicodeDecodeError, ValueError) as error:
            raise BackendProtocolError(
                "The backend returned invalid JSON.",
                request_id=request_id,
            ) from error


def _validated_endpoint(endpoint: str, allow_insecure_localhost: bool) -> str:
    endpoint = endpoint.strip()
    if any(character.isspace() or ord(character) < 33 for character in endpoint):
        raise BackendConfigurationError("The Main Backend endpoint is invalid.")
    parsed = urlsplit(endpoint)
    if not endpoint or not parsed.hostname or parsed.username or parsed.password:
        raise BackendConfigurationError("The Main Backend endpoint is invalid.")
    if parsed.query or parsed.fragment:
        raise BackendConfigurationError(
            "The Main Backend endpoint must not contain a query or fragment."
        )
    try:
        parsed.port
    except ValueError as error:
        raise BackendConfigurationError("The Main Backend endpoint port is invalid.") from error
    secure = parsed.scheme == "https"
    local_exception = (
        allow_insecure_localhost
        and parsed.scheme == "http"
        and parsed.hostname in LOCAL_HOSTS
    )
    if not secure and not local_exception:
        raise BackendConfigurationError(
            "The Main Backend endpoint must use HTTPS. Plain HTTP is allowed only "
            "for localhost when CODY_BACKEND_ALLOW_INSECURE_LOCALHOST=true."
        )
    if not parsed.path.endswith("/internal/cody/v1"):
        raise BackendConfigurationError(
            "The Main Backend endpoint must end with /internal/cody/v1."
        )
    if parsed.path != "/internal/cody/v1":
        raise BackendConfigurationError(
            "The Main Backend endpoint path must be exactly /internal/cody/v1."
        )
    return endpoint


def _reject_nonfinite_json(value: str) -> None:
    raise ValueError(f"Non-finite JSON number {value} is not permitted.")


def _response_result(
    payload: Any,
    request: BackendRequest,
    http_status: int,
) -> BackendResult:
    if not isinstance(payload, Mapping):
        raise BackendProtocolError(
            "The backend response must be a JSON object.",
            request_id=request.request_id,
        )
    if payload.get("api_version") != BACKEND_API_VERSION:
        raise BackendProtocolError(
            "The backend response API version did not match Cody's contract.",
            request_id=request.request_id,
        )
    response_request_id = payload.get("request_id")
    if response_request_id != request.request_id:
        raise BackendProtocolError(
            "The backend response request ID did not match Cody's request.",
            request_id=request.request_id,
        )
    success = payload.get("success")
    if not isinstance(success, bool):
        raise BackendProtocolError(
            "The backend response is missing a boolean success field.",
            request_id=request.request_id,
        )
    server_time = payload.get("server_time")
    if not isinstance(server_time, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z",
        server_time,
    ):
        raise BackendProtocolError(
            "The backend response has an invalid server_time.",
            request_id=request.request_id,
        )
    try:
        datetime.strptime(server_time, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError as error:
        raise BackendProtocolError(
            "The backend response has an invalid server_time.",
            request_id=request.request_id,
        ) from error

    if success:
        if not 200 <= http_status < 300:
            raise BackendProtocolError(
                "The backend returned success with a failing HTTP status.",
                request_id=request.request_id,
            )
        data = payload.get("data")
        if not isinstance(data, Mapping):
            raise BackendProtocolError(
                "A successful backend response must contain an object in data.",
                request_id=request.request_id,
            )
        try:
            return BackendResult(
                request_id=request.request_id,
                data=dict(data),
                server_time=server_time,
            )
        except ValueError as error:
            raise BackendProtocolError(
                "The backend response data contains an invalid JSON value.",
                request_id=request.request_id,
            ) from error

    if 200 <= http_status < 300:
        raise BackendProtocolError(
            "The backend returned a failure envelope with a successful HTTP status.",
            request_id=request.request_id,
        )
    if 300 <= http_status < 400:
        raise BackendProtocolError(
            "The Main Backend must not redirect Cody requests.",
            request_id=request.request_id,
        )

    error = payload.get("error")
    if not isinstance(error, Mapping):
        raise BackendProtocolError(
            "A failed backend response must contain an error object.",
            request_id=request.request_id,
        )
    code = error.get("code")
    message = error.get("message")
    retryable = error.get("retryable")
    if (
        not isinstance(code, str)
        or code not in SAFE_ERROR_MESSAGES
        or not isinstance(message, str)
        or not isinstance(retryable, bool)
    ):
        raise BackendProtocolError(
            "The backend error object has an invalid schema.",
            request_id=request.request_id,
        )
    raise BackendActionError(
        code=code,
        request_id=request.request_id,
        retryable=retryable,
        http_status=http_status,
    )
