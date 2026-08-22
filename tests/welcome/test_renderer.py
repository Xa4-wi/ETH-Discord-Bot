from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from PIL import Image

from cody.config import PROJECT_ROOT
from cody.features.welcome.renderer import create_welcome_card, render_welcome_card


class WelcomeRendererTests(unittest.IsolatedAsyncioTestCase):
    def test_renderer_outputs_expected_png_size(self) -> None:
        avatar = (PROJECT_ROOT / "assets" / "branding" / "cody-icon.png").read_bytes()
        card = render_welcome_card(avatar, "Test Member", "0042")

        with Image.open(card) as image:
            self.assertEqual(image.size, (1200, 675))
            self.assertEqual(image.format, "PNG")

    async def test_member_count_falls_back_to_cached_members(self) -> None:
        expected = BytesIO(b"card")
        member = SimpleNamespace(
            display_avatar=SimpleNamespace(read=AsyncMock(return_value=b"avatar")),
            display_name="Test Member",
            guild=SimpleNamespace(member_count=None, members=[1, 2, 3]),
        )

        with patch(
            "cody.features.welcome.renderer.render_welcome_card",
            return_value=expected,
        ) as renderer:
            result = await create_welcome_card(member)

        self.assertIs(result, expected)
        renderer.assert_called_once_with(b"avatar", "Test Member", "0003")


if __name__ == "__main__":
    unittest.main()
