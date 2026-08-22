"""Environment and repository configuration for Cody."""

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


WELCOME_CHANNEL_ID = _channel_id("CODY_WELCOME_CHANNEL_ID", 1540841975320813649)
RULES_CHANNEL_ID = _channel_id("CODY_RULES_CHANNEL_ID", 1540846388328275990)
WORLD_CHANNEL_ID = _channel_id("CODY_WORLD_CHANNEL_ID", 1540846427377373284)

WELCOME_BACKGROUND = PROJECT_ROOT / "assets" / "welcome" / "umbral-background.png"
FONT_DIR = PROJECT_ROOT / "assets" / "fonts"
FONT_DISPLAY = FONT_DIR / "play-display.ttf"
FONT_MONO = FONT_DIR / "share-tech-system.ttf"
FONT_BODY = FONT_DISPLAY


def get_discord_token() -> str:
    """Read Cody's token without storing it in source or on disk."""

    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError(
            "DISCORD_TOKEN is not set. Start Cody with scripts/start-bot.ps1."
        )
    return token
