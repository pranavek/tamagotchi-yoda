# Tamagotchi-Yoda — Developer / Agent Guide

## Project overview

Zero-interaction ambient virtual Yoda. Pi Zero 2 W drives a Waveshare 2.13" e-ink HAT (V4, 250×122, 1-bit) and renders a Yoda silhouette plus the occasional three-word wisdom quote. No inputs, no network.

## Tech stack

- **Language**: Python 3.7+
- **Graphics**: Pillow (1-bit `Image` + `ImageDraw`)
- **Hardware**: vendored `waveshare_epd.epd2in13_V4` (under `lib/`)
- **Deployment**: systemd (`tamagotchi-yoda.service`)

## Project structure

- `src/main.py` — entry point, signal handlers, render-and-sleep loop
- `src/config.py` — all constants (pin doc, timings, paths)
- `src/display.py` — Waveshare wrapper with `MockEPD` import-time fallback
- `src/sprite.py` — `YodaSprite` (45×55 silhouette, three variants composed via `ImageDraw` at init)
- `src/quotes.py` — 20-entry Yoda quote bank + `select_quote()`
- `src/state_machine.py` — `YodaState` with atomic JSON writes
- `lib/waveshare_epd/` — vendored Waveshare V4 driver (do not modify)

## Key invariants

- The canvas is **landscape 250×122**, even though the underlying driver is portrait 122×250. `Display.full_refresh()` handles the orientation via `image.rotate(180)` when `ROTATE_180` is true.
- All rendering is 1-bit (`Image.new('1', ..., 255)`). Black = 0, white = 255.
- The sprite is composed once at class init and frozen into per-variant pixel sets — `blit()` is just a putpixel walk.
- State writes are atomic (`os.replace` over a `*.tmp` file in the same directory) so a power cut never leaves a half-written `state.json`.
- The Waveshare driver is import-guarded — on a non-Pi dev box `MockEPD` takes over so the module imports cleanly and renders to `last_display.png` instead.

## Hardware reference repo

[`/workspaces/git/eink_weather/`](../eink_weather/) is the sibling repo this project mirrors:

- Same panel (Waveshare 2.13" V4) — driver was vendored verbatim from there
- Same systemd shape (`Type=simple`, `User=root`, journal output)
- Same `image.rotate(180)` mounting convention
- Same `Image.new('1', (250, 122), 255)` 1-bit landscape composition

When in doubt about hardware behavior, check eink_weather first.

## Development notes

- Off-Pi: `python3 -m src.main` runs the full loop with a mock driver and dumps every frame to `last_display.png`
- Sprite tweaking: open `src/sprite.py`, run the ASCII preview snippet in the README to see your changes
- State debugging: `state.json` is human-readable; delete it to reset Yoda to "day 0"

## Service management

- File: `tamagotchi-yoda.service`
- Install: `sudo cp tamagotchi-yoda.service /etc/systemd/system/`
- Logs: `sudo journalctl -u tamagotchi-yoda.service -f`
- Restart: `sudo systemctl restart tamagotchi-yoda.service`

## Out of scope

- Battery / TPL5111 single-shot power-cycling mode (the spec lists this as future work)
- Partial-refresh optimization — full-refresh-every-N-ticks is the safe default
- TTF fonts — `ImageFont.load_default()` keeps the dependency surface to Pillow alone
- Any kind of network, web UI, MQTT, or remote control — the project's whole point is to be inert and ambient
