"""Weather-driven events.

The engine maintains a small set of running "streak" counters that increment
on each weather fetch when the matching condition holds, and reset otherwise.
Event firing is decided from those streaks plus the live weathercode.

State shape (managed by the caller as ``event_state``):

    {
      "clear_streak_h":   float,   # consecutive hours of clear sky
      "snow_streak_h":    float,
      "fog_streak_h":     float,
      "hot_streak_h":     float,   # consecutive hours with temp > 30C
      "dry_streak_h":     float,   # consecutive hours without rain/snow
      "active":           list[str],
      "last_seen_codes":  list[int],  # recent codes (bounded)
    }
"""

from typing import Dict, List, Optional

from .elements import code_to_element


_RAIN_CODES = set(range(51, 56)) | set(range(61, 66)) | set(range(80, 83))
_SNOW_CODES = set(range(71, 78)) | set(range(85, 87))
_CLEAR_CODES = {0}
_FOG_CODES = {45, 48}
_STORM_CODES = set(range(95, 100))


def default_event_state() -> Dict:
    return {
        "clear_streak_h": 0.0,
        "snow_streak_h": 0.0,
        "fog_streak_h": 0.0,
        "hot_streak_h": 0.0,
        "dry_streak_h": 0.0,
        "active": [],
        "last_seen_codes": [],
        "bloom_armed": False,  # set True once dry_streak passes 7d
    }


def update(
    state: Dict,
    weather: dict,
    seconds_since_last: float,
) -> Dict:
    """Advance streak counters by the elapsed real-world hours.

    Returns the new state. ``state["active"]`` lists the events firing *right now*.
    """
    hours = seconds_since_last / 3600.0
    code = int(weather["weathercode"])
    temp = float(weather.get("temperature", 0.0))
    out = dict(state)

    def _bump(key: str, hit: bool) -> None:
        out[key] = (out.get(key, 0.0) + hours) if hit else 0.0

    is_clear = code in _CLEAR_CODES
    is_snow = code in _SNOW_CODES
    is_fog = code in _FOG_CODES
    is_hot = temp > 30
    is_wet = code in _RAIN_CODES or code in _SNOW_CODES or code in _STORM_CODES

    _bump("clear_streak_h", is_clear)
    _bump("snow_streak_h", is_snow)
    _bump("fog_streak_h", is_fog)
    _bump("hot_streak_h", is_hot)
    _bump("dry_streak_h", not is_wet)

    if out["dry_streak_h"] >= 7 * 24:
        out["bloom_armed"] = True

    active: List[str] = []

    if code in _STORM_CODES:
        active.append("storm_surge")
    if out["clear_streak_h"] > 48:
        active.append("drought")
    if out["snow_streak_h"] > 24:
        active.append("deep_freeze")
    if out["hot_streak_h"] > 24:
        active.append("heat_wave")
    if out["fog_streak_h"] > 12:
        active.append("fogbound")
    if out.get("bloom_armed") and code in _RAIN_CODES:
        active.append("seasonal_bloom")
        out["bloom_armed"] = False  # one-shot

    out["active"] = active

    last = list(out.get("last_seen_codes", []))
    last.append(code)
    out["last_seen_codes"] = last[-24:]

    return out


def stat_modifiers(active_events: List[str]) -> Dict[str, float]:
    """Return per-tick multiplicative modifiers from the active events.

    Keys map to:
      hunger_decay_mult  (>1 means hunger decays faster)
      health_decay_mult
      energy_regen_mult
    """
    mods = {"hunger_decay_mult": 1.0, "health_decay_mult": 1.0, "energy_regen_mult": 1.0}
    if "drought" in active_events:
        mods["hunger_decay_mult"] *= 2.0
    if "heat_wave" in active_events:
        mods["health_decay_mult"] *= 2.0
    if "deep_freeze" in active_events:
        mods["energy_regen_mult"] *= 0.5
    return mods


# Bonus to elemental XP on a fresh weather fetch under specific events.
def xp_event_bonus(elements: Dict[str, int], active_events: List[str]) -> Dict[str, int]:
    out = dict(elements)
    if "deep_freeze" in active_events:
        out["ice"] = int(out.get("ice", 0) * 1.5)
    if "heat_wave" in active_events:
        out["fire"] = int(out.get("fire", 0) * 1.5)
    if "fogbound" in active_events:
        out["shadow"] = out.get("shadow", 0) * 2
    return out


# One-shot stat deltas on event arrival (caller fires once per event onset).
def one_shot_deltas(event: str) -> Dict[str, float]:
    if event == "storm_surge":
        return {"hunger": 20, "happiness": 20, "health": 10, "energy": 20}
    if event == "seasonal_bloom":
        return {"happiness": 50}
    return {}


EVENT_BANNER = {
    "storm_surge": "Storm Surge",
    "drought": "Drought!",
    "deep_freeze": "Deep Freeze",
    "heat_wave": "Heat Wave",
    "fogbound": "Fogbound",
    "seasonal_bloom": "Bloom!",
}


def banner(active_events: List[str]) -> Optional[str]:
    """Return the first event banner string to display, or None."""
    for evt in ("storm_surge", "seasonal_bloom", "heat_wave", "drought", "deep_freeze", "fogbound"):
        if evt in active_events:
            return EVENT_BANNER[evt]
    return None
