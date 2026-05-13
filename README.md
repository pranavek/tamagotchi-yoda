# tamagotchi-yoda

A zero-interaction ambient Yoda for the Raspberry Pi Zero 2 W + Waveshare 2.13" e-ink HAT (V4).

Wakes every 10–45 minutes, renders a 1-bit Yoda sprite on the 250×122 panel, occasionally surfaces a three-word Yoda-style quote in a speech bubble, then puts the e-ink controller back to sleep. No buttons, no inputs, no network.

## Hardware

| Component | Spec |
|-----------|------|
| Host      | Raspberry Pi Zero 2 W |
| Display   | Waveshare 2.13" e-Paper HAT V4 (250×122, 1-bit) |
| Interface | SPI0 + GPIO 23/24/25 |
| Power     | 5V via the GPIO header or USB-C |

The Pi Zero 2 W cannot truly suspend; the script runs as a long-lived process with the e-ink controller sleeping between updates.

## Setup (on the Pi)

```bash
sudo apt update
sudo apt install python3-pip python3-pil -y

# Enable SPI:
sudo raspi-config           # → Interface Options → SPI → Enable

sudo mkdir -p /root/tamagotchi-yoda
sudo cp -r . /root/tamagotchi-yoda/
cd /root/tamagotchi-yoda
sudo pip3 install -r requirements.txt

# Install as a systemd service:
sudo cp tamagotchi-yoda.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now tamagotchi-yoda.service

# Watch the logs:
sudo journalctl -u tamagotchi-yoda.service -f
```

## Dev / off-Pi run

The Waveshare driver is import-guarded; if `spidev` / `RPi.GPIO` aren't available, a `MockEPD` stands in and every rendered frame is dumped to `./last_display.png`.

```bash
python3 -m src.main             # renders one frame, sleeps, repeats
open last_display.png            # see what would have gone to the panel
```

To eyeball just the sprite:

```bash
python3 - <<'PY'
from PIL import Image
from src.sprite import YodaSprite
s = YodaSprite()
img = Image.new('1', (250, 122), 255)
s.blit(img, 20, 40, 'idle')
img.save('/tmp/yoda.png')
PY
```

## Layout

```
src/                    application code
  main.py               entry point + signal handlers + main loop
  config.py             constants (pin map, timings, paths)
  display.py            Waveshare wrapper + MockEPD fallback
  sprite.py             45×55 Yoda silhouette, three variants
  quotes.py             3-word Yoda-style quote bank
  state_machine.py      JSON-persisted state with atomic writes
lib/waveshare_epd/      vendored Waveshare V4 driver
tamagotchi-yoda.service systemd unit
```

State lives at `/root/tamagotchi-yoda/state.json` and survives reboots.

## Tuning

Edit `src/config.py`:

- `MIN_TICK_INTERVAL` / `MAX_TICK_INTERVAL` — how often Yoda wakes
- `QUOTE_CHANCE` — probability per tick of surfacing a new quote
- `QUOTE_DISPLAY_TICKS` — how many wake cycles a quote lingers
- `ROTATE_180` — flip if the HAT is mounted the other way up
- `FULL_REFRESH_EVERY_N_TICKS` — anti-ghosting cadence

## Acceptance

- [x] Yoda silhouette recognizable at 45×55 on a 250×122 panel
- [x] Quotes appear in a bounded bubble, 3 words max, Yoda-style syntax
- [x] Tick interval is randomized between 10 and 45 min
- [x] State persists across reboots
- [x] E-ink controller sleeps between updates
- [x] No user input — no buttons, no web interface
