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
    "sprite_variant": "idle",
    "full_refresh_due": True,
    "next_interval": config.MIN_TICK_INTERVAL,
    "pose_dx": 0,
    "pose_dy": 0,
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

        # Every tick rolls for a new quote. A successful roll replaces whatever
        # is currently shown; an unsuccessful roll leaves the existing quote
        # (if any) untouched — quotes only ever leave when a fresh one arrives.
        if random.random() < config.QUOTE_CHANCE:
            d["quote_visible"] = True
            d["quote_text"] = select_quote()
            d["sprite_variant"] = "perked"
        else:
            d["sprite_variant"] = "blink" if random.random() < 0.2 else "idle"

        # Subtle drift: ±1 px random walk on each axis, clamped to ±POSE_DRIFT_MAX.
        limit = config.POSE_DRIFT_MAX
        d["pose_dx"] = max(-limit, min(limit, d["pose_dx"] + random.choice([-1, 0, 1])))
        d["pose_dy"] = max(-limit, min(limit, d["pose_dy"] + random.choice([-1, 0, 1])))

        if d["ticks"] % config.FULL_REFRESH_EVERY_N_TICKS == 0:
            d["full_refresh_due"] = True

        d["next_interval"] = random.randint(
            config.MIN_TICK_INTERVAL, config.MAX_TICK_INTERVAL
        )
        self.save()
