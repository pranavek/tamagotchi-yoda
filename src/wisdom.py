"""Longer Yoda-style motivational sentences for the panel below the bubble.

Each entry is one full sentence (or a short pair), kept under ~44 characters
so it wraps cleanly to two ~22-char lines in the default Pillow bitmap font.
Selected fresh on every weather/market fetch.
"""

import random


WISDOM = [
    "Patience you must have, young one.",
    "Do or do not. There is no try.",
    "Fear is the path to dark side.",
    "Strong with the Force, you are.",
    "Train yourself to let go.",
    "Already know you that which you need.",
    "Luminous beings are we.",
    "Size matters not. Judge me by size?",
    "Always in motion is the future.",
    "Pass on what you have learned.",
    "Truly wonderful, the child's mind is.",
    "Named must your fear be.",
    "Listen to learn, you must.",
    "Wars not make one great.",
    "Much to learn you still have.",
    "Concentrate, feel the Force.",
    "A Jedi craves not these things.",
    "The greatest teacher, failure is.",
    "That is why you fail.",
    "Reckless he is. Matters not.",
    "Anger leads to suffering.",
    "Hmm. Patience. Patience.",
    "Save you, the Force can.",
    "Believe, and become you will.",
    "Quiet the mind. Listen, you must.",
]


def select_wisdom() -> str:
    return random.choice(WISDOM)
