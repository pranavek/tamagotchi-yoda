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

from . import config
from .display import Display
from .sprite import YodaSprite
from .state_machine import YodaState


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("yoda")


def _draw_bubble(canvas: Image.Image, text: str, font) -> None:
    draw = ImageDraw.Draw(canvas)
    x, y = config.BUBBLE_X, config.BUBBLE_Y
    w, h = config.BUBBLE_W, config.BUBBLE_H
    radius = 8

    # Bubble body — rounded white rectangle with a black outline.
    if hasattr(draw, "rounded_rectangle"):
        draw.rounded_rectangle(
            (x, y, x + w, y + h), radius=radius, outline=0, fill=255, width=1
        )
    else:
        draw.rectangle((x, y, x + w, y + h), outline=0, fill=255, width=1)

    # Tail — small triangle pointing down toward Yoda's head.
    tx, ty = config.BUBBLE_TAIL_TARGET
    tail_anchor_x = x + 12
    tail_anchor_y = y + h
    draw.polygon(
        [
            (tail_anchor_x, tail_anchor_y - 1),
            (tail_anchor_x + 8, tail_anchor_y - 1),
            (tx, ty),
        ],
        fill=255,
        outline=0,
    )

    draw.text(
        (x + config.BUBBLE_TEXT_X_PAD, y + config.BUBBLE_TEXT_Y_PAD),
        text,
        font=font,
        fill=0,
    )


def render_frame(state: YodaState, yoda: YodaSprite, font) -> Image.Image:
    canvas = Image.new("1", (config.EPD_WIDTH, config.EPD_HEIGHT), 255)
    yoda.blit(canvas, config.YODA_X, config.YODA_Y, state.data["sprite_variant"])
    if state.data["quote_visible"] and state.data["quote_text"]:
        _draw_bubble(canvas, state.data["quote_text"], font)
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

    log.info("boot tick=%d quote_visible=%s", state.data["ticks"], state.data["quote_visible"])

    # First frame on boot — always full-refresh, then sleep.
    img = render_frame(state, yoda, font)
    display.full_refresh(img)
    state.data["full_refresh_due"] = False
    state.save()
    display.sleep()

    while True:
        interval = max(1, int(state.data["next_interval"]))
        log.info("sleeping %d s until next tick", interval)
        time.sleep(interval)

        state.tick()
        img = render_frame(state, yoda, font)
        display.full_refresh(img)
        if state.data["full_refresh_due"]:
            state.data["full_refresh_due"] = False
            state.save()
        log.info(
            "tick=%d variant=%s quote=%s",
            state.data["ticks"],
            state.data["sprite_variant"],
            state.data["quote_text"],
        )
        display.sleep()


if __name__ == "__main__":
    main()
