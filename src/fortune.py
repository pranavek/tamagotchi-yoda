"""Market-sentiment events — the mind side of Yoda's life.

Mirrors the shape of ``events.py`` for code reuse: ``default_state``,
``update``, ``one_shot_deltas``, ``banner``. Adds ``mood_modifiers`` for the
per-fetch happiness drift the spec attaches to the mood buckets themselves.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional

from . import config


FORTUNE_EVENTS = ("market_crash", "bull_run", "volatility_spike", "complacency")


def default_state() -> Dict:
    return {
        "recent_scores": [],          # list of [iso_ts, score], cap 12 entries
        "consecutive_complacent": 0,
        "active": [],
    }


def _max_min_swing_24h(history: List[List]) -> tuple[Optional[int], Optional[int]]:
    """Return (max, min) score over entries from the last 24 hours."""
    if not history:
        return None, None
    cutoff = datetime.now(timezone.utc).timestamp() - 24 * 3600
    recent = []
    for entry in history:
        ts_iso, score = entry[0], entry[1]
        try:
            ts = datetime.fromisoformat(ts_iso).timestamp()
        except (ValueError, TypeError):
            continue
        if ts >= cutoff:
            recent.append(score)
    if not recent:
        return None, None
    return max(recent), min(recent)


def update(state: Dict, score: int, prev_score: Optional[int], fetch_iso: str) -> Dict:
    out = dict(state)
    history = list(out.get("recent_scores") or [])
    history.append([fetch_iso, score])
    out["recent_scores"] = history[-12:]

    # Complacency streak.
    in_neutral_band = 45 <= score <= 55
    out["consecutive_complacent"] = (
        out.get("consecutive_complacent", 0) + 1 if in_neutral_band else 0
    )

    active: List[str] = []

    # Crash / Bull Run — either extreme score or large directional 24h swing.
    hi, lo = _max_min_swing_24h(out["recent_scores"])
    if score < 20:
        active.append("market_crash")
    elif hi is not None and lo is not None and (hi - lo) > 30 and score == lo:
        # we're sitting at the bottom of the 24h band after a >30 pt drop
        active.append("market_crash")

    if score > 80:
        active.append("bull_run")
    elif hi is not None and lo is not None and (hi - lo) > 30 and score == hi:
        active.append("bull_run")

    # Volatility — abs swing between this fetch and the previous one.
    if prev_score is not None and abs(score - prev_score) > 20:
        active.append("volatility_spike")

    # Complacency — only once we cross the threshold; stays active while streak holds.
    if out["consecutive_complacent"] >= config.COMPLACENCY_FETCH_THRESHOLD:
        active.append("complacency")

    out["active"] = active
    return out


# Per-fetch happiness drift attached directly to the mood bucket
# (spec §4 "Market Mood Effect on Happiness").
_MOOD_HAPPINESS = {
    "panic":    -15.0,
    "fear":     -5.0,
    "neutral":  0.0,
    "greed":    +10.0,
    "euphoria": +20.0,
}


def mood_modifiers(mood: str, prev_mood: Optional[str]) -> Dict[str, float]:
    """Return {stat: delta} applied on every successful market fetch.

    ``prev_mood`` is reserved for future "mood-changed" bonuses; currently the
    per-fetch drift is mood-only.
    """
    return {"happiness": _MOOD_HAPPINESS.get(mood, 0.0)}


def euphoria_hangover_due(mood: str) -> bool:
    """The spec gives euphoria a +20 happiness boost AND a -5 health hit
    on the NEXT tick (the "hangover"). Caller flips a flag in state."""
    return mood == "euphoria"


def one_shot_deltas(event: str) -> Dict[str, float]:
    if event == "market_crash":
        return {"happiness": -30.0}
    if event == "bull_run":
        return {"happiness": +30.0}
    if event == "volatility_spike":
        return {"energy": -20.0}
    if event == "complacency":
        # Complacency is "per-fetch -10 while active" — applied every fetch the
        # event is active, not just on arrival. Caller handles re-application.
        return {}
    return {}


def per_fetch_active_deltas(active: List[str]) -> Dict[str, float]:
    """Deltas applied every fetch the event is in `active` (not just on arrival)."""
    out: Dict[str, float] = {}
    if "complacency" in active:
        out["happiness"] = out.get("happiness", 0.0) - 10.0
    return out


# Priority order — first-matched event wins the banner slot.
_BANNER = {
    "market_crash":     "Crash!",
    "bull_run":         "Bull Run",
    "volatility_spike": "Volatile",
    "complacency":      "Yawn...",
}


def banner(active: List[str]) -> Optional[str]:
    for evt in ("market_crash", "bull_run", "volatility_spike", "complacency"):
        if evt in active:
            return _BANNER[evt]
    return None
