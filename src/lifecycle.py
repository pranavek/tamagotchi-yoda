"""Life-cycle stage based on age since hatching.

Per spec §4.3:
    Egg    : first 2h after first boot
    Baby   : next 24h
    Child  : next 48h
    Teen   : next 72h
    Adult  : permanent
    Senior : random chance after 30d as Adult (we approximate with a clean
             threshold rather than randomness so the visual is predictable)
"""

from datetime import datetime, timezone
from typing import Optional

from . import config


STAGES = ("egg", "baby", "child", "teen", "adult", "senior")


def _stage_thresholds_seconds() -> list[tuple[str, float]]:
    """Cumulative thresholds in seconds, scaled by DEVELOPMENT_SPEEDUP for testing."""
    speedup = max(1.0, float(config.DEVELOPMENT_SPEEDUP))
    h = 3600.0 / speedup
    return [
        ("egg", 2 * h),
        ("baby", 2 * h + 24 * h),
        ("child", 2 * h + 24 * h + 48 * h),
        ("teen", 2 * h + 24 * h + 48 * h + 72 * h),
        ("adult", 2 * h + 24 * h + 48 * h + 72 * h + 30 * 24 * h),
        # past that, senior
    ]


def stage_for(hatched_at_iso: Optional[str], now: Optional[datetime] = None) -> str:
    if not hatched_at_iso:
        return "egg"
    try:
        hatched = datetime.fromisoformat(hatched_at_iso)
    except ValueError:
        return "egg"
    if hatched.tzinfo is None:
        hatched = hatched.replace(tzinfo=timezone.utc)
    now = (now or datetime.now(timezone.utc))
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    seconds_alive = (now - hatched).total_seconds()

    for stage, threshold in _stage_thresholds_seconds():
        if seconds_alive < threshold:
            return stage
    return "senior"


# Visual scale per stage — multiplier on the 45×55 base sprite.
STAGE_SCALE = {
    "egg": 1.0,        # egg sprite has its own geometry
    "baby": 0.55,
    "child": 0.70,
    "teen": 0.85,
    "adult": 1.0,
    "senior": 1.0,
}
