import unittest

from cody.features.server_stats.constants import SERVER_STATS_CONFIG


class ServerStatsConfigurationTests(unittest.TestCase):
    def test_supplied_discord_ids_are_the_defaults(self) -> None:
        self.assertEqual(SERVER_STATS_CONFIG.umbral_role_id, 1541114274079051959)
        self.assertEqual(SERVER_STATS_CONFIG.lumen_belt_role_id, 1541114432954830868)
        self.assertEqual(SERVER_STATS_CONFIG.helio_role_id, 1541114604002873395)

        self.assertEqual(SERVER_STATS_CONFIG.member_channel_id, 1541109424796602418)
        self.assertEqual(SERVER_STATS_CONFIG.umbral_channel_id, 1541109668263362691)
        self.assertEqual(SERVER_STATS_CONFIG.lumen_belt_channel_id, 1541109719530344538)
        self.assertEqual(SERVER_STATS_CONFIG.helio_channel_id, 1541109796063674519)
        self.assertEqual(
            SERVER_STATS_CONFIG.active_teams_channel_id,
            1541111483897749534,
        )
        self.assertEqual(
            SERVER_STATS_CONFIG.matches_today_channel_id,
            1541111104661495929,
        )
        self.assertEqual(
            SERVER_STATS_CONFIG.grid_output_channel_id,
            1541111224882823239,
        )
        self.assertEqual(
            SERVER_STATS_CONFIG.ladder_leader_channel_id,
            1541111316310396949,
        )


if __name__ == "__main__":
    unittest.main()
