import unittest

from cody.features.server_stats.cog import ServerStatsCog


class ServerStatsCogTests(unittest.TestCase):
    def test_admin_commands_are_refresh_and_permissions(self) -> None:
        command_names = {
            command.name for command in ServerStatsCog.__cog_app_commands__
        }

        self.assertEqual(command_names, {"refresh", "permissions"})


if __name__ == "__main__":
    unittest.main()
