"""Element x mood quote matrix.

Yoda speaks differently when the market is in panic vs euphoria. Each
(element, mood) cell holds three 3-word Yoda-style observations.

90 total entries: 6 elements × 5 moods × 3 phrasings.
"""

import random
from typing import Optional


OBSERVATIONS = {
    "fire": {
        "panic":    ["Burn too fast", "Ash falls soon", "Heat consumes all"],
        "fear":     ["Caution in flame", "Warmth still distant", "Embers hold hope"],
        "neutral":  ["Burn bright today", "Heat shapes all", "Flames dance wild"],
        "greed":    ["Fire grows higher", "Blaze without end", "Spark becomes inferno"],
        "euphoria": ["All burns gold", "Phoenix rises now", "Sun cannot set"],
    },
    "water": {
        "panic":    ["Tide retreats fast", "Riverbed cracks dry", "Depths turn shallow"],
        "fear":     ["Calm before storm", "Drink with care", "Currents shift cold"],
        "neutral":  ["Falling water, mmm", "Flow finds path", "Rivers carry truth"],
        "greed":    ["Floods bring more", "Rain never ends", "Ocean swells wide"],
        "euphoria": ["Mighty river sings", "Spring eternal flows", "Bless the deep"],
    },
    "ice": {
        "panic":    ["Cracks split deep", "Thaw arrives wrong", "Cold cannot hold"],
        "fear":     ["Bitter wind bites", "Freeze the hope", "Shiver in dark"],
        "neutral":  ["Cold it is", "Snow blankets all", "Stillness winter brings"],
        "greed":    ["Endless winter, mmm", "Frost grows strong", "Crystal palace rises"],
        "euphoria": ["Diamonds in snow", "Pure white forever", "Beautiful ice eternal"],
    },
    "air": {
        "panic":    ["Winds tear fierce", "Sky falls down", "Breath comes short"],
        "fear":     ["Whispers hide truth", "Gusts unsettle minds", "Storm draws near"],
        "neutral":  ["Soft skies today", "Patience the wind", "Calm it seems"],
        "greed":    ["Wind lifts higher", "Skies open wide", "Birds soar free"],
        "euphoria": ["Float on bliss", "Sky has no", "Soar, soar, soar"],
    },
    "storm": {
        "panic":    ["Doom approaches yes", "Lightning strikes home", "Cower we must"],
        "fear":     ["Hide we should", "Tremble the trees", "Thunder warns all"],
        "neutral":  ["Powerful the storm", "Rain whips wild", "Thunder cracks loud"],
        "greed":    ["Storm feeds power", "Lightning gives life", "Rage builds strong"],
        "euphoria": ["Ride the storm", "Power without limit", "Become the thunder"],
    },
    "shadow": {
        "panic":    ["Darkness swallows hope", "Lost in mist", "Cannot find way"],
        "fear":     ["Shadows whisper warnings", "See far cannot", "Hide hide hide"],
        "neutral":  ["Quiet the mist", "Patience in fog", "Listen close you"],
        "greed":    ["Shadows deepen yes", "Mystery grows thick", "Veil never lifts"],
        "euphoria": ["Embrace the dark", "Mystery is wisdom", "Shadow holds all"],
    },
}


def observe(element: str, mood: str = "neutral") -> Optional[str]:
    bank = OBSERVATIONS.get(element) or {}
    quotes = bank.get(mood) or bank.get("neutral") or []
    return random.choice(quotes) if quotes else None
