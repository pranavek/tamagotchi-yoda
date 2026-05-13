"""45x55 1-bit Yoda silhouette, hand-composed via PIL primitives at import.

The bitmap is generated once per process from primitive shapes (polygons,
ellipses, lines) and then frozen into per-variant pixel sets. Blitting walks
the frozen set and writes black pixels onto the target canvas — no per-tick
PIL allocation, no file I/O.
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
        }

    def _build(self, variant: str) -> frozenset:
        img = Image.new("1", (self.width, self.height), 255)
        d = ImageDraw.Draw(img)

        ear_dy = -1 if variant == "perked" else 0

        # Pointed ears extend to x=0 and x=44 (per spec).
        d.polygon([(0, 0 + ear_dy), (4, 16 + ear_dy), (13, 19)], fill=0)
        d.polygon([(44, 0 + ear_dy), (40, 16 + ear_dy), (31, 19)], fill=0)

        # Head — filled ellipse.
        d.ellipse((8, 9, 36, 33), fill=0)

        # Hood / robe — bell-shaped trapezoid, blending into the head.
        d.polygon(
            [(4, 23), (10, 20), (34, 20), (40, 23), (44, 54), (0, 54)],
            fill=0,
        )

        # Walking cane — white diagonal slash inside the robe, reads as a
        # cane edge against the dark silhouette on a 1-bit panel.
        d.line([(15, 34), (22, 54)], fill=255, width=2)

        # Eyes — white pixels punched into the black face.
        if variant == "blink":
            d.line([(17, 21), (20, 21)], fill=255)
            d.line([(24, 21), (27, 21)], fill=255)
        elif variant == "perked":
            d.rectangle([(17, 19), (19, 21)], fill=255)
            d.rectangle([(25, 19), (27, 21)], fill=255)
        else:
            d.rectangle([(17, 19), (19, 21)], fill=255)
            d.rectangle([(25, 19), (27, 21)], fill=255)

        d.line([(20, 27), (24, 27)], fill=255)

        return frozenset(
            (x, y)
            for y in range(self.height)
            for x in range(self.width)
            if img.getpixel((x, y)) == 0
        )

    def blit(self, canvas, x: int, y: int, variant: str = "idle") -> None:
        pixels = self.variants.get(variant) or self.variants["idle"]
        w, h = canvas.size
        for px, py in pixels:
            cx, cy = x + px, y + py
            if 0 <= cx < w and 0 <= cy < h:
                canvas.putpixel((cx, cy), 0)
