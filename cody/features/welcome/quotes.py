"""Load and select quotes for welcome cards."""

import json
import logging
import random
from pathlib import Path

from cody.config import WELCOME_QUOTES


LOGGER = logging.getLogger(__name__)

FALLBACK_WELCOME_QUOTE = "Past here, the sun is still a rumor."


def load_welcome_quotes(path: Path = WELCOME_QUOTES) -> tuple[str, ...]:
    """Return normalized quotes from the welcome asset, or a safe fallback."""

    try:
        with path.open(encoding="utf-8") as quotes_file:
            payload = json.load(quotes_file)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        LOGGER.warning("Could not load welcome quotes from %s: %s", path, error)
        return (FALLBACK_WELCOME_QUOTE,)

    if not isinstance(payload, dict) or not isinstance(payload.get("quotes"), list):
        LOGGER.warning("Welcome quote file %s does not contain a quotes list", path)
        return (FALLBACK_WELCOME_QUOTE,)

    quotes = tuple(
        normalized
        for quote in payload["quotes"]
        if isinstance(quote, str) and (normalized := " ".join(quote.split()))
    )
    if not quotes:
        LOGGER.warning("Welcome quote file %s contains no usable quotes", path)
        return (FALLBACK_WELCOME_QUOTE,)

    return quotes


def random_welcome_quote(path: Path = WELCOME_QUOTES) -> str:
    """Choose one welcome quote at random."""

    return random.choice(load_welcome_quotes(path))
