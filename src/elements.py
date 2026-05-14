"""WMO weather code → element mapping + elemental XP affinity graph."""

from typing import Dict


ELEMENTS = ("fire", "water", "ice", "air", "storm", "shadow")


def code_to_element(weathercode: int) -> str:
    """Map a WMO weather code to the dominant element it represents."""
    c = int(weathercode)
    if c == 0:
        return "fire"
    if 1 <= c <= 3:
        return "air"
    if c in (45, 48):
        return "shadow"
    if 51 <= c <= 55:
        return "water"
    if 61 <= c <= 65:
        return "water"
    if 71 <= c <= 77:
        return "ice"
    if 80 <= c <= 82:
        return "water"
    if 85 <= c <= 86:
        return "ice"
    if 95 <= c <= 99:
        return "storm"
    return "air"  # unknown → balanced default


_COMPLEMENTARY = {
    "water": "ice",
    "ice": "water",
    "fire": "air",
    "air": "fire",
}

_OPPOSING = {
    "fire": "ice",
    "ice": "fire",
    "water": "air",
    "air": "water",
}


def apply_xp(current: Dict[str, int], weather_element: str) -> Dict[str, int]:
    """Return a new ELEMENTS dict with XP gains applied per the spec rules.

    - Matching element: +15
    - Complementary element: +5
    - Opposing element: -5 (clamped at 0)
    - Storm weather: +10 to ALL elements
    """
    out = dict(current)

    if weather_element == "storm":
        for k in out:
            out[k] += 10
        out["storm"] += 5  # matching bonus on top of the chaotic +10
        return out

    out[weather_element] = out.get(weather_element, 0) + 15

    comp = _COMPLEMENTARY.get(weather_element)
    if comp:
        out[comp] = out.get(comp, 0) + 5

    opp = _OPPOSING.get(weather_element)
    if opp:
        out[opp] = max(0, out.get(opp, 0) - 5)

    return out


def dominant(elements: Dict[str, int]) -> str:
    """The element with the highest XP. Ties broken by `ELEMENTS` declaration order."""
    if not elements or all(v == 0 for v in elements.values()):
        return "air"
    return max(ELEMENTS, key=lambda e: (elements.get(e, 0), -ELEMENTS.index(e)))


ELEMENT_GLYPH = {
    "fire": "F",
    "water": "W",
    "ice": "I",
    "air": "A",
    "storm": "S",
    "shadow": "H",
}
