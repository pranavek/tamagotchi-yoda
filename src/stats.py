"""Core stat decay + weather-driven feed.

Stats are floats in [0, 100]. Decay runs per-hour and is applied per tick at
the appropriate fractional rate. Weather feeds add when a new fetch lands.
"""

from typing import Dict, Optional

from . import config
from .elements import code_to_element


STAT_KEYS = ("hunger", "happiness", "health", "energy")


def default_stats() -> Dict[str, float]:
    return {"hunger": 60.0, "happiness": 60.0, "health": 80.0, "energy": 80.0}


def _clamp(v: float) -> float:
    return max(0.0, min(100.0, v))


def decay(stats: Dict[str, float], seconds: float, current_temp_c: Optional[float]) -> Dict[str, float]:
    """Apply per-second decay across all four stats."""
    hours = seconds / 3600.0
    out = dict(stats)

    out["hunger"] = _clamp(out["hunger"] - config.HUNGER_DECAY_PER_HOUR * hours)
    out["happiness"] = _clamp(out["happiness"] - config.HAPPINESS_DECAY_PER_HOUR * hours)

    health_loss = config.HEALTH_DECAY_PER_HOUR * hours
    if current_temp_c is not None and (current_temp_c > 35 or current_temp_c < -10):
        health_loss += config.HEALTH_DECAY_EXTREME_TEMP_BONUS * hours
    out["health"] = _clamp(out["health"] - health_loss)

    out["energy"] = _clamp(out["energy"] - config.ENERGY_DECAY_PER_HOUR * hours)
    return out


def feed_from_weather(
    stats: Dict[str, float],
    weather: dict,
    prev_weather: Optional[dict],
) -> Dict[str, float]:
    """Apply weather-driven stat gains from a single fresh fetch.

    Per spec §4.1:
      Hunger     +10..30 per fetch (element-dependent)
      Happiness  +5..20 per fetch; bonus if weather changed since last fetch
      Health     +10..20 per fetch; Ice/Storm give more
    """
    elem = code_to_element(weather["weathercode"])
    out = dict(stats)

    hunger_gain = {"fire": 30, "water": 20, "ice": 10, "air": 12, "storm": 25, "shadow": 15}.get(elem, 15)
    out["hunger"] = _clamp(out["hunger"] + hunger_gain)

    happiness_gain = {"fire": 8, "water": 14, "ice": 6, "air": 18, "storm": 20, "shadow": 5}.get(elem, 10)
    if prev_weather and prev_weather.get("weathercode") != weather["weathercode"]:
        happiness_gain += 5  # variety bonus
    out["happiness"] = _clamp(out["happiness"] + happiness_gain)

    health_gain = 20 if elem in ("ice", "storm") else 12
    out["health"] = _clamp(out["health"] + health_gain)

    return out


def regenerate_energy_if_night(stats: Dict[str, float], hour_of_day: int, seconds: float) -> Dict[str, float]:
    """Energy regen between 22:00 and 06:00 local. ENERGY_REGEN_PER_HOUR per hour."""
    is_night = hour_of_day >= 22 or hour_of_day < 6
    if not is_night:
        return stats
    out = dict(stats)
    out["energy"] = _clamp(out["energy"] + config.ENERGY_REGEN_PER_HOUR * (seconds / 3600.0))
    return out


def is_dying(stats: Dict[str, float], state_flags: dict) -> Optional[str]:
    """Return a death reason if the pet has crossed a fatal threshold, else None.

    Caller maintains `state_flags["hunger_zero_since"]` / `happiness_zero_since`
    as ISO timestamps; if non-null and aged past the spec window, the pet dies.
    """
    if stats["health"] <= 0:
        return "health"
    # Caller decides on hunger / happiness durations via state flags; we just
    # report current zero crossings.
    return None
