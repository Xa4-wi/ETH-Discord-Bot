from types import SimpleNamespace
import unittest

import discord

from cody.config import SUPPORT_CHANNEL_ID, TICKET_CATEGORY_ID
from cody.features.tickets.cog import TicketCog
from cody.features.tickets.models import TicketCategory, TicketStatus
from cody.features.tickets.views import (
    SupportPanelView,
    TicketActionsView,
    TicketCategoryView,
    support_panel_embed,
)


class TicketViewAndCogTests(unittest.IsolatedAsyncioTestCase):
    def test_supplied_channel_defaults_are_configured(self) -> None:
        self.assertEqual(SUPPORT_CHANNEL_ID, 1541132121551274154)
        self.assertEqual(TICKET_CATEGORY_ID, 1541137977613488149)

    def test_admin_commands_have_role_checks_and_visibility(self) -> None:
        command_checks = {
            command.name: [check.__name__ for check in command.checks]
            for command in TicketCog.__cog_app_commands__
        }
        permissions = getattr(
            TicketCog,
            "__discord_app_commands_default_permissions__",
        )

        self.assertEqual(
            command_checks,
            {
                "setup": ["admin_access_check"],
                "status": ["admin_access_check"],
            },
        )
        self.assertEqual(permissions, discord.Permissions(administrator=True))

    async def test_persistent_views_use_stable_component_ids(self) -> None:
        controller = SimpleNamespace()
        panel = SupportPanelView(controller)
        actions = TicketActionsView(controller)

        self.assertTrue(panel.is_persistent())
        self.assertTrue(actions.is_persistent())
        self.assertEqual(
            [item.custom_id for item in panel.children],
            ["cody:tickets:open"],
        )
        self.assertEqual(
            [item.custom_id for item in actions.children],
            [
                "cody:tickets:claim",
                "cody:tickets:release",
                "cody:tickets:resolve",
            ],
        )

    async def test_initial_action_state_prevents_release_before_claim(self) -> None:
        view = TicketActionsView(SimpleNamespace(), TicketStatus.OPEN)
        state = {item.custom_id: item.disabled for item in view.children}

        self.assertFalse(state["cody:tickets:claim"])
        self.assertTrue(state["cody:tickets:release"])
        self.assertFalse(state["cody:tickets:resolve"])

    async def test_category_picker_lists_all_intake_categories(self) -> None:
        view = TicketCategoryView(SimpleNamespace())
        select = view.children[0]

        self.assertEqual(
            [option.value for option in select.options],
            [category.value for category in TicketCategory],
        )

    def test_support_panel_has_recovery_marker(self) -> None:
        self.assertEqual(
            support_panel_embed().footer.text,
            "CODY // SUPPORT INTERFACE",
        )


if __name__ == "__main__":
    unittest.main()
