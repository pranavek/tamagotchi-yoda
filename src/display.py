"""Waveshare 2.13" V4 e-ink wrapper.

Wraps the vendored Waveshare driver with a tiny surface area:

    Display().full_refresh(image)
    Display().sleep()
    Display().clear()

A ``MockEPD`` is substituted on import failure (e.g. running on a dev box
without ``RPi.GPIO`` / ``spidev`` / actual hardware), so the rest of the app
imports and renders without changes off-Pi.
"""

import importlib
import logging
import os
import sys

from PIL import Image

from . import config

logger = logging.getLogger(__name__)

# Ensure the vendored Waveshare driver is importable when running as
# ``python -m src.main`` from the repo root.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LIB_PATH = os.path.join(_REPO_ROOT, "lib")
if _LIB_PATH not in sys.path:
    sys.path.insert(0, _LIB_PATH)


class _MockEPD:
    """Stand-in for the Waveshare EPD class on non-Pi dev boxes."""

    width = config.EPD_HEIGHT
    height = config.EPD_WIDTH

    def init(self) -> None:
        pass

    def Clear(self, color: int) -> None:
        pass

    def display(self, buffer) -> None:
        pass

    def getbuffer(self, image):
        return image

    def sleep(self) -> None:
        pass


def _load_epd():
    try:
        module = importlib.import_module(config.EPD_DRIVER)
        epd = module.EPD()
        epd.init()
        return epd
    except Exception as e:
        logger.warning(
            "waveshare_epd driver unavailable (%s); using MockEPD.", e
        )
        return _MockEPD()


class Display:
    def __init__(self) -> None:
        self.epd = _load_epd()
        self.epd.Clear(0xFF)

    def full_refresh(self, image: Image.Image) -> None:
        out = image.rotate(180) if config.ROTATE_180 else image
        self.epd.display(self.epd.getbuffer(out))
        if config.DEBUG_DUMP_PNG:
            try:
                out.save(config.DEBUG_PNG_PATH)
            except OSError as e:
                logger.debug("debug PNG dump failed: %s", e)

    def sleep(self) -> None:
        self.epd.sleep()

    def clear(self) -> None:
        self.epd.Clear(0xFF)
