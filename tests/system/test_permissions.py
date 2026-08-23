from types import SimpleNamespace
import unittest

from cody.config import ADMIN_ROLE_ID, PARTICIPANT_ROLE_ID
from cody.features.server_stats.cog import ServerStatsCog
from cody.features.system.cog import SystemCog
from cody.features.welcome.cog import WelcomeCog
from cody.shared.permissions import (
    CodyRoleRequired,
    admin_access_check,
    member_has_role,
    participant_access_check,
)


def interaction_with_roles(*role_ids: int):
    return SimpleNamespace(
        user=SimpleNamespace(
            roles=[SimpleNamespace(id=role_id) for role_id in role_ids]
        )
    )


class CodyPermissionTests(unittest.IsolatedAsyncioTestCase):
    def test_configured_role_ids_match_the_supplied_defaults(self) -> None:
        self.assertEqual(PARTICIPANT_ROLE_ID, 1541112817476702238)
        self.assertEqual(ADMIN_ROLE_ID, 1540821890510229571)

    def test_member_role_lookup_uses_snowflake_ids(self) -> None:
        interaction = interaction_with_roles(PARTICIPANT_ROLE_ID)

        self.assertTrue(member_has_role(interaction.user, PARTICIPANT_ROLE_ID))
        self.assertFalse(member_has_role(interaction.user, ADMIN_ROLE_ID))

    async def test_participant_role_can_use_participant_commands(self) -> None:
        allowed = await participant_access_check(
            interaction_with_roles(PARTICIPANT_ROLE_ID)
        )

        self.assertTrue(allowed)

    async def test_admin_role_can_also_use_participant_commands(self) -> None:
        allowed = await participant_access_check(
            interaction_with_roles(ADMIN_ROLE_ID)
        )

        self.assertTrue(allowed)

    async def test_participant_cannot_use_admin_commands(self) -> None:
        with self.assertRaises(CodyRoleRequired):
            await admin_access_check(interaction_with_roles(PARTICIPANT_ROLE_ID))

    async def test_admin_role_can_use_admin_commands(self) -> None:
        allowed = await admin_access_check(interaction_with_roles(ADMIN_ROLE_ID))

        self.assertTrue(allowed)

    async def test_user_without_roles_cannot_use_participant_commands(self) -> None:
        with self.assertRaises(CodyRoleRequired):
            await participant_access_check(SimpleNamespace(user=SimpleNamespace()))

    def test_registered_commands_keep_their_role_checks(self) -> None:
        system_checks = {
            command.name: [check.__name__ for check in command.checks]
            for command in SystemCog.__cog_app_commands__
        }
        welcome_checks = {
            command.name: [check.__name__ for check in command.checks]
            for command in WelcomeCog.__cog_app_commands__
        }
        stats_checks = {
            command.name: [check.__name__ for check in command.checks]
            for command in ServerStatsCog.__cog_app_commands__
        }

        self.assertEqual(
            system_checks,
            {
                "ping": ["participant_access_check"],
                "about": ["participant_access_check"],
            },
        )
        self.assertEqual(
            welcome_checks,
            {"test_welcome": ["admin_access_check"]},
        )
        self.assertEqual(
            stats_checks,
            {
                "refresh": ["admin_access_check"],
                "permissions": ["admin_access_check"],
            },
        )


if __name__ == "__main__":
    unittest.main()
