# tamagotchi-yoda

A weather-driven ambient virtual pet on a Raspberry Pi Zero 2 W + Waveshare 2.13" e-ink HAT (V4).

Yoda hatches once on first boot, ages from Egg → Baby → Child → Teen → Adult → Senior over a week of real time, and feeds on real-world weather pulled from the [Open-Meteo](https://open-meteo.com) forecast API. His mood, health, and elemental affinity are driven entirely by the weather above your latitude/longitude — no buttons, no inputs, no user-facing controls. The display refreshes every 15 minutes.

## How he lives

Every 15 minutes the device wakes:

- Pose drifts ±2 px (gentle sway)
- Stats decay (hunger, happiness, health, energy)
- About every fourth tick (~60 min) Yoda fetches fresh weather and:
  - **Stats feed** — hunger/happiness/health get topped up; the bonuses depend on which element the current weathercode maps to
  - **Elemental XP** — Fire / Water / Ice / Air / Storm / Shadow XP shifts (matching = +15, complementary = +5, opposing = −5, storms boost all six)
  - **Events fire** — Drought (clear >48h), Heat Wave (>30°C for >24h), Deep Freeze (snow >24h), Fogbound (fog >12h), Storm Surge (any thunderstorm tick), Seasonal Bloom (first rain after 7+ dry days)
  - **Observation** — Yoda mutters a 3-word weather remark in the speech bubble

Energy regenerates between 22:00 and 06:00 local. Health below zero is fatal.

## Display layout (250 × 122)

```
+----------------------------------------------------+
| H[##__] *[#___] +[####] Z[###_]            [Elem] | ← status bar
|                                                    |
|         (Yoda — sized by life stage)               |
|                                ___________         |
|                               | "Cold it" |        |
|                               | "is, mmm" |        |
|                                                    |
| ADULT  Fire  Heat Wave                             | ← life-stage / event banner
+----------------------------------------------------+
```

## Hardware

| Component | Spec |
|-----------|------|
| Host      | Raspberry Pi Zero 2 W (WiFi enabled — required for Open-Meteo) |
| Display   | Waveshare 2.13" e-Paper HAT V4 (250×122, 1-bit) |
| Interface | SPI0 + GPIO 23/24/25 |
| Power     | 5V via the GPIO header or USB-C |

## Setup (on the Pi)

```bash
sudo apt update
sudo apt install python3-pip python3-pil -y
sudo raspi-config           # → Interface Options → SPI → Enable
# Make sure WiFi is configured and the Pi can reach api.open-meteo.com.

sudo mkdir -p /root/tamagotchi-yoda
sudo cp -r . /root/tamagotchi-yoda/
cd /root/tamagotchi-yoda
sudo pip3 install -r requirements.txt

# Set your location:
sudo nano src/config.py     # edit LATITUDE / LONGITUDE / TIMEZONE

# Install as a systemd service:
sudo cp tamagotchi-yoda.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now tamagotchi-yoda.service
sudo journalctl -u tamagotchi-yoda.service -f
```

## Dev / off-Pi run

The Waveshare driver is import-guarded — if `spidev` / `RPi.GPIO` aren't available, a `MockEPD` substitutes and every rendered frame is dumped to `last_display.png`. Weather fetches go out over the real network from your dev box.

```bash
python3 -m src.main
open last_display.png
```

To watch a fast-forwarded life cycle without waiting a week, set `DEVELOPMENT_SPEEDUP` in `src/config.py` (e.g. `60.0` turns hours-of-aging into minutes-of-aging).

## Layout

```
src/
  main.py            entry, signal handlers, render-and-sleep loop
  config.py          all tunables (location, cadences, decay rates)
  display.py         Waveshare wrapper + MockEPD fallback
  sprite.py          45×55 Yoda (idle/blink/perked/egg) + scaled blit
  state_machine.py   persistent JSON state, decay/feed/event orchestration
  weather.py         Open-Meteo client (urllib only — no external deps)
  stats.py           Hunger / Happiness / Health / Energy decay + feed
  elements.py        WMO code → element + XP affinity graph
  lifecycle.py       Egg / Baby / Child / Teen / Adult / Senior age gating
  events.py          Drought / Heat Wave / Storm Surge / etc.
  observations.py    Yoda-style 3-word weather mutterings
lib/waveshare_epd/   vendored Waveshare V4 driver
tamagotchi-yoda.service systemd unit
```

State lives at `/root/tamagotchi-yoda/state.json` and survives reboots, so Yoda's age and XP accumulate across power cycles.

## Tuning

Edit `src/config.py`:

- `LATITUDE` / `LONGITUDE` / `TIMEZONE` — pin Yoda's weather to your location
- `WEATHER_FETCH_EVERY_N_TICKS` — how often to call Open-Meteo (default every 4 ticks ≈ 60 min)
- `QUOTE_CHANCE` — probability per weather fetch that Yoda speaks
- `HUNGER_DECAY_PER_HOUR` etc. — stat decay rates
- `DEVELOPMENT_SPEEDUP` — compress the life cycle for testing
- `POSE_DRIFT_MAX` — per-axis sway bound
- `ROTATE_180` — flip if the HAT is mounted the other way up
- `FULL_REFRESH_EVERY_N_TICKS` — anti-ghosting cadence

## Acceptance

- [x] Yoda silhouette visible at all life stages (scaled per stage)
- [x] Display refreshes every 15 min
- [x] Stats decay continuously; weather fetches replenish them
- [x] Six-element XP system; dominant element shown in the corner
- [x] Six weather-driven events implemented with stat / XP modifiers
- [x] State persists across reboots
- [x] No user input — no buttons, no web interface
