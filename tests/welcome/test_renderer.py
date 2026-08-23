from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from PIL import Image, ImageDraw

from cody.config import PROJECT_ROOT
from cody.features.welcome.quotes import load_welcome_quotes
from cody.features.welcome.renderer import (
    QUOTE_AREA_HEIGHT,
    QUOTE_AREA_WIDTH,
    QUOTE_LINE_SPACING,
    QUOTE_MAX_LINES,
    _layout_quote,
    create_welcome_card,
    render_welcome_card,
)


class WelcomeRendererTests(unittest.IsolatedAsyncioTestCase):
    def test_renderer_outputs_expected_png_size(self) -> None:
        avatar = (PROJECT_ROOT / "assets" / "branding" / "cody-icon.png").read_bytes()
        card = render_welcome_card(
            avatar,
            "Test Member",
            "0042",
            "Every layer depends on another.",
        )

        with Image.open(card) as image:
            self.assertEqual(image.size, (1200, 675))
            self.assertEqual(image.format, "PNG")

    def test_renderer_draws_the_supplied_quote(self) -> None:
        avatar = (PROJECT_ROOT / "assets" / "branding" / "cody-icon.png").read_bytes()

        first_card = render_welcome_card(avatar, "Test Member", "0042", "First quote")
        second_card = render_welcome_card(
            avatar,
            "Test Member",
            "0042",
            "A visibly different second quote",
        )

        self.assertNotEqual(first_card.getvalue(), second_card.getvalue())

    def test_all_quotes_fit_inside_the_inner_panel(self) -> None:
        image = Image.new("RGB", (1200, 675))
        draw = ImageDraw.Draw(image)

        for quote in load_welcome_quotes():
            with self.subTest(quote=quote):
                wrapped_quote, font = _layout_quote(draw, quote)
                lines = wrapped_quote.splitlines()
                box = draw.multiline_textbbox(
                    (0, 0),
                    wrapped_quote,
                    font=font,
                    spacing=QUOTE_LINE_SPACING,
                    align="center",
                )

                self.assertLessEqual(len(lines), QUOTE_MAX_LINES)
                self.assertLessEqual(box[3] - box[1], QUOTE_AREA_HEIGHT)
                for line in lines:
                    line_box = draw.textbbox((0, 0), line, font=font)
                    self.assertLessEqual(
                        line_box[2] - line_box[0],
                        QUOTE_AREA_WIDTH,
                    )

    async def test_member_count_falls_back_to_cached_members(self) -> None:
        expected = BytesIO(b"card")
        member = SimpleNamespace(
            display_avatar=SimpleNamespace(read=AsyncMock(return_value=b"avatar")),
            display_name="Test Member",
            guild=SimpleNamespace(member_count=None, members=[1, 2, 3]),
        )

        with (
            patch(
                "cody.features.welcome.renderer.random_welcome_quote",
                return_value="Selected quote",
            ),
            patch(
                "cody.features.welcome.renderer.render_welcome_card",
                return_value=expected,
            ) as renderer,
        ):
            result = await create_welcome_card(member)

        self.assertIs(result, expected)
        renderer.assert_called_once_with(
            b"avatar",
            "Test Member",
            "0003",
            "Selected quote",
        )


if __name__ == "__main__":
    unittest.main()
