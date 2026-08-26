from __future__ import annotations

import asyncio
import json
import unittest
from unittest.mock import AsyncMock
from uuid import uuid4

import aiohttp

from cody.integrations.backend import (
    BackendAction,
    BackendActionError,
    BackendConfigurationError,
    BackendProtocolError,
    BackendRequest,
    BackendTransportError,
    MainBackendClient,
)


ENDPOINT = "https://backend.example/internal/cody/v1"
TOKEN = "test-service-credential-value-0123456789"
SERVER_TIME = "2026-08-26T12:20:00.000Z"


class FakeResponse:
    def __init__(
        self,
        status: int,
        payload=None,
        *,
        raw: bytes | None = None,
        content_type: str = "application/json; charset=utf-8",
        content_length: int | None = None,
        chunks: list[bytes] | None = None,
    ) -> None:
        self.status = status
        self._raw = raw if raw is not None else json.dumps(payload).encode("utf-8")
        self.content_length = (
            len(self._raw) if content_length is None else content_length
        )
        self.headers = {"Content-Type": content_type}
        self.content = FakeContent(chunks or [self._raw])


class FakeContent:
    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = chunks

    async def iter_chunked(self, size: int):
        for source in self._chunks:
            for offset in range(0, len(source), size):
                yield source[offset : offset + size]


class FakeRequestContext:
    def __init__(self, result) -> None:
        self.result = result

    async def __aenter__(self):
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        return None


class FakeSession:
    def __init__(self, *results) -> None:
        self.results = list(results)
        self.calls = []
        self.closed = False

    def post(self, endpoint, **kwargs):
        self.calls.append((endpoint, kwargs))
        return FakeRequestContext(self.results.pop(0))

    async def close(self) -> None:
        self.closed = True


def success_payload(request_id: str, data=None):
    return {
        "api_version": "1",
        "success": True,
        "request_id": request_id,
        "server_time": SERVER_TIME,
        "data": data or {},
    }


class BackendEnvelopeTests(unittest.TestCase):
    def test_action_allow_list_contains_no_competition_mutations(self) -> None:
        actions = {action.value for action in BackendAction}

        self.assertIn("statistics.summary", actions)
        self.assertIn("ticket.resolve", actions)
        self.assertNotIn("match.schedule", actions)
        self.assertNotIn("match.cancel", actions)
        self.assertNotIn("match.retry", actions)
        self.assertNotIn("team.create", actions)
        self.assertNotIn("submission.upload", actions)

    def test_actor_request_forwards_lossless_ids_and_context(self) -> None:
        request = BackendRequest.create(
            BackendAction.PARTICIPANT_GET,
            actor_discord_user_id=18446744073709551615,
            discord_guild_id=1530000000000000000,
            discord_interaction_id=1540000000000000000,
        )

        envelope = request.to_json()
        self.assertEqual(
            envelope["actor"]["discord_user_id"],
            "18446744073709551615",
        )
        self.assertEqual(
            envelope["context"],
            {
                "discord_guild_id": "1530000000000000000",
                "discord_interaction_id": "1540000000000000000",
            },
        )
        self.assertNotIn("idempotency_key", envelope)

    def test_actor_requests_require_discord_context(self) -> None:
        with self.assertRaises(ValueError):
            BackendRequest.create(
                BackendAction.TEAM_GET,
                actor_discord_user_id=123,
            )

    def test_every_ticket_write_requires_explicit_idempotency(self) -> None:
        write_actions = [action for action in BackendAction if action.changes_state]
        for action in write_actions:
            with self.subTest(action=action.value):
                with self.assertRaises(ValueError):
                    BackendRequest.create(
                        action,
                        actor_discord_user_id=123,
                        discord_guild_id=456,
                        discord_interaction_id=789,
                    )

                key = str(uuid4())
                request = BackendRequest.create(
                    action,
                    actor_discord_user_id=123,
                    discord_guild_id=456,
                    discord_interaction_id=789,
                    idempotency_key=key,
                )
                self.assertEqual(request.to_json()["idempotency_key"], key)

    def test_invalid_or_lossy_snowflakes_are_rejected(self) -> None:
        for value in (0, -1, "00123", " 123", 2**64, True):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    BackendRequest.create(
                        BackendAction.PARTICIPANT_GET,
                        actor_discord_user_id=value,
                        discord_guild_id=456,
                        discord_interaction_id=789,
                    )

    def test_payload_is_a_deep_immutable_snapshot(self) -> None:
        original = {"filters": {"states": ["OPEN"]}}
        request = BackendRequest.create(
            BackendAction.EVENT_STATUS,
            payload=original,
        )

        original["filters"]["states"].append("CLOSED")

        self.assertEqual(
            request.to_json()["payload"],
            {"filters": {"states": ["OPEN"]}},
        )
        with self.assertRaises(TypeError):
            request.payload["new"] = "value"


class MainBackendClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_success_uses_exact_post_envelope_and_safe_headers(self) -> None:
        request = BackendRequest.create(BackendAction.STATISTICS_SUMMARY)
        session = FakeSession(FakeResponse(200, success_payload(request.request_id)))
        client = MainBackendClient(ENDPOINT, TOKEN, session=session)

        result = await client.execute(request)

        self.assertEqual(result.request_id, request.request_id)
        endpoint, call = session.calls[0]
        self.assertEqual(endpoint, ENDPOINT)
        self.assertEqual(json.loads(call["data"].decode("utf-8")), request.to_json())
        self.assertEqual(call["headers"]["Authorization"], f"Bearer {TOKEN}")
        self.assertEqual(call["headers"]["X-Request-ID"], request.request_id)
        self.assertFalse(call["allow_redirects"])

    async def test_request_limit_applies_to_exact_utf8_wire_bytes(self) -> None:
        request = BackendRequest.create(
            BackendAction.EVENT_STATUS,
            payload={"label": "Ümbral 🌑" * 20},
        )
        encoded = json.dumps(
            request.to_json(),
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        session = FakeSession(
            FakeResponse(200, success_payload(request.request_id))
        )
        client = MainBackendClient(
            ENDPOINT,
            TOKEN,
            session=session,
            max_request_bytes=len(encoded),
        )

        await client.execute(request)

        self.assertEqual(session.calls[0][1]["data"], encoded)

        too_small = FakeSession()
        client = MainBackendClient(
            ENDPOINT,
            TOKEN,
            session=too_small,
            max_request_bytes=len(encoded) - 1,
        )
        with self.assertRaises(BackendProtocolError):
            await client.execute(request)
        self.assertEqual(too_small.calls, [])

    async def test_backend_diagnostic_is_never_the_public_exception_message(self) -> None:
        request = BackendRequest.create(
            BackendAction.PARTICIPANT_GET,
            actor_discord_user_id=123,
            discord_guild_id=456,
            discord_interaction_id=789,
        )
        diagnostic = "private row and service-token-value details"
        session = FakeSession(
            FakeResponse(
                404,
                {
                    "api_version": "1",
                    "success": False,
                    "request_id": request.request_id,
                    "server_time": SERVER_TIME,
                    "error": {
                        "code": "USER_NOT_LINKED",
                        "message": diagnostic,
                        "retryable": False,
                    },
                },
            )
        )
        client = MainBackendClient(ENDPOINT, TOKEN, session=session)

        with self.assertLogs("cody.integrations.backend.client", level="WARNING") as logs:
            with self.assertRaises(BackendActionError) as context:
                await client.execute(request)

        self.assertEqual(context.exception.code, "USER_NOT_LINKED")
        self.assertFalse(hasattr(context.exception, "diagnostic_message"))
        self.assertNotIn(diagnostic, str(context.exception))
        self.assertNotIn(diagnostic, " ".join(logs.output))
        self.assertNotIn(TOKEN, " ".join(logs.output))

    async def test_safe_read_retries_with_the_same_logical_request(self) -> None:
        request = BackendRequest.create(BackendAction.EVENT_STATUS)
        session = FakeSession(
            aiohttp.ClientConnectionError("offline"),
            FakeResponse(200, success_payload(request.request_id, {"phase": "OPEN"})),
        )
        sleep = AsyncMock()
        client = MainBackendClient(
            ENDPOINT,
            TOKEN,
            session=session,
            read_retries=1,
            sleep=sleep,
        )

        result = await client.execute(request)

        self.assertEqual(result.data["phase"], "OPEN")
        self.assertEqual(len(session.calls), 2)
        self.assertEqual(
            [
                json.loads(call[1]["data"].decode("utf-8"))["request_id"]
                for call in session.calls
            ],
            [request.request_id, request.request_id],
        )
        sleep.assert_awaited_once()

    async def test_tls_failure_is_never_retried(self) -> None:
        request = BackendRequest.create(BackendAction.EVENT_STATUS)
        tls_error = aiohttp.ServerFingerprintMismatch(
            b"expected",
            b"received",
            "backend.example",
            443,
        )
        session = FakeSession(tls_error, FakeResponse(200, {}))
        sleep = AsyncMock()
        client = MainBackendClient(
            ENDPOINT,
            TOKEN,
            session=session,
            read_retries=3,
            sleep=sleep,
        )

        with self.assertRaises(BackendTransportError) as context:
            await client.execute(request)

        self.assertFalse(context.exception.retryable)
        self.assertFalse(context.exception.outcome_uncertain)
        self.assertEqual(len(session.calls), 1)
        sleep.assert_not_awaited()

    async def test_ticket_write_is_not_automatically_retried(self) -> None:
        request = BackendRequest.create(
            BackendAction.TICKET_RESOLVE,
            actor_discord_user_id=123,
            discord_guild_id=456,
            discord_interaction_id=789,
            idempotency_key=str(uuid4()),
        )
        session = FakeSession(FakeResponse(503, {}), FakeResponse(200, {}))
        client = MainBackendClient(
            ENDPOINT,
            TOKEN,
            session=session,
            read_retries=3,
        )

        with self.assertRaises(BackendTransportError) as context:
            await client.execute(request)

        self.assertTrue(context.exception.outcome_uncertain)
        self.assertFalse(context.exception.retryable)
        self.assertEqual(len(session.calls), 1)

    async def test_mismatched_request_id_and_wrong_content_type_fail_closed(self) -> None:
        request = BackendRequest.create(BackendAction.EVENT_STATUS)
        mismatch = FakeSession(
            FakeResponse(200, success_payload(str(uuid4())))
        )
        with self.assertRaises(BackendProtocolError):
            await MainBackendClient(ENDPOINT, TOKEN, session=mismatch).execute(request)

        wrong_type = FakeSession(
            FakeResponse(
                200,
                success_payload(request.request_id),
                content_type="text/html",
            )
        )
        with self.assertRaises(BackendProtocolError):
            await MainBackendClient(ENDPOINT, TOKEN, session=wrong_type).execute(
                request
            )

    async def test_response_size_limit_is_enforced(self) -> None:
        request = BackendRequest.create(BackendAction.EVENT_STATUS)
        session = FakeSession(FakeResponse(200, raw=b"{}" * 20))
        client = MainBackendClient(
            ENDPOINT,
            TOKEN,
            session=session,
            max_response_bytes=10,
        )

        with self.assertRaises(BackendProtocolError):
            await client.execute(request)

    async def test_streaming_limit_rejects_a_lying_content_length(self) -> None:
        request = BackendRequest.create(BackendAction.EVENT_STATUS)
        session = FakeSession(
            FakeResponse(
                200,
                raw=b"{}" * 20,
                content_length=1,
                chunks=[b"{}" * 5, b"{}" * 15],
            )
        )
        client = MainBackendClient(
            ENDPOINT,
            TOKEN,
            session=session,
            max_response_bytes=10,
        )

        with self.assertRaises(BackendProtocolError):
            await client.execute(request)

    async def test_nonfinite_response_number_is_a_typed_protocol_error(self) -> None:
        request = BackendRequest.create(BackendAction.EVENT_STATUS)
        raw = (
            '{"api_version":"1","success":true,'
            f'"request_id":"{request.request_id}",'
            f'"server_time":"{SERVER_TIME}",'
            '"data":{"rating":1e999}}'
        ).encode("utf-8")
        session = FakeSession(FakeResponse(200, raw=raw))

        with self.assertRaises(BackendProtocolError):
            await MainBackendClient(ENDPOINT, TOKEN, session=session).execute(request)

    async def test_malformed_write_response_marks_outcome_uncertain(self) -> None:
        request = BackendRequest.create(
            BackendAction.TICKET_RESOLVE,
            actor_discord_user_id=123,
            discord_guild_id=456,
            discord_interaction_id=789,
            idempotency_key=str(uuid4()),
        )
        session = FakeSession(FakeResponse(200, raw=b"not-json"))

        with self.assertRaises(BackendProtocolError) as context:
            await MainBackendClient(ENDPOINT, TOKEN, session=session).execute(request)

        self.assertTrue(context.exception.outcome_uncertain)
        self.assertEqual(len(session.calls), 1)

    def test_https_and_exact_endpoint_path_are_required(self) -> None:
        with self.assertRaises(BackendConfigurationError):
            MainBackendClient("http://backend.example/internal/cody/v1", TOKEN)
        with self.assertRaises(BackendConfigurationError):
            MainBackendClient("https://backend.example/another-api", TOKEN)

        client = MainBackendClient(
            "http://localhost:8000/internal/cody/v1",
            TOKEN,
            allow_insecure_localhost=True,
        )
        self.assertEqual(
            client.endpoint,
            "http://localhost:8000/internal/cody/v1",
        )


if __name__ == "__main__":
    unittest.main()
