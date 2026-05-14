"""Entry point: render Yoda, sleep, repeat.

Run as ``python3 -m src.main`` from the repo root, or via the systemd unit
``tamagotchi-yoda.service``.
"""

import logging
import random
import signal
import sys
import time

from PIL import Image, ImageDraw, ImageFont

from . import config, events, fortune
from .display import Display
from .elements import ELEMENT_GLYPH
from .lifecycle import STAGE_SCALE
from .market import fetch_current as fetch_market_current
from .sprite import YodaSprite
from .state_machine import YodaState
from .weather import fetch_current as fetch_weather_current


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("yoda")


_STAT_ICONS = ("H", "*", "+", "Z")  # hunger / happiness / health / energy
_STAT_KEYS = ("hunger", "happiness", "health", "energy")


def _draw_status_bar(canvas: Image.Image, state: YodaState, font) -> None:
    draw = ImageDraw.Draw(canvas)
    y = config.STATUS_BAR_Y
    h = config.STATUS_BAR_H
    cell_w = config.STAT_CELL_W

    for i, (icon, key) in enumerate(zip(_STAT_ICONS, _STAT_KEYS)):
        x0 = i * cell_w
        draw.text((x0 + 1, y), icon, font=font, fill=0)
        bar_x0 = x0 + 10
        bar_x1 = x0 + cell_w - 4
        draw.rectangle((bar_x0, y + 3, bar_x1, y + h - 4), outline=0, fill=255)
        v = max(0.0, min(100.0, float(state.data["stats"].get(key, 0))))
        fill_w = int((bar_x1 - bar_x0 - 1) * v / 100.0)
        if fill_w > 0:
            draw.rectangle(
                (bar_x0 + 1, y + 4, bar_x0 + 1 + fill_w, y + h - 5), fill=0
            )

    # Element glyph in the top-right.
    elem = state.dominant_element
    glyph = ELEMENT_GLYPH.get(elem, "?")
    gx = config.ELEMENT_GLYPH_X
    draw.rectangle((gx, y, gx + 14, y + h - 2), outline=0, fill=255)
    draw.text((gx + 4, y + 1), glyph, font=font, fill=0)

    draw.line((0, y + h, config.EPD_WIDTH, y + h), fill=0)


def _scaled_box(scale: float) -> tuple:
    """Return (offset_x, offset_y, new_w, new_h) inside the 45x55 sprite box
    for a sprite scaled by ``scale``. Mirrors YodaSprite.blit_scaled anchoring.
    """
    new_w = max(8, int(round(config.YODA_WIDTH * scale)))
    new_h = max(10, int(round(config.YODA_HEIGHT * scale)))
    return (
        (config.YODA_WIDTH - new_w) // 2,
        config.YODA_HEIGHT - new_h,
        new_w,
        new_h,
    )


def _draw_aura(canvas: Image.Image, x: int, y: int, scale: float, mood: str) -> None:
    """Procedural aura around the sprite, driven by market mood. 1-bit only."""
    if mood == "neutral":
        return

    draw = ImageDraw.Draw(canvas)
    ox, oy, nw, nh = _scaled_box(scale)
    left = x + ox
    top = y + oy
    right = left + nw
    bottom = top + nh
    cx = left + nw // 2

    if mood == "panic":
        # Jagged 1-px "static" scattered just outside the bounding box.
        import random as _r
        rng = _r.Random((left * 31 + top * 17 + nh) & 0xFFFF)
        for _ in range(10):
            side = rng.randint(0, 3)
            if side == 0:    # top
                px, py = rng.randint(left - 3, right + 3), top - rng.randint(1, 3)
            elif side == 1:  # right
                px, py = right + rng.randint(1, 3), rng.randint(top, bottom)
            elif side == 2:  # bottom
                px, py = rng.randint(left - 3, right + 3), bottom + rng.randint(1, 3)
            else:            # left
                px, py = left - rng.randint(1, 3), rng.randint(top, bottom)
            if 0 <= px < canvas.size[0] and 0 <= py < canvas.size[1]:
                canvas.putpixel((px, py), 0)

    elif mood == "fear":
        # Single downward droplet pixel near the head.
        droplet_x = left + nw // 3
        for dy, dx in ((0, 0), (1, 0), (2, 0), (3, -1), (3, 0), (3, 1), (4, 0)):
            px, py = droplet_x + dx, top - 5 + dy
            if 0 <= px < canvas.size[0] and 0 <= py < canvas.size[1]:
                canvas.putpixel((px, py), 0)

    elif mood == "greed":
        # Two-three upward floating dots above the head.
        for i, dy in enumerate((-3, -6, -9)):
            r = 1 if i == 0 else 0
            if r:
                draw.ellipse((cx - 1, top + dy - 1, cx + 1, top + dy + 1), fill=0)
            else:
                canvas.putpixel((cx, top + dy), 0)

    elif mood == "euphoria":
        # Six 2-px radiating lines around the sprite centre.
        import math
        cy = top + nh // 2
        r_in = max(nw, nh) // 2 + 4
        r_out = r_in + 6
        for i in range(8):
            ang = i * (math.pi / 4)
            x0 = int(cx + r_in * math.cos(ang))
            y0 = int(cy + r_in * math.sin(ang))
            x1 = int(cx + r_out * math.cos(ang))
            y1 = int(cy + r_out * math.sin(ang))
            draw.line((x0, y0, x1, y1), fill=0, width=1)


