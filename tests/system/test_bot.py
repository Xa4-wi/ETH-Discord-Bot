from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock

from cody.bot import CodyBot


class CodyBotTests(unittest.IsolatedAsyncioTestCase):
    async def test_legacy_guild_command_copies_are_cleared_once(self) -> None:
        guild = SimpleNamespace(id=123, name="Test Guild")
        tree = SimpleNamespace(
            clear_commands=Mock(),
            sync=AsyncMock(return_value=[]),
        )
        bot = SimpleNamespace(
            guild_command_copies_cleared=False,
            guilds=[guild],
            tree=tree,
        )

        await CodyBot.clear_legacy_guild_command_copies(bot)
        await CodyBot.clear_legacy_guild_command_copies(bot)

        tree.clear_commands.assert_called_once_with(guild=guild)
        tree.sync.assert_awaited_once_with(guild=guild)
        self.assertTrue(bot.guild_command_copies_cleared)


if __name__ == "__main__":
    unittest.main()
