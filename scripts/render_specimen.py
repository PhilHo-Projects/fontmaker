"""Render a specimen sheet from a generated font, so you can eyeball the result.

Runs on the SYSTEM python (needs Pillow). Pillow loads the TTF through FreeType,
so a specimen that renders at all is already proof the file is a valid font.
"""

import argparse

from PIL import Image, ImageDraw, ImageFont

LINES = [
    ("ABCDEFGHIJKLM", 64),
    ("NOPQRSTUVWXYZ", 64),
    ("abcdefghijklm", 64),
    ("nopqrstuvwxyz", 64),
    ("0123456789 .,:;!?'\"-()", 52),
    ("The quick brown fox jumps", 40),
    ("over the lazy dog.", 40),
    ("Handgloves 1234567890", 28),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--font", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--width", type=int, default=1100)
    args = ap.parse_args()

    padding = 40
    rendered = []
    for text, size in LINES:
        font = ImageFont.truetype(args.font, size)
        ascent, descent = font.getmetrics()
        rendered.append((text, font, ascent, descent))

    height = padding * 2 + sum(a + d + 18 for _t, _f, a, d in rendered)
    img = Image.new("L", (args.width, height), 255)
    draw = ImageDraw.Draw(img)

    y = padding
    for text, font, ascent, descent in rendered:
        draw.text((padding, y + ascent), text, font=font, fill=0, anchor="ls")
        y += ascent + descent + 18

    img.save(args.out)
    print("specimen: %s (%dx%d)" % (args.out, img.width, img.height))


if __name__ == "__main__":
    main()
