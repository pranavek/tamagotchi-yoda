"""Persistent state for the weather-driven Tamagotchi-Yoda.

State file is JSON. Writes are atomic (``write tmp + os.replace``) so a
power-cut never leaves a half-written ``state.json`` on disk.

Each ``tick()`` advances time by ``next_interval`` seconds (the time we just
slept): pose drifts, stats decay, energy regenerates at night, and on every
N-th tick we fetch fresh weather, recompute elemental XP, apply event
modifiers, and pick a new observation for Yoda to mutter.
"""

import json
import logging
import os
import random
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from . import config, events, fortune, stats
from .elements import apply_xp, code_to_element, dominant
from .lifecycle import stage_for
from .market import market_mood
from .observations import observe


log = logging.getLogger(__name__)


DEFAULT_STATE: dict[str, Any] = {
    "ticks": 0,
    "last_tick": None,
    "sprite_variant": "idle",
    "full_refresh_due": True,
    "next_interval": config.MIN_TICK_INTERVAL,
    "pose_dx": 0,
    "pose_dy": 0,

    "hatched_at": None,
    "stage": "egg",

    "stats": None,            # populated by stats.default_stats() on first load
    "elements": {"fire": 0, "water": 0, "ice": 0, "air": 0, "storm": 0, "shadow": 0},

    "last_weather": None,
    "last_weather_at": None,
    "ticks_since_fetch": 0,

    "event_state": None,      # populated by events.default_event_state() on first load
    "observation_visible": False,
    "observation_text": None,

    "last_market": None,
    "last_market_at": None,
    "ticks_since_market_fetch": 0,
    "market_mood": "neutral",
    "prev_market_mood": "neutral",
    "fortune_state": None,    # populated by fortune.default_state() on first load
    "euphoria_hangover_due": False,

    "dead": False,
    "death_reason": None,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _now_local_hour() -> int:
    return datetime.now().hour


class YodaState:
    def __init__(self, state_file: str) -> None:
        self.file = state_file
        self.data: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        try:
            with open(self.file, "r") as f:
                loaded = json.load(f)
            merged = {**DEFAULT_STATE, **loaded}
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            merged = dict(DEFAULT_STATE)

        # First-boot bootstrap (only on a genuinely-fresh state).
        if not merged.get("hatched_at"):
            merged["hatched_at"] = _now_iso()
        if merged.get("stats") is None:
            merged["stats"] = stats.default_stats()
        if merged.get("event_state") is None:
            merged["event_state"] = events.default_event_state()
        if merged.get("fortune_state") is None:
            merged["fortune_state"] = fortune.default_state()
        # Defensive: ensure all 6 element keys are present even on older state files.
        for k in ("fire", "water", "ice", "air", "storm", "shadow"):
            merged["elements"].setdefault(k, 0)
        return merged

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.file) or ".", exist_ok=True)
        tmp = f"{self.file}.tmp"
        with open(tmp, "w") as f:
            json.dump(self.data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.file)

    # ------------------------------------------------------------------ tick

    def tick(
        self,
        fetch_weather: Optional[Callable[[], Optional[dict]]] = None,
        fetch_market: Optional[Callable[[], Optional[dict]]] = None,
    ) -> None:
        """Advance state by one wake cycle.

        ``fetch_weather`` and ``fetch_market`` are injected so tests can mock
        the network. When ``None``, the corresponding refresh is skipped.
        """
        d = self.data
        d["ticks"] += 1
        d["ticks_since_fetch"] += 1
        d["ticks_since_market_fetch"] += 1
        d["last_tick"] = _now_iso()

        elapsed_s = float(d.get("next_interval") or config.MIN_TICK_INTERVAL)

        # Euphoria hangover: spec says health -5 *next tick* after a euphoria fetch.
        if d.get("euphoria_hangover_due"):
            d["stats"]["health"] = max(0.0, d["stats"]["health"] - config.EUPHORIA_HANGOVER_HEALTH_LOSS)
            d["euphoria_hangover_due"] = False

        # Pose drift.
        limit = config.POSE_DRIFT_MAX
        d["pose_dx"] = max(-limit, min(limit, d["pose_dx"] + random.choice([-1, 0, 1])))
        d["pose_dy"] = max(-limit, min(limit, d["pose_dy"] + random.choice([-1, 0, 1])))

        # Stat decay (gated on the live weather we already have).
        temp = (d["last_weather"] or {}).get("temperature")
        d["stats"] = stats.decay(d["stats"], elapsed_s, temp)
        d["stats"] = stats.regenerate_energy_if_night(d["stats"], _now_local_hour(), elapsed_s)

        # Event-derived stat decay multipliers tweak baseline rates.
        active = d["event_state"].get("active", [])
        mods = events.stat_modifiers(active)
        if mods["hunger_decay_mult"] != 1.0:
            extra = (config.HUNGER_DECAY_PER_HOUR * (mods["hunger_decay_mult"] - 1.0)) * (elapsed_s / 3600.0)
            d["stats"]["hunger"] = max(0.0, d["stats"]["hunger"] - extra)
        if mods["health_decay_mult"] != 1.0:
            extra = (config.HEALTH_DECAY_PER_HOUR * (mods["health_decay_mult"] - 1.0)) * (elapsed_s / 3600.0)
            d["stats"]["health"] = max(0.0, d["stats"]["health"] - extra)

        # Optional weather refresh.
        if (
            fetch_weather is not None
            and d["ticks_since_fetch"] >= config.WEATHER_FETCH_EVERY_N_TICKS
        ):
            self._refresh_weather(fetch_weather)

        # Optional market refresh.
        if (
            fetch_market is not None
            and d["ticks_since_market_fetch"] >= config.MARKET_FETCH_EVERY_N_TICKS
        ):
            self._refresh_market(fetch_market)

        # Sprite variant: blink occasionally, perked if a fresh observation arrived this tick.
        if d.get("_just_observed"):
            d["sprite_variant"] = "perked"
            d["_just_observed"] = False
        elif random.random() < 0.2:
            d["sprite_variant"] = "blink"
        else:
            d["sprite_variant"] = "idle"

        # Life-stage refresh.
        d["stage"] = stage_for(d["hatched_at"])

        # Death check (only one we can decide synchronously: health <= 0).
        if not d["dead"] and d["stats"]["health"] <= 0:
            d["dead"] = True
            d["death_reason"] = "health"

        if d["ticks"] % config.FULL_REFRESH_EVERY_N_TICKS == 0:
            d["full_refresh_due"] = True

        d["next_interval"] = random.randint(config.MIN_TICK_INTERVAL, config.MAX_TICK_INTERVAL)
        self.save()

    # ------------------------------------------------------------- boot helper

    def boot_refresh(
        self,
        fetch_weather: Optional[Callable[[], Optional[dict]]] = None,
        fetch_market: Optional[Callable[[], Optional[dict]]] = None,
    ) -> None:
        """Populate weather + market on startup before the first render.

        Called once by ``main()`` before entering the tick loop. If either
        fetch fails the engine falls back to the last cached value (which on
        a fresh state file is ``None`` and just means the pet boots blind for
        another cycle).
        """
        if fetch_weather is not None:
            self._refresh_weather(fetch_weather)
        if fetch_market is not None:
            self._refresh_market(fetch_market)
        self.save()

    # --------------------------------------------------------------- weather

    def _seconds_since(self, last_at_iso: Optional[str]) -> float:
        if not last_at_iso:
            return 0.0
        try:
            last_at = datetime.fromisoformat(last_at_iso)
        except ValueError:
            return 0.0
        if last_at.tzinfo is None:
            last_at = last_at.replace(tzinfo=timezone.utc)
        return max(0.0, (datetime.now(timezone.utc) - last_at).total_seconds())

    def _refresh_weather(self, fetch_weather: Callable[[], Optional[dict]]) -> None:
        d = self.data
        prev = d["last_weather"]
        prev_at = d.get("last_weather_at")
        weather = fetch_weather()
        d["ticks_since_fetch"] = 0
        if weather is None:
            log.info("weather fetch failed; keeping last cached weather")
            return

        d["last_weather"] = weather
        d["last_weather_at"] = _now_iso()

        # Feed stats from the fresh weather.
        d["stats"] = stats.feed_from_weather(d["stats"], weather, prev)

        # Update elemental XP.
        weather_element = code_to_element(weather["weathercode"])
        d["elements"] = apply_xp(d["elements"], weather_element)

        # Advance event streaks by the real-world seconds since the previous
        # fetch (or 0 on the very first boot, when there is no prior fetch).
        seconds_since_prev_fetch = self._seconds_since(prev_at)
        previously_active = set(d["event_state"].get("active", []))
        d["event_state"] = events.update(d["event_state"], weather, seconds_since_prev_fetch)
        newly_active = set(d["event_state"].get("active", [])) - previously_active

        for evt in newly_active:
            deltas = events.one_shot_deltas(evt)
            for k, v in deltas.items():
                d["stats"][k] = min(100.0, d["stats"][k] + v)

        if newly_active:
            d["elements"] = events.xp_event_bonus(d["elements"], list(newly_active))

        # Maybe pick an observation for Yoda to mutter, keyed by element and mood.
        if random.random() < config.QUOTE_CHANCE:
            text = observe(weather_element, d.get("market_mood", "neutral"))
            if text:
                d["observation_visible"] = True
                d["observation_text"] = text
                d["_just_observed"] = True

    # --------------------------------------------------------------- market

    def _refresh_market(self, fetch_market: Callable[[], Optional[dict]]) -> None:
        d = self.data
        prev_score = (d["last_market"] or {}).get("score")
        market = fetch_market()
        d["ticks_since_market_fetch"] = 0
        if market is None:
            log.info("market fetch failed; keeping last cached score")
            return

        d["last_market"] = market
        d["last_market_at"] = _now_iso()

        new_mood = market_mood(market["score"])
        d["prev_market_mood"] = d.get("market_mood", "neutral")
        d["market_mood"] = new_mood

        # Per-fetch happiness drift from the mood bucket itself.
        drift = fortune.mood_modifiers(new_mood, d["prev_market_mood"])
        for k, v in drift.items():
            d["stats"][k] = max(0.0, min(100.0, d["stats"][k] + v))

        # Euphoria leaves a hangover that hits health on the next tick.
        if fortune.euphoria_hangover_due(new_mood):
            d["euphoria_hangover_due"] = True

        # Fortune-event detection on the new score.
        previously_active = set(d["fortune_state"].get("active", []))
        d["fortune_state"] = fortune.update(
            d["fortune_state"], market["score"], prev_score, market.get("fetched_at_iso") or _now_iso()
        )
        newly_active = set(d["fortune_state"].get("active", [])) - previously_active

        for evt in newly_active:
            deltas = fortune.one_shot_deltas(evt)
            for k, v in deltas.items():
                d["stats"][k] = max(0.0, min(100.0, d["stats"][k] + v))

        # Per-fetch active deltas (e.g. complacency keeps draining happiness).
        for k, v in fortune.per_fetch_active_deltas(d["fortune_state"].get("active", [])).items():
            d["stats"][k] = max(0.0, min(100.0, d["stats"][k] + v))

        # If we don't already have a fresh observation from this tick, the
        # market shift gets its own shot at producing one — keyed by current
        # weather element + the new mood.
        if not d.get("_just_observed") and random.random() < config.QUOTE_CHANCE:
            elem = code_to_element((d["last_weather"] or {}).get("weathercode", 1))
            text = observe(elem, new_mood)
            if text:
                d["observation_visible"] = True
                d["observation_text"] = text
                d["_just_observed"] = True

    # -------------------------------------------------------- conveniences

    @property
    def dominant_element(self) -> str:
        return dominant(self.data["elements"])