def _market_readout(state: YodaState) -> str:
    """Compact second-line subtext: F&G score + mood bucket. Falls back to
    element + mood if we haven't successfully fetched the market yet."""
    market = state.data.get("last_market") or {}
    mood = state.data.get("market_mood", "neutral")
    score = market.get("score")
    if score is not None:
        return f"F&G {score} \xb7 {mood}"
    return f"{state.dominant_element} \xb7 {mood}"


def _draw_bubble(canvas: Image.Image, state: YodaState, text: str, font) -> None:
    draw = ImageDraw.Draw(canvas)
    x, y = config.BUBBLE_X, config.BUBBLE_Y
    w, h = config.BUBBLE_W, config.BUBBLE_H

    for cx, cy, r in config.BUBBLE_DOTS:
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=0, fill=255)

    if hasattr(draw, "rounded_rectangle"):
        draw.rounded_rectangle(
            (x, y, x + w, y + h), radius=8, outline=0, fill=255, width=1
        )
    else:
        draw.rectangle((x, y, x + w, y + h), outline=0, fill=255, width=1)

    line_x = x + config.BUBBLE_TEXT_X_PAD
    line1_y = y + config.BUBBLE_TEXT_Y_PAD
    line2_y = line1_y + config.BUBBLE_LINE_HEIGHT
    draw.text((line_x, line1_y), text, font=font, fill=0)
    draw.text((line_x, line2_y), _market_readout(state), font=font, fill=0)


def _draw_banner(canvas: Image.Image, state: YodaState, font) -> None:
    draw = ImageDraw.Draw(canvas)
    stage = state.data.get("stage", "egg")
    elem = state.dominant_element
    event_str = events.banner(state.data["event_state"].get("active", []))
    fortune_str = fortune.banner(state.data["fortune_state"].get("active", []))

    parts = [stage.upper(), elem.title()]
    if event_str:
        parts.append(event_str)
    if fortune_str:
        parts.append(fortune_str)
    if state.data.get("dead"):
        parts = ["GONE", f"({state.data.get('death_reason') or '?'})"]

    text = "  ".join(parts)
    draw.line((0, config.BANNER_Y - 1, config.EPD_WIDTH, config.BANNER_Y - 1), fill=0)
    draw.text((2, config.BANNER_Y), text, font=font, fill=0)


def render_frame(state: YodaState, yoda: YodaSprite, font) -> Image.Image:
    canvas = Image.new("1", (config.EPD_WIDTH, config.EPD_HEIGHT), 255)

    _draw_status_bar(canvas, state, font)

    stage = state.data.get("stage", "egg")
    variant = "egg" if stage == "egg" else state.data["sprite_variant"]
    scale = STAGE_SCALE.get(stage, 1.0)
    x = config.YODA_X + state.data.get("pose_dx", 0)
    y = config.YODA_Y + state.data.get("pose_dy", 0)

    # Aura drawn BEFORE the sprite so the silhouette overlays it cleanly.
    _draw_aura(canvas, x, y, scale, state.data.get("market_mood", "neutral"))
    yoda.blit_scaled(canvas, x, y, variant, scale)

    if state.data["observation_visible"] and state.data["observation_text"]:
        _draw_bubble(canvas, state, state.data["observation_text"], font)

    _draw_banner(canvas, state, font)
    return canvas


def main() -> None:
    random.seed()
    display = Display()
    yoda = YodaSprite()
    font = ImageFont.load_default()
    state = YodaState(config.STATE_FILE)

    def _shutdown(signum, frame):
        log.info("signal %s received — saving state and exiting", signum)
        state.save()
        try:
            display.clear()
        except Exception as e:
            log.warning("display.clear() failed during shutdown: %s", e)
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    log.info(
        "boot tick=%d stage=%s dominant=%s — fetching weather + market",
        state.data["ticks"],
        state.data.get("stage"),
        state.dominant_element,
    )
    state.boot_refresh(
        fetch_weather=fetch_weather_current,
        fetch_market=fetch_market_current,
    )
    log.info(
        "boot fetch complete: weather=%s market_score=%s mood=%s obs=%r",
        (state.data["last_weather"] or {}).get("weathercode"),
        (state.data["last_market"] or {}).get("score"),
        state.data.get("market_mood"),
        state.data.get("observation_text"),
    )

    img = render_frame(state, yoda, font)
    display.full_refresh(img)
    state.data["full_refresh_due"] = False
    state.save()
    display.sleep()

    while True:
        interval = max(1, int(state.data["next_interval"]))
        log.info("sleeping %d s until next tick", interval)
        time.sleep(interval)

        state.tick(
            fetch_weather=fetch_weather_current,
            fetch_market=fetch_market_current,
        )
        img = render_frame(state, yoda, font)
        display.full_refresh(img)
        if state.data["full_refresh_due"]:
            state.data["full_refresh_due"] = False
            state.save()
        log.info(
            "tick=%d stage=%s stats=%s dominant=%s mood=%s events=%s fortune=%s obs=%r",
            state.data["ticks"],
            state.data.get("stage"),
            {k: round(state.data["stats"][k], 1) for k in _STAT_KEYS},
            state.dominant_element,
            state.data.get("market_mood"),
            state.data["event_state"].get("active"),
            state.data["fortune_state"].get("active"),
            state.data.get("observation_text"),
        )
        display.sleep()


if __name__ == "__main__":
    main()
