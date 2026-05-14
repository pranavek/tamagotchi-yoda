"""Crypto Fear & Greed Index client (alternative.me).

Drop-in stand-in for CNN's stock F&G endpoint, which 418-blocks bots from
most datacenter networks. Same 0–100 scale, same mood semantics, no auth,
daily-updated. From a Yoda's perspective the market is the market.
"""

import json
import logging
import urllib.request
from typing import Optional

from . import config

log = logging.getLogger(__name__)


def fetch_current() -> Optional[dict]:
    try:
        with urllib.request.urlopen(
            config.MARKET_URL, timeout=config.MARKET_HTTP_TIMEOUT
        ) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        log.warning("market fetch failed: %s", e)
        return None

    data = (body.get("data") or [None])[0]
    if not data or "value" not in data:
        log.warning("market response missing data[0].value")
        return None

    try:
        score = int(data["value"])
    except (TypeError, ValueError):
        log.warning("market response value is not an int: %r", data.get("value"))
        return None

    return {
        "score": max(0, min(100, score)),
        "classification": data.get("value_classification") or "Neutral",
        "fetched_at_iso": data.get("timestamp"),
    }


def market_mood(score: int) -> str:
    """0-100 score → one of: panic / fear / neutral / greed / euphoria."""
    if score < 25:
        return "panic"
    if score < 45:
        return "fear"
    if score < 55:
        return "neutral"
    if score < 75:
        return "greed"
    return "euphoria"


MOODS = ("panic", "fear", "neutral", "greed", "euphoria")
