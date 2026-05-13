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
MIN_TICK_INTERVAL = 600        # 10 minutes
MAX_TICK_INTERVAL = 2700       # 45 minutes
QUOTE_CHANCE = 0.15            # 15% probability per tick
QUOTE_DISPLAY_TICKS = 3        # quote stays for 3 wake cycles before clearing
FULL_REFRESH_EVERY_N_TICKS = 10  # anti-ghosting forced full refresh cadence

# ---- Sprite layout (pixels, on the 250x122 canvas) --------------------------
YODA_WIDTH = 45
YODA_HEIGHT = 55
YODA_X = 20                    # left margin
YODA_Y = 40                    # vertical bias

# ---- Speech bubble ----------------------------------------------------------
BUBBLE_X = 90
BUBBLE_Y = 20
BUBBLE_W = 140
BUBBLE_H = 40
BUBBLE_TEXT_X_PAD = 8
BUBBLE_TEXT_Y_PAD = 14
# Tail of the bubble points down-left toward Yoda's head.
BUBBLE_TAIL_TARGET = (75, 55)

# ---- Persistence ------------------------------------------------------------
STATE_FILE = "/root/tamagotchi-yoda/state.json"
DEBUG_PNG_PATH = "last_display.png"
