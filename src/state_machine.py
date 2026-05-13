"""Persistent state for the ambient Yoda.

The state file is JSON. Writes go to a temp file in the same directory and
are renamed into place with ``os.replace`` so a power cut never leaves a
half-written ``state.json`` on disk.
"""

import json
import os
import random
from datetime import datetime
from typing import Any

from . import config
from .quotes import select_quote


DEFAULT_STATE: dict[str, Any] = {
    "ticks": 0,
    "last_tick": None,
    "quote_visible": False,
    "quote_text": None,
    "quote_remaining_ticks": 0,
    "sprite_variant": "idle",
    "full_refresh_due": True,
    "next_interval": config.MIN_TICK_INTERVAL,
}


class YodaState:
    def __init__(self, state_file: str) -> None:
        self.file = state_file
        self.data: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        try:
            with open(self.file, "r") as f:
                loaded = json.load(f)
            # Merge with defaults so older state files survive schema additions.
            merged = {**DEFAULT_STATE, **loaded}
            return merged
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return dict(DEFAULT_STATE)

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.file) or ".", exist_ok=True)
        tmp = f"{self.file}.tmp"
        with open(tmp, "w") as f:
            json.dump(self.data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.file)

    def tick(self) -> None:
        d = self.data
        d["ticks"] += 1
        d["last_tick"] = datetime.now().isoformat(timespec="seconds")

        if d["quote_visible"]:
            d["quote_remaining_ticks"] -= 1
            if d["quote_remaining_ticks"] <= 0:
                d["quote_visible"] = False
                d["quote_text"] = None
                d["sprite_variant"] = "idle"
        elif random.random() < config.QUOTE_CHANCE:
            d["quote_visible"] = True
            d["quote_text"] = select_quote()
            d["quote_remaining_ticks"] = config.QUOTE_DISPLAY_TICKS
            d["sprite_variant"] = "perked"
        else:
            d["sprite_variant"] = "blink" if random.random() < 0.2 else "idle"

        if d["ticks"] % config.FULL_REFRESH_EVERY_N_TICKS == 0:
            d["full_refresh_due"] = True

        d["next_interval"] = random.randint(
            config.MIN_TICK_INTERVAL, config.MAX_TICK_INTERVAL
        )
        self.save()
