"""Environment and repository configuration for Cody."""

import math
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _channel_id(environment_name: str, default: int) -> int:
    value = os.getenv(environment_name)
    if value is None:
        return default

    try:
        return int(value)
    except ValueError as error:
        raise RuntimeError(f"{environment_name} must be a Discord channel ID.") from error


def _role_id(environment_name: str, default: int) -> int:
    value = os.getenv(environment_name)
    if value is None:
        return default

    try:
        return int(value)
    except ValueError as error:
        raise RuntimeError(f"{environment_name} must be a Discord role ID.") from error


def _boolean(environment_name: str, default: bool) -> bool:
    value = os.getenv(environment_name)
    if value is None:
        return default

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise RuntimeError(f"{environment_name} must be true or false.")


def _positive_float(environment_name: str, default: float) -> float:
    value = os.getenv(environment_name)
    if value is None:
        return default
    try:
        parsed = float(value)
    except ValueError as error:
        raise RuntimeError(f"{environment_name} must be a number.") from error
    if not math.isfinite(parsed) or parsed <= 0:
        raise RuntimeError(
            f"{environment_name} must be a finite number greater than zero."
        )
    return parsed


def _nonnegative_int(environment_name: str, default: int) -> int:
    value = os.getenv(environment_name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError as error:
        raise RuntimeError(f"{environment_name} must be an integer.") from error
    if parsed < 0:
        raise RuntimeError(f"{environment_name} must not be negative.")
    return parsed


WELCOME_CHANNEL_ID = _channel_id("CODY_WELCOME_CHANNEL_ID", 1540841975320813649)
RULES_CHANNEL_ID = _channel_id("CODY_RULES_CHANNEL_ID", 1540846388328275990)
WORLD_CHANNEL_ID = _channel_id("CODY_WORLD_CHANNEL_ID", 1540846427377373284)

PARTICIPANT_ROLE_ID = _role_id(
    "CODY_PARTICIPANT_ROLE_ID",
    1541112817476702238,
)
ADMIN_ROLE_ID = _role_id(
    "CODY_ADMIN_ROLE_ID",
    1540821890510229571,
)
LOG_CHANNEL_ID = _channel_id(
    "CODY_LOG_CHANNEL_ID",
    1541131430682431518,
)
SUPPORT_CHANNEL_ID = _channel_id(
    "CODY_SUPPORT_CHANNEL_ID",
    1541132121551274154,
)
TICKET_CATEGORY_ID = _channel_id(
    "CODY_TICKET_CATEGORY_ID",
    1541137977613488149,
)
ORGANIZER_ROLE_ID = _role_id(
    "CODY_ORGANIZER_ROLE_ID",
    1540821070213292125,
)

STATS_MEMBERS_CHANNEL_ID = _channel_id(
    "CODY_STATS_MEMBERS_CHANNEL_ID",
    1541109424796602418,
)
STATS_UMBRAL_CHANNEL_ID = _channel_id(
    "CODY_STATS_UMBRAL_CHANNEL_ID",
    1541109668263362691,
)
STATS_LUMEN_CHANNEL_ID = _channel_id(
    "CODY_STATS_LUMEN_CHANNEL_ID",
    1541109719530344538,
)
STATS_HELIO_CHANNEL_ID = _channel_id(
    "CODY_STATS_HELIO_CHANNEL_ID",
    1541109796063674519,
)
STATS_ACTIVE_TEAMS_CHANNEL_ID = _channel_id(
    "CODY_STATS_ACTIVE_TEAMS_CHANNEL_ID",
    1541111483897749534,
)
STATS_MATCHES_TODAY_CHANNEL_ID = _channel_id(
    "CODY_STATS_MATCHES_TODAY_CHANNEL_ID",
    1541111104661495929,
)
STATS_GRID_OUTPUT_CHANNEL_ID = _channel_id(
    "CODY_STATS_GRID_OUTPUT_CHANNEL_ID",
    1541111224882823239,
)
STATS_LADDER_LEADER_CHANNEL_ID = _channel_id(
    "CODY_STATS_LADDER_LEADER_CHANNEL_ID",
    1541111316310396949,
)

STATS_UMBRAL_ROLE_ID = _role_id(
    "CODY_STATS_UMBRAL_ROLE_ID",
    1541114274079051959,
)
STATS_LUMEN_ROLE_ID = _role_id(
    "CODY_STATS_LUMEN_ROLE_ID",
    1541114432954830868,
)
STATS_HELIO_ROLE_ID = _role_id(
    "CODY_STATS_HELIO_ROLE_ID",
    1541114604002873395,
)

STATS_PROVIDER = os.getenv("CODY_STATS_PROVIDER", "discord").strip().lower()
STATS_ENDPOINT = os.getenv("CODY_STATS_ENDPOINT", "").strip()
STATS_INCLUDE_BOTS = _boolean("CODY_STATS_INCLUDE_BOTS", False)

BACKEND_API_VERSION = "1"
BACKEND_TIMEOUT_SECONDS = _positive_float("CODY_BACKEND_TIMEOUT_SECONDS", 10.0)
BACKEND_READ_RETRIES = _nonnegative_int("CODY_BACKEND_READ_RETRIES", 2)
BACKEND_MAX_REQUEST_BYTES = _nonnegative_int(
    "CODY_BACKEND_MAX_REQUEST_BYTES",
    65_536,
)
BACKEND_MAX_RESPONSE_BYTES = _nonnegative_int(
    "CODY_BACKEND_MAX_RESPONSE_BYTES",
    1_048_576,
)
BACKEND_ALLOW_INSECURE_LOCALHOST = _boolean(
    "CODY_BACKEND_ALLOW_INSECURE_LOCALHOST",
    False,
)

WELCOME_BACKGROUND = PROJECT_ROOT / "assets" / "welcome" / "umbral-background.png"
WELCOME_QUOTES = PROJECT_ROOT / "assets" / "welcome" / "welcome_quotes.json"
FONT_DIR = PROJECT_ROOT / "assets" / "fonts"
FONT_DISPLAY = FONT_DIR / "play-display.ttf"
FONT_MONO = FONT_DIR / "share-tech-system.ttf"
FONT_BODY = FONT_DISPLAY


def get_discord_token() -> str:
    """Read Cody's token without storing it in source or on disk."""

    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError(
            "DISCORD_TOKEN is not set. Start Cody with the launcher in scripts/."
        )
    return token


def get_backend_endpoint() -> str:
    """Read the single Main Backend integration endpoint from the environment."""

    endpoint = os.getenv("CODY_BACKEND_ENDPOINT", "").strip()
    if not endpoint:
        raise RuntimeError(
            "CODY_BACKEND_ENDPOINT is required for the Main Backend provider."
        )
    return endpoint


def get_backend_service_token() -> str:
    """Read Cody's Main Backend credential without storing it in source."""

    token = os.getenv("CODY_BACKEND_SERVICE_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "CODY_BACKEND_SERVICE_TOKEN is required for the Main Backend provider."
        )
    return token
