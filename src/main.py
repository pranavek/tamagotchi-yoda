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

from . import config, events
from .display import Display
from .elements import ELEMENT_GLYPH
from .lifecycle import STAGE_SCALE
from .sprite import YodaSprite
from .state_machine import YodaState
from .weather import fetch_current


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
        # Icon column.
        draw.text((x0 + 1, y), icon, font=font, fill=0)
        # Bar.
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

    # Faint baseline under the status bar.
    draw.line((0, y + h, config.EPD_WIDTH, y + h), fill=0)


def _draw_bubble(canvas: Image.Image, text: str, font) -> None:
    draw = ImageDraw.Draw(canvas)
    x, y = config.BUBBLE_X, config.BUBBLE_Y
    w, h = config.BUBBLE_W, config.BUBBLE_H

    # Thought-trail dots first so the bubble outline draws over them cleanly.
    for cx, cy, r in config.BUBBLE_DOTS:
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=0, fill=255)

    if hasattr(draw, "rounded_rectangle"):
        draw.rounded_rectangle(
            (x, y, x + w, y + h), radius=8, outline=0, fill=255, width=1
        )
    else:
        draw.rectangle((x, y, x + w, y + h), outline=0, fill=255, width=1)

    draw.text(
        (x + config.BUBBLE_TEXT_X_PAD, y + config.BUBBLE_TEXT_Y_PAD),
        text,
        font=font,
        fill=0,
    )


def _draw_banner(canvas: Image.Image, state: YodaState, font) -> None:
    draw = ImageDraw.Draw(canvas)
    stage = state.data.get("stage", "egg")
    elem = state.dominant_element
    event_str = events.banner(state.data["event_state"].get("active", []))

    parts = [stage.upper(), elem.title()]
    if event_str:
        parts.append(event_str)
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
    yoda.blit_scaled(canvas, x, y, variant, scale)

    if state.data["observation_visible"] and state.data["observation_text"]:
        _draw_bubble(canvas, state.data["observation_text"], font)

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
        "boot tick=%d stage=%s dominant=%s",
        state.data["ticks"],
        state.data.get("stage"),
        state.dominant_element,
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

        state.tick(fetch_weather=fetch_current)
        img = render_frame(state, yoda, font)
        display.full_refresh(img)
        if state.data["full_refresh_due"]:
            state.data["full_refresh_due"] = False
            state.save()
        log.info(
            "tick=%d stage=%s stats=%s dominant=%s events=%s obs=%r",
            state.data["ticks"],
            state.data.get("stage"),
            {k: round(state.data["stats"][k], 1) for k in _STAT_KEYS},
            state.dominant_element,
            state.data["event_state"].get("active"),
            state.data.get("observation_text"),
        )
        display.sleep()


if __name__ == "__main__":
    main()
