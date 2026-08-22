"""Render personalized ETH Battlecode welcome cards in memory."""

import asyncio
from io import BytesIO

import discord
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

from cody.config import FONT_BODY, FONT_DISPLAY, FONT_MONO, WELCOME_BACKGROUND

CARD_WIDTH = 1200
CARD_HEIGHT = 675

GOLD = (232, 161, 60)
OFF_WHITE = (246, 239, 223)
MUTED = (180, 185, 180)
UMBRAL_GREEN = (123, 211, 137)


def _font(size: int, *, kind: str = "body") -> ImageFont.FreeTypeFont:
    """Load a bundled project font, with Pillow's font as a safe fallback."""

    paths = {
        "display": FONT_DISPLAY,
        "mono": FONT_MONO,
        "body": FONT_BODY,
    }
    path = paths[kind]
    if path.exists():
        return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default(size=size)


def _fitted_font(
    draw: ImageDraw.ImageDraw,
    text: str,
    *,
    maximum: int,
    minimum: int,
    width: int,
    kind: str = "display",
) -> ImageFont.FreeTypeFont:
    """Return the largest font size that fits within the supplied width."""

    for size in range(maximum, minimum - 1, -2):
        font = _font(size, kind=kind)
        box = draw.textbbox((0, 0), text, font=font)
        if box[2] - box[0] <= width:
            return font

    return _font(minimum, kind=kind)


def _chamfered_points(
    box: tuple[int, int, int, int],
    cut: int,
) -> list[tuple[int, int]]:
    x1, y1, x2, y2 = box
    return [
        (x1 + cut, y1),
        (x2 - cut, y1),
        (x2, y1 + cut),
        (x2, y2 - cut),
        (x2 - cut, y2),
        (x1 + cut, y2),
        (x1, y2 - cut),
        (x1, y1 + cut),
    ]


def _draw_chamfered_panel(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    *,
    cut: int = 18,
    fill: tuple[int, int, int, int] = (4, 10, 13, 150),
    outline_alpha: int = 170,
    width: int = 2,
) -> None:
    points = _chamfered_points(box, cut)
    draw.polygon(points, fill=fill)
    draw.line(
        points + [points[0]],
        fill=(*GOLD, outline_alpha),
        width=width,
        joint="curve",
    )


def _draw_corner_brackets(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    *,
    length: int = 72,
) -> None:
    x1, y1, x2, y2 = box
    color = (*GOLD, 220)
    width = 4

    draw.line((x1, y1 + length, x1, y1, x1 + length, y1), fill=color, width=width)
    draw.line((x2 - length, y1, x2, y1, x2, y1 + length), fill=color, width=width)
    draw.line((x1, y2 - length, x1, y2, x1 + length, y2), fill=color, width=width)
    draw.line((x2 - length, y2, x2, y2, x2, y2 - length), fill=color, width=width)


