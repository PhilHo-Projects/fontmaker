"""Large per-glyph proof grid, with baseline / x-height / cap guides.

System python (Pillow). This is the microscope for outline work: the specimen
tells you whether text reads, this tells you which glyph is wrong.
"""

import argparse

from PIL import Image, ImageDraw, ImageFont

DEFAULT = ("ABCDEFGHIJKLMNOPQRSTUVWXYZ"
           "abcdefghijklmnopqrstuvwxyz"
           "0123456789"
           ".,:;!?'\"-()[]{}/&@#$%*+=<>")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--font", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--chars", default=DEFAULT)
    ap.add_argument("--cols", type=int, default=13)
    ap.add_argument("--size", type=int, default=150)
    args = ap.parse_args()

    cell = int(args.size * 1.5)
    base = int(cell * 0.72)
    font = ImageFont.truetype(args.font, args.size)
    upm_px = args.size  # 1000 upm maps to size px
    guides = {  # em units -> label
        0: (0, 0, 0), 492: (200, 200, 255), 680: (255, 190, 190),
        712: (210, 255, 210), -214: (255, 220, 180),
    }

    rows = (len(args.chars) + args.cols - 1) // args.cols
    img = Image.new("RGB", (args.cols * cell, rows * cell), "white")
    d = ImageDraw.Draw(img)

    for i, ch in enumerate(args.chars):
        cx = (i % args.cols) * cell
        cy = (i // args.cols) * cell
        d.rectangle([cx, cy, cx + cell - 1, cy + cell - 1], outline=(230, 230, 230))
        for em, col in guides.items():
            y = cy + base - em * upm_px / 1000.0
            d.line([cx, y, cx + cell, y], fill=col)
        adv = d.textlength(ch, font=font)
        left = cx + (cell - adv) / 2.0
        d.line([left, cy, left, cy + cell], fill=(220, 220, 240))
        d.line([left + adv, cy, left + adv, cy + cell], fill=(220, 220, 240))
        d.text((left, cy + base), ch, font=font, fill="black", anchor="ls")

    img.save(args.out)
    print("proof   : %s (%dx%d)" % (args.out, img.width, img.height))


if __name__ == "__main__":
    main()
