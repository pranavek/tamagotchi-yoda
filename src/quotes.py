"""Yoda-style 3-word wisdom quotes."""

import random


QUOTES = [
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
    "A reflection of",
    "Much to learn",
    "Control your anger",
    "Pass on learned",
    "Luminous beings are",
    "Do or do",
    "The Force surrounds",
    "Size matters not",
]


def select_quote() -> str:
    return random.choice(QUOTES)