def render_welcome_card(
    avatar_bytes: bytes,
    display_name: str,
    arrival_code: str,
) -> BytesIO:
    """Render a personalized welcome card and return its PNG buffer."""

    with Image.open(WELCOME_BACKGROUND) as source:
        background = ImageOps.fit(
            source.convert("RGBA"),
            (CARD_WIDTH, CARD_HEIGHT),
            method=Image.Resampling.LANCZOS,
        )

    background = ImageEnhance.Color(background).enhance(0.72)
    background = ImageEnhance.Contrast(background).enhance(1.08)

    shade = Image.new("RGBA", background.size, (3, 7, 10, 105))
    canvas = Image.alpha_composite(background, shade)
    hud_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(hud_layer)

    # Project a restrained scan/grid layer over the world artwork.
    for y in range(0, CARD_HEIGHT, 12):
        draw.line((0, y, CARD_WIDTH, y), fill=(255, 255, 255, 3), width=1)
    for x in range(0, CARD_WIDTH, 120):
        draw.line((x, 0, x, CARD_HEIGHT), fill=(*GOLD, 3), width=1)

    _draw_chamfered_panel(
        draw,
        (270, 32, CARD_WIDTH - 270, CARD_HEIGHT - 42),
        cut=24,
        fill=(3, 9, 11, 145),
        outline_alpha=145,
    )
    _draw_corner_brackets(draw, (24, 24, CARD_WIDTH - 24, CARD_HEIGHT - 24))
    canvas = Image.alpha_composite(canvas, hud_layer)
    draw = ImageDraw.Draw(canvas)

    draw.text(
        (CARD_WIDTH // 2, 66),
        f"ARRIVAL // {arrival_code}",
        font=_font(30, kind="mono"),
        fill=GOLD,
        anchor="mm",
    )
    draw.line(
        (CARD_WIDTH // 2 - 130, 98, CARD_WIDTH // 2 + 130, 98),
        fill=GOLD,
        width=2,
    )
    draw.rectangle(
        (CARD_WIDTH // 2 - 142, 95, CARD_WIDTH // 2 - 134, 101),
        fill=GOLD,
    )
    draw.rectangle(
        (CARD_WIDTH // 2 + 134, 95, CARD_WIDTH // 2 + 142, 101),
        fill=GOLD,
    )

    avatar_size = 205
    avatar_x = CARD_WIDTH // 2 - avatar_size // 2
    avatar_y = 125

    with Image.open(BytesIO(avatar_bytes)) as avatar_source:
        avatar = ImageOps.fit(
            avatar_source.convert("RGBA"),
            (avatar_size, avatar_size),
            method=Image.Resampling.LANCZOS,
        )

    mask = Image.new("L", (avatar_size, avatar_size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, avatar_size - 1, avatar_size - 1), fill=255)
    avatar.putalpha(mask)

    glow_size = avatar_size + 64
    glow = Image.new("RGBA", (glow_size, glow_size), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse(
        (32, 32, glow_size - 32, glow_size - 32),
        fill=(*GOLD, 190),
    )
    glow = glow.filter(ImageFilter.GaussianBlur(23))
    canvas.alpha_composite(glow, (avatar_x - 32, avatar_y - 32))
    canvas.alpha_composite(avatar, (avatar_x, avatar_y))

    frame_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(frame_layer)
    draw.ellipse(
        (
            avatar_x - 7,
            avatar_y - 7,
            avatar_x + avatar_size + 7,
            avatar_y + avatar_size + 7,
        ),
        outline=GOLD,
        width=4,
    )
    draw.ellipse(
        (
            avatar_x - 17,
            avatar_y - 17,
            avatar_x + avatar_size + 17,
            avatar_y + avatar_size + 17,
        ),
        outline=(*GOLD, 75),
        width=2,
    )

    mid_y = avatar_y + avatar_size // 2
    draw.line((avatar_x - 65, mid_y, avatar_x - 18, mid_y), fill=(*GOLD, 170), width=2)
    draw.line(
        (avatar_x + avatar_size + 18, mid_y, avatar_x + avatar_size + 65, mid_y),
        fill=(*GOLD, 170),
        width=2,
    )
    draw.rectangle((avatar_x - 70, mid_y - 3, avatar_x - 64, mid_y + 3), fill=GOLD)
    draw.rectangle(
        (
            avatar_x + avatar_size + 64,
            mid_y - 3,
            avatar_x + avatar_size + 70,
            mid_y + 3,
        ),
        fill=GOLD,
    )
    canvas = Image.alpha_composite(canvas, frame_layer)
    draw = ImageDraw.Draw(canvas)

    name_font = _fitted_font(
        draw,
        display_name,
        maximum=60,
        minimum=34,
        width=760,
        kind="display",
    )
    draw.text(
        (CARD_WIDTH // 2, 386),
        display_name,
        font=name_font,
        fill=OFF_WHITE,
        stroke_width=1,
        stroke_fill=(8, 12, 13),
        anchor="mm",
    )
    draw.text(
        (CARD_WIDTH // 2, 440),
        "UMBRAL // REGISTRY",
        font=_font(25, kind="mono"),
        fill=UMBRAL_GREEN,
        anchor="mm",
    )
    draw.text(
        (CARD_WIDTH // 2, 480),
        "ASCENT STATUS // INITIAL",
        font=_font(18, kind="mono"),
        fill=MUTED,
        anchor="mm",
    )
    draw.text(
        (CARD_WIDTH // 2, 535),
        '"Past here, the sun is still a rumor."',
        font=_font(27, kind="body"),
        fill=OFF_WHITE,
        anchor="mm",
    )

    draw.text(
        (48, 625),
        "ENTRY NETWORK",
        font=_font(18, kind="mono"),
        fill=MUTED,
        anchor="lm",
    )
    draw.text(
        (CARD_WIDTH - 48, 625),
        "CODY // 01",
        font=_font(18, kind="mono"),
        fill=GOLD,
        anchor="rm",
    )

    output = BytesIO()
    canvas.convert("RGB").save(output, format="PNG", optimize=True)
    output.seek(0)
    return output


async def create_welcome_card(member: discord.Member) -> BytesIO:
    """Read a member avatar and render their card off the event loop."""

    avatar_bytes = await member.display_avatar.read()
    member_count = member.guild.member_count
    if member_count is None:
        member_count = len(member.guild.members)

    arrival_code = f"{member_count:04d}"

    return await asyncio.to_thread(
        render_welcome_card,
        avatar_bytes,
        member.display_name,
        arrival_code,
    )
