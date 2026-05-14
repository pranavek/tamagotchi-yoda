"""Yoda-style 3-word observations driven by current weather."""

import random
from typing import Optional


# Observations indexed by element. Each list is sampled by the engine.
OBSERVATIONS = {
    "fire": [
        "Hot it is",
        "Burning the sky",
        "Bright today, yes",
        "Drink water, you",
    ],
    "water": [
        "Falling water, mmm",
        "Wet is good",
        "Drink the rain",
        "Patience, the storm",
    ],
    "ice": [
        "Cold it is",
        "Wrap warm, you",
        "Snow blankets all",
        "Stillness, winter brings",
    ],
    "air": [
        "Soft skies today",
        "Patience the wind",
        "Calm it seems",
        "Listen, you must",
    ],
    "storm": [
        "Powerful, the storm",
        "Hide we should",
        "Lightning, fierce yes",
        "Tremble, the trees",
    ],
    "shadow": [
        "Quiet the mist",
        "See far, cannot",
        "Patience in fog",
        "Listen close, you",
    ],
}


def observe(element: str) -> Optional[str]:
    bank = OBSERVATIONS.get(element)
    if not bank:
        return None
    return random.choice(bank)
