"""Safe, typed failures for the Main Backend integration."""

from __future__ import annotations


DEFAULT_UNAVAILABLE_MESSAGE = (
    "Battlecode data is currently unavailable. Please try again shortly."
)

SAFE_ERROR_MESSAGES = {
    "API_VERSION_UNSUPPORTED": DEFAULT_UNAVAILABLE_MESSAGE,
    "SERVICE_AUTH_FAILED": DEFAULT_UNAVAILABLE_MESSAGE,
    "USER_NOT_LINKED": (
        "Your Discord account is not connected to an ETH Battlecode participant. "
        "Sign in on the website with Discord first."
    ),
    "USER_NOT_FOUND": "Your participant account could not be found.",
    "NO_TEAM": "Your participant account is not currently assigned to a team.",
    "PERMISSION_DENIED": "You do not have access to that Battlecode information.",
    "TEAM_NOT_FOUND": "That team could not be found.",
    "SUBMISSION_NOT_FOUND": "That submission could not be found.",
    "MATCH_NOT_FOUND": "That match could not be found.",
    "TICKET_NOT_FOUND": "That support ticket could not be found.",
    "TICKET_RESOLVED": "That support ticket is already resolved.",
    "OPEN_TICKET_EXISTS": "You already have an active support ticket.",
    "TICKET_ALREADY_CLAIMED": "That support ticket is already assigned.",
    "TICKET_INVALID_STATE": "That support ticket cannot be changed right now.",
    "IDEMPOTENCY_CONFLICT": (
        "Cody could not safely repeat that support action. Please try again."
    ),
    "CURSOR_INVALID": "That result page is no longer available. Start again.",
    "REQUEST_TOO_LARGE": "That request is too large for Cody to process.",
    "RATE_LIMITED": "Too many requests were made. Please try again shortly.",
    "INVALID_REQUEST": "Cody could not send a valid request to Battlecode.",
    "BACKEND_UNAVAILABLE": DEFAULT_UNAVAILABLE_MESSAGE,
    "INFRASTRUCTURE_UNAVAILABLE": DEFAULT_UNAVAILABLE_MESSAGE,
    "INTERNAL_ERROR": DEFAULT_UNAVAILABLE_MESSAGE,
}


class BackendIntegrationError(RuntimeError):
    """Base class for failures crossing the Cody/backend boundary."""


class BackendConfigurationError(BackendIntegrationError):
    """Backend settings are missing or unsafe."""


class BackendProtocolError(BackendIntegrationError):
    """The backend response did not satisfy the versioned contract."""

    def __init__(
        self,
        message: str,
        *,
        request_id: str | None = None,
        outcome_uncertain: bool = False,
    ) -> None:
        super().__init__(message)
        self.request_id = request_id
        # A malformed response to a mutation does not prove whether the Main
        # Backend committed that mutation. Features must reconcile before they
        # decide whether to replay the same idempotency key.
        self.outcome_uncertain = outcome_uncertain


class BackendTransportError(BackendIntegrationError):
    """The HTTP exchange failed before a valid response was obtained."""

    def __init__(
        self,
        message: str = DEFAULT_UNAVAILABLE_MESSAGE,
        *,
        request_id: str,
        retryable: bool,
        outcome_uncertain: bool = False,
    ) -> None:
        super().__init__(message)
        self.request_id = request_id
        self.retryable = retryable
        self.outcome_uncertain = outcome_uncertain


class BackendActionError(BackendIntegrationError):
    """A validated backend rejection with a user-safe public message."""

    def __init__(
        self,
        *,
        code: str,
        request_id: str,
        retryable: bool,
        http_status: int,
    ) -> None:
        self.code = code
        self.request_id = request_id
        self.retryable = retryable
        self.http_status = http_status
        super().__init__(SAFE_ERROR_MESSAGES.get(code, DEFAULT_UNAVAILABLE_MESSAGE))
