"""Thin Open-Meteo client.

Returns a normalised current-weather dict or ``None`` on any failure.
Failures must never crash the main loop — the engine falls back on the last
cached weather and the pet continues to age on baseline decay.
"""

import logging
import urllib.parse
import urllib.request
from typing import Optional

from . import config

log = logging.getLogger(__name__)


def fetch_current() -> Optional[dict]:
    params = {
        "latitude": config.LATITUDE,
        "longitude": config.LONGITUDE,
        "current_weather": "true",
        "daily": "weathercode,temperature_2m_max,temperature_2m_min",
        "timezone": config.TIMEZONE,
    }
    url = f"{config.OPEN_METEO_URL}?{urllib.parse.urlencode(params)}"

    try:
        with urllib.request.urlopen(url, timeout=config.WEATHER_HTTP_TIMEOUT) as resp:
            import json

            body = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        log.warning("open-meteo fetch failed: %s", e)
        return None

    current = body.get("current_weather") or {}
    daily = body.get("daily") or {}

    if "weathercode" not in current:
        log.warning("open-meteo response missing current_weather.weathercode")
        return None

    return {
        "weathercode": int(current["weathercode"]),
        "temperature": float(current.get("temperature", 0.0)),
        "windspeed": float(current.get("windspeed", 0.0)),
        "is_day": int(current.get("is_day", 1)),
        "tmax": float((daily.get("temperature_2m_max") or [0.0])[0]),
        "tmin": float((daily.get("temperature_2m_min") or [0.0])[0]),
        "fetched_at_iso": current.get("time"),
    }
