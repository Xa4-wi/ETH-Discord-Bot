from types import SimpleNamespace
import unittest

from cody.config import ROLE_CHANNEL_ID, RULES_CHANNEL_ID
from cody.features.welcome.views import welcome_view


class WelcomeViewTests(unittest.IsolatedAsyncioTestCase):
    async def test_view_uses_components_v2_and_attached_card(self) -> None:
        member = SimpleNamespace(
            display_name="Test Member",
            mention="<@123>",
            guild=SimpleNamespace(id=456),
        )

        view = welcome_view(member, "arrival-123.png")
        payload = view.to_components()
        media_url = payload[0]["components"][0]["items"][0]["media"]["url"]

        self.assertTrue(view.has_components_v2())
        self.assertEqual(media_url, "attachment://arrival-123.png")

        buttons = payload[0]["components"][3]["components"]
        self.assertEqual(
            [button["label"] for button in buttons],
            ["Rules", "Choose Role"],
        )
        self.assertEqual(
            [button["url"] for button in buttons],
            [
                f"https://discord.com/channels/456/{RULES_CHANNEL_ID}",
                f"https://discord.com/channels/456/{ROLE_CHANNEL_ID}",
            ],
        )


if __name__ == "__main__":
    unittest.main()
