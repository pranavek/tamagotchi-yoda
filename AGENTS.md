# Tamagotchi-Yoda — Developer / Agent Guide

## Project overview

Weather-driven ambient virtual pet on Pi Zero 2 W + Waveshare 2.13" e-ink (V4, 250×122, 1-bit). Yoda is the visible character at every life stage. The Open-Meteo API drives his stats, elemental XP, life-stage progression, and weather-event banners.

## Tech stack

- **Language**: Python 3.7+
- **Graphics**: Pillow (1-bit `Image` + `ImageDraw`)
- **Weather**: Open-Meteo (`urllib.request` — no third-party HTTP dep)
- **Hardware**: vendored `waveshare_epd.epd2in13_V4` (`lib/`)
- **Deployment**: systemd (`tamagotchi-yoda.service`)

## Project structure

| File | Role |
|------|------|
| `src/main.py` | entry point, signal handlers, render-and-sleep loop, layout composition |
| `src/config.py` | every tunable in one place (location, cadences, decay rates, layout) |
| `src/display.py` | Waveshare wrapper with `MockEPD` import-time fallback |
| `src/sprite.py` | `YodaSprite` — idle / blink / perked / egg variants + scaled blit |
| `src/state_machine.py` | persistent JSON state, decay + feed + event orchestration |
| `src/weather.py` | Open-Meteo client; returns normalised dict or `None` on failure |
| `src/stats.py` | 0–100 stat decay, weather-feed, night-time energy regen |
| `src/elements.py` | WMO code → element, XP affinity graph, dominant-element lookup |
| `src/lifecycle.py` | age-since-hatch → stage; per-stage visual scale |
| `src/events.py` | streak-based event detection + stat/XP modifiers |
| `src/observations.py` | Yoda-style 3-word weather mutterings |
| `lib/waveshare_epd/` | vendored Waveshare V4 driver (do not modify) |

## Key invariants

- Canvas is **landscape 250×122**, even though the underlying driver is portrait 122×250. `Display.full_refresh()` rotates 180° when `ROTATE_180` is true.
- All rendering is 1-bit (`Image.new('1', ..., 255)`). Black = 0, white = 255.
- Sprite is composed once at class init and frozen into per-variant pixel sets. `blit()` is a putpixel walk. `blit_scaled()` renders to a temp image and resizes nearest-neighbour to keep 1-bit.
- State writes are atomic: write `*.tmp` in the same directory, then `os.replace`.
- The Waveshare driver is import-guarded — on a non-Pi dev box `MockEPD` takes over and frames dump to `last_display.png`.
- Weather fetch failures **never** crash the loop; the engine falls back to the last cached weather and the pet keeps decaying on baseline rates.
- Stats are floats; rendering rounds for display but state preserves precision.

## Cadence model

There are two interleaved cadences inside a single loop:

| Cadence | Period | Triggered by |
|---------|--------|--------------|
| Display tick | 15 min | every loop iteration |
| Weather fetch | ~60 min | every `WEATHER_FETCH_EVERY_N_TICKS` (default 4) ticks |

Display tick handles: pose drift, stat decay, energy night-regen, sprite-variant choice, life-stage refresh, full-refresh-throttling, and render. Weather fetch handles: Open-Meteo call, stat feed, XP update, event detection, observation pick.

## Life-cycle gating

`lifecycle.stage_for(hatched_at_iso)` returns one of `egg / baby / child / teen / adult / senior` from age-since-hatch. Durations are spec defaults (2h / 24h / 48h / 72h / 30d) divided by `DEVELOPMENT_SPEEDUP` for testing.

`STAGE_SCALE` maps each stage to a visual scale factor (`0.55` for baby, `1.0` for adult). Egg stage swaps in the egg sprite variant entirely.

## Hardware reference repo

[`/workspaces/git/eink_weather/`](../eink_weather/) is the sibling repo. Same panel, same driver, same systemd shape, same `image.rotate(180)` mounting convention.

## Development notes

- **Off-Pi run**: `python3 -m src.main` works against the real Open-Meteo API with a mock display.
- **Fast-forwarding age**: set `DEVELOPMENT_SPEEDUP = 60.0` in `config.py` to age an hour per minute.
- **Resetting**: delete `state.json` to re-hatch.
- **Forcing an event**: temporarily lower the streak thresholds in `events.update` or inject a fake `last_weather` dict (e.g. weathercode 95 to trigger Storm Surge).

## Service management

- File: `tamagotchi-yoda.service`
- Install: `sudo cp tamagotchi-yoda.service /etc/systemd/system/`
- Logs: `sudo journalctl -u tamagotchi-yoda.service -f`
- Restart: `sudo systemctl restart tamagotchi-yoda.service`

## Out of scope

- Manual feeding / petting / button controls (the weather is the caregiver, full stop)
- TTF fonts — `ImageFont.load_default()` keeps the dependency surface to Pillow alone
- Per-element custom sprites — the engine tracks dominant element internally; visual variety is expressed via the corner glyph and bottom banner
- Battery / TPL5111 single-shot mode
- Partial-refresh optimization
