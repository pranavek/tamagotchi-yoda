"""All constants for tamagotchi-yoda. No logic — pure data."""

# ---- Display ----------------------------------------------------------------
# Underlying Waveshare driver is portrait (122x250). We render in landscape:
# the canvas is 250 wide x 122 tall, and the driver's getbuffer() handles the
# physical rotation.
EPD_WIDTH = 250
EPD_HEIGHT = 122
EPD_DRIVER = "waveshare_epd.epd2in13_V4"

# Pi <-> HAT wiring (managed by the Waveshare driver; documented for service techs)
#   SPI bus : /dev/spidev0.0
#   MOSI    : GPIO 10
#   MISO    : GPIO 9
#   SCLK    : GPIO 11
#   CS      : GPIO 8
#   DC      : GPIO 24
#   RST     : GPIO 23
#   BUSY    : GPIO 25

# Set False if the HAT is mounted with its ribbon at the opposite side.
ROTATE_180 = True

# Dump every rendered frame to ./last_display.png for off-Pi inspection.
DEBUG_DUMP_PNG = True

# ---- Timing (seconds) -------------------------------------------------------
MIN_TICK_INTERVAL = 540        # 9 minutes
MAX_TICK_INTERVAL = 660        # 11 minutes
FULL_REFRESH_EVERY_N_TICKS = 10
WEATHER_FETCH_EVERY_N_TICKS = 6   # ~60 min between Open-Meteo calls

# ---- Subtle motion ----------------------------------------------------------
POSE_DRIFT_MAX = 2

# ---- Sprite layout (pixels, on the 250x122 canvas) --------------------------
YODA_WIDTH = 45
YODA_HEIGHT = 55
YODA_X = 20
YODA_Y = 50

# ---- Speech bubble ----------------------------------------------------------
# A rounded rectangle with a chain of three tiny "thought" dots leading down
# toward Yoda's head. Two lines: Yoda's quote on top, market readout below.
BUBBLE_X = 100
BUBBLE_Y = 18
BUBBLE_W = 132
BUBBLE_H = 40
BUBBLE_TEXT_X_PAD = 7
BUBBLE_TEXT_Y_PAD = 5
BUBBLE_LINE_HEIGHT = 13
# Dots are listed bubble-to-yoda. Each entry is (cx, cy, radius).
BUBBLE_DOTS = ((92, 64, 3), (80, 73, 2), (70, 81, 1))

# ---- Status bar (top edge) --------------------------------------------------
STATUS_BAR_Y = 0
STATUS_BAR_H = 14
STAT_CELL_W = 52
ELEMENT_GLYPH_X = 232

# ---- Bottom banner (life stage / events) -----------------------------------
BANNER_Y = 112

# ---- Weather API ------------------------------------------------------------
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
LATITUDE = 33.5207             # Birmingham, AL (spec example)
LONGITUDE = -86.8025
TIMEZONE = "America/Chicago"
WEATHER_HTTP_TIMEOUT = 8

# ---- Market API -------------------------------------------------------------
# Crypto Fear & Greed Index (no auth, daily-updated, same 0-100 scale as CNN's
# stock F&G). CNN's endpoint blocks datacenter IPs; this one is permissive.
MARKET_URL = "https://api.alternative.me/fng/"
MARKET_HTTP_TIMEOUT = 8
MARKET_FETCH_EVERY_N_TICKS = 24    # ~4 h at 9-11 min ticks
COMPLACENCY_FETCH_THRESHOLD = 5    # consecutive neutral-band fetches before Complacency fires
EUPHORIA_HANGOVER_HEALTH_LOSS = 5.0

# ---- Stat decay (per real-world hour) --------------------------------------
HUNGER_DECAY_PER_HOUR = 2.0
HAPPINESS_DECAY_PER_HOUR = 1.0
HEALTH_DECAY_PER_HOUR = 0.5
HEALTH_DECAY_EXTREME_TEMP_BONUS = 5.0
ENERGY_DECAY_PER_HOUR = 1.0
ENERGY_REGEN_PER_HOUR = 5.0    # only between 22:00 and 06:00 local

# ---- Lifecycle --------------------------------------------------------------
# Set DEVELOPMENT_SPEEDUP > 1 to compress the egg/baby/child/teen progression
# for testing (e.g. 60 turns hours into minutes). 1 = real time.
DEVELOPMENT_SPEEDUP = 1.0

# ---- Persistence ------------------------------------------------------------
STATE_FILE = "/root/tamagotchi-yoda/state.json"
DEBUG_PNG_PATH = "last_display.png"
