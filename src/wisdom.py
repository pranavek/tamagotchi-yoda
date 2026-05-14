"""Generic 3-word Yoda phrases.

Pinned to line 3 of the zone under the speech bubble. Independent of weather
and market — these are always-true Yoda lore. Refreshed on every weather /
market fetch.
"""

import random


PHRASES = [
    "Do or not",
    "Fear leads dark",
    "Patience you must",
    "Luminous beings are",
    "Size matters not",
    "Pass on learned",
    "Control anger now",
    "In you must",
    "Your choice it",
    "Strong am I",
    "That is why",
    "Already know you",
    "Much to learn",
    "Control your anger",
    "Do or do",
    "The Force surrounds",
    "Try not, do",
    "Believe you must",
    "Trust your feelings",
    "Calm your mind",
    "Light the way",
    "Wise the path",
    "Mind, free it",
    "Quiet, the heart",
]


def select_phrase() -> str:
    return random.choice(PHRASES)
