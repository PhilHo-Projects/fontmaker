"""Generate a test glyph sheet PNG - stands in for an AI-generated font image.

Runs on the SYSTEM python (needs Pillow).

The sheet is a plain grid of cells, one character per cell, black ink on white,
with every glyph sitting on a baseline at a fixed fraction of the cell height.
No guide lines are drawn: anything visible in a cell gets traced as ink.
"""

import argparse
import math
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

DEFAULT_CHARS = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
    "0123456789"
    ".,:;!?'\"-()"
)


def _fit_font(font_path, cell, baseline_frac):
    """Pick a pixel size whose ascent lands on the baseline row."""
    target_ascent = cell * baseline_frac * 0.92
    size = int(cell * baseline_frac)
    for _ in range(8):
        font = ImageFont.truetype(font_path, size)
        ascent, _descent = font.getmetrics()
        if ascent == 0:
            break
        adjusted = int(round(size * target_ascent / ascent))
        if adjusted == size:
            break
        size = max(8, adjusted)
    return ImageFont.truetype(font_path, size)


def _roughen(img, seed, amount):
    """Wobble the ink so the sheet looks drawn rather than rendered."""
    rng = random.Random(seed)
    w, h = img.size
    # Low-frequency displacement field, sampled per output pixel block.
    period = max(8, int(min(w, h) / 12))
    cols = w // period + 2
    rows = h // period + 2
    field = [[(rng.uniform(-amount, amount), rng.uniform(-amount, amount))
              for _ in range(cols)] for _ in range(rows)]

    src = img.load()
    out = Image.new("L", (w, h), 255)
    dst = out.load()
    for y in range(h):
        gy = y / period
        y0 = int(gy)
        fy = gy - y0
        for x in range(w):
            gx = x / period
            x0 = int(gx)
            fx = gx - x0
            dx = (field[y0][x0][0] * (1 - fx) + field[y0][x0 + 1][0] * fx) * (1 - fy) \
                + (field[y0 + 1][x0][0] * (1 - fx) + field[y0 + 1][x0 + 1][0] * fx) * fy
            dy = (field[y0][x0][1] * (1 - fx) + field[y0][x0 + 1][1] * fx) * (1 - fy) \
                + (field[y0 + 1][x0][1] * (1 - fx) + field[y0 + 1][x0 + 1][1] * fx) * fy
            sx = min(w - 1, max(0, int(x + dx)))
            sy = min(h - 1, max(0, int(y + dy)))
            dst[x, y] = src[sx, sy]
    return out.filter(ImageFilter.GaussianBlur(0.6))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True, help="output PNG path")
    ap.add_argument("--chars", default=DEFAULT_CHARS)
    ap.add_argument("--cols", type=int, default=13)
    ap.add_argument("--cell", type=int, default=300, help="cell size in px")
    ap.add_argument("--baseline", type=float, default=0.8,
                    help="baseline position as a fraction of cell height")
    ap.add_argument("--font", default=r"C:\Windows\Fonts\georgia.ttf",
                    help="source TTF used to draw the test ink")
    ap.add_argument("--rough", type=float, default=0.0,
                    help="wobble the ink by up to N px to mimic a drawn/AI sheet")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    chars = args.chars
    cols = args.cols
    rows = math.ceil(len(chars) / cols)
    cell = args.cell

    sheet = Image.new("L", (cols * cell, rows * cell), 255)
    draw = ImageDraw.Draw(sheet)
    font = _fit_font(args.font, cell, args.baseline)

    baseline_px = int(round(cell * args.baseline))
    for i, ch in enumerate(chars):
        if ch == " ":
            continue
        cx = (i % cols) * cell + cell // 2
        cy = (i // cols) * cell + baseline_px
        draw.text((cx, cy), ch, font=font, fill=0, anchor="ms")

    if args.rough > 0:
        sheet = _roughen(sheet, args.seed, args.rough)

    sheet.save(args.out)
    print(f"sheet   : {args.out}")
    print(f"grid    : {cols} cols x {rows} rows, cell {cell}px, baseline {args.baseline}")
    print(f"chars   : {len(chars)}")


if __name__ == "__main__":
    main()
