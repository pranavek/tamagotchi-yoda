# tamagotchi-yoda

A weather- and market-driven ambient virtual pet on a Raspberry Pi Zero 2 W + Waveshare 2.13" e-ink HAT (V4).

Yoda hatches once on first boot, ages from Egg → Baby → Child → Teen → Adult → Senior over a week of real time, and lives on two real-world entropy sources:

- **Weather** (cyclical, seasonal) pulled hourly from [Open-Meteo](https://open-meteo.com) — feeds the body: hunger, health, elemental XP.
- **Market sentiment** (chaotic, emotional) pulled every ~4 h from the [Crypto Fear & Greed Index](https://alternative.me/crypto/fear-and-greed-index/) — feeds the mind: happiness, stress, the tone of his quotes, the aura around his silhouette.

No buttons, no inputs, no user-facing controls. The display refreshes every ~10 minutes; the data fetches happen on boot and then on their own cadence.

## How he lives

**On boot** Yoda fetches weather and market immediately so the first rendered frame already reflects reality. After that:

Every ~10 minutes the device wakes:

- Pose drifts ±2 px (gentle sway)
- Stats decay (hunger, happiness, health, energy)
- Every 6 ticks (~60 min) Yoda fetches fresh **weather** and:
  - **Stats feed** — hunger/happiness/health get topped up; the bonuses depend on which element the current weathercode maps to
  - **Elemental XP** — Fire / Water / Ice / Air / Storm / Shadow XP shifts (matching = +15, complementary = +5, opposing = −5, storms boost all six)
  - **Weather events fire** — Drought (clear >48h), Heat Wave (>30°C for >24h), Deep Freeze (snow >24h), Fogbound (fog >12h), Storm Surge (any thunderstorm tick), Seasonal Bloom (first rain after 7+ dry days)
- Every 24 ticks (~4 h) Yoda fetches the **Crypto Fear & Greed Index** and:
  - **Market mood** — score 0–100 buckets into panic / fear / neutral / greed / euphoria
  - **Mind feed** — happiness drifts by the mood bucket (panic −15, fear −5, neutral 0, greed +10, euphoria +20); euphoria leaves a −5 health hangover on the next tick
  - **Fortune events fire** — Market Crash (score <20 or 24 h drop >30 pts), Bull Run (score >80 or 24 h rise >30 pts), Volatility Spike (>20 pt swing between fetches), Complacency (5+ consecutive neutral fetches)
  - **Aura overlay** — non-neutral moods paint a procedural aura around Yoda's silhouette
- **Observation** — on every successful fetch Yoda mutters a fresh 3-word remark picked from the (element × mood) quote matrix; the bubble stays up between fetches

Energy regenerates between 22:00 and 06:00 local. Health below zero is fatal.

## Display layout (250 × 122)

```
+----------------------------------------------------+
| H[##__] *[#___] +[####] Z[###_]            [Elem] | ← status bar
|                                                    |
|         (Yoda — sized by life stage + mood aura)   |
|                                ___________         |
|                               | "Cold it" |        |
|                               | "is, mmm" |        |
|                                                    |
| ADULT  Fire  Heat Wave  Crash!                     | ← life-stage / weather event / fortune event
+----------------------------------------------------+
```

Mood auras (drawn around Yoda based on market mood):

| Mood     | Aura visual |
|----------|-------------|
| panic    | jagged 1-px static scattered just outside the silhouette |
| fear     | single downward droplet pixel above the head |
| neutral  | nothing |
| greed    | upward floating dots above the head |
| euphoria | 8 radiating lines from sprite centre |

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
  main.py            entry, signal handlers, render-and-sleep loop, layout
  config.py          all tunables (location, cadences, decay rates, URLs)
  display.py         Waveshare wrapper + MockEPD fallback
  sprite.py          45×55 Yoda (idle/blink/perked/egg) + scaled blit
  state_machine.py   persistent JSON state, boot fetch, tick orchestration
  weather.py         Open-Meteo client (urllib only — no external deps)
  market.py          Crypto Fear & Greed Index client + mood bucketing
  stats.py           Hunger / Happiness / Health / Energy decay + feed
  elements.py        WMO code → element + XP affinity graph
  lifecycle.py       Egg / Baby / Child / Teen / Adult / Senior age gating
  events.py          Weather events: Drought / Heat Wave / Storm Surge / etc.
  fortune.py         Market events: Crash / Bull Run / Volatility / Complacency
  observations.py    (element × mood) → 3-word Yoda-style remark matrix
lib/waveshare_epd/   vendored Waveshare V4 driver
tamagotchi-yoda.service systemd unit
```

State lives at `/root/tamagotchi-yoda/state.json` and survives reboots, so Yoda's age and XP accumulate across power cycles.

## Tuning

Edit `src/config.py`:

- `LATITUDE` / `LONGITUDE` / `TIMEZONE` — pin Yoda's weather to your location
- `WEATHER_FETCH_EVERY_N_TICKS` — how often to call Open-Meteo (default 6 ≈ 60 min)
- `MARKET_FETCH_EVERY_N_TICKS` — how often to call alternative.me (default 24 ≈ 4 h)
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
