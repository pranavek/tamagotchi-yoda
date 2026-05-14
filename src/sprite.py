"""45x55 1-bit Yoda silhouette plus an egg variant for the egg stage.

The bitmap is composed once at import from PIL primitives and frozen into
per-variant pixel sets. ``blit()`` is a putpixel walk; ``blit_scaled()``
renders the variant onto a small intermediate image and scales it with
nearest-neighbour to keep the panel 1-bit.
"""

from PIL import Image, ImageDraw

from .config import YODA_HEIGHT, YODA_WIDTH


class YodaSprite:
    def __init__(self) -> None:
        self.width = YODA_WIDTH
        self.height = YODA_HEIGHT
        self.variants = {
            "idle": self._build("idle"),
            "blink": self._build("blink"),
            "perked": self._build("perked"),
            "egg": self._build("egg"),
        }

    def _build(self, variant: str) -> frozenset:
        img = Image.new("1", (self.width, self.height), 255)
        d = ImageDraw.Draw(img)

        if variant == "egg":
            self._draw_egg(d)
        else:
            self._draw_yoda(d, variant)

        return frozenset(
            (x, y)
            for y in range(self.height)
            for x in range(self.width)
            if img.getpixel((x, y)) == 0
        )

    def _draw_yoda(self, d: ImageDraw.ImageDraw, variant: str) -> None:
        ear_dy = -1 if variant == "perked" else 0

        d.polygon([(0, 0 + ear_dy), (4, 16 + ear_dy), (13, 19)], fill=0)
        d.polygon([(44, 0 + ear_dy), (40, 16 + ear_dy), (31, 19)], fill=0)
        d.ellipse((8, 9, 36, 33), fill=0)
        d.polygon(
            [(4, 23), (10, 20), (34, 20), (40, 23), (44, 54), (0, 54)],
            fill=0,
        )
        d.line([(15, 34), (22, 54)], fill=255, width=2)

        if variant == "blink":
            d.line([(17, 21), (20, 21)], fill=255)
            d.line([(24, 21), (27, 21)], fill=255)
        else:
            d.rectangle([(17, 19), (19, 21)], fill=255)
            d.rectangle([(25, 19), (27, 21)], fill=255)
        d.line([(20, 27), (24, 27)], fill=255)

    def _draw_egg(self, d: ImageDraw.ImageDraw) -> None:
        cx = self.width // 2
        # Ovoid body, narrower at top.
        d.ellipse((cx - 12, 8, cx + 12, self.height - 4), fill=0)
        # Zigzag crack across the middle (white slash through the silhouette).
        crack = [
            (cx - 10, 28),
            (cx - 6, 24),
            (cx - 2, 30),
            (cx + 2, 25),
            (cx + 6, 31),
            (cx + 10, 26),
        ]
        d.line(crack, fill=255, width=1)

    def blit(self, canvas, x: int, y: int, variant: str = "idle") -> None:
        pixels = self.variants.get(variant) or self.variants["idle"]
        w, h = canvas.size
        for px, py in pixels:
            cx, cy = x + px, y + py
            if 0 <= cx < w and 0 <= cy < h:
                canvas.putpixel((cx, cy), 0)

    def blit_scaled(self, canvas, x: int, y: int, variant: str, scale: float) -> None:
        """Render variant onto a temporary 45x55 image, scale, and blit.

        Anchors the scaled sprite at the BOTTOM of the original 45x55 box so
        smaller (younger) stages appear to stand on the same baseline.
        """
        if abs(scale - 1.0) < 1e-3:
            self.blit(canvas, x, y, variant)
            return

        tmp = Image.new("1", (self.width, self.height), 255)
        self.blit(tmp, 0, 0, variant)
        new_w = max(8, int(round(self.width * scale)))
        new_h = max(10, int(round(self.height * scale)))
        scaled = tmp.resize((new_w, new_h), Image.NEAREST)

        dx = (self.width - new_w) // 2
        dy = self.height - new_h
        cw, ch = canvas.size
        for py in range(new_h):
            for px in range(new_w):
                if scaled.getpixel((px, py)) == 0:
                    tx, ty = x + dx + px, y + dy + py
                    if 0 <= tx < cw and 0 <= ty < ch:
                        canvas.putpixel((tx, ty), 0)
