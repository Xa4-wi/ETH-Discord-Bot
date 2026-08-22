"""Run Cody."""

from cody.bot import create_bot
from cody.config import get_discord_token
from cody.shared.logging import configure_logging


def main() -> None:
    configure_logging()
    create_bot().run(get_discord_token())


if __name__ == "__main__":
    main()
