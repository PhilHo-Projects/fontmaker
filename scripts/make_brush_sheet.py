"""Paint a sumi-e / samurai-style brush glyph sheet.

Runs on the SYSTEM python (needs Pillow, numpy, scipy).

Takes a heavy base face and repaints it as ink on paper: an angled nib for
calligraphic thick/thin contrast, torn edges, dry-brush streaks where the
bristles skip, pooled ink where the brush lingers, and a little splatter.

Each cell is painted on its own canvas and only then pasted into the sheet, so
no glyph can bleed into its neighbour by construction.
"""

import argparse
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

DEFAULT_CHARS = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
    "0123456789"
    ".,:;!?'\"-()"
)


def fit_font(font_path, cell, baseline_frac, fill=0.9):
    """Size the face so its ascent lands on the baseline row."""
    target = cell * baseline_frac * fill
    size = int(cell * baseline_frac)
    for _ in range(8):
        font = ImageFont.truetype(font_path, size)
        ascent, _ = font.getmetrics()
        if not ascent:
            break
        nxt = int(round(size * target / ascent))
        if nxt == size:
            break
        size = max(8, nxt)
    return ImageFont.truetype(font_path, size)


def smooth_noise(shape, sigma, rng):
    """Zero-mean, unit-variance smooth random field."""
    field = ndimage.gaussian_filter(rng.standard_normal(shape), sigma)
    spread = field.std()
    return field / spread if spread > 1e-9 else field


def line_footprint(length, angle_deg):
    """A 1px-wide line structuring element - a nib held at a fixed angle."""
    size = length if length % 2 else length + 1
    foot = np.zeros((size, size), dtype=bool)
    mid = size // 2
    rad = math.radians(angle_deg)
    for t in np.linspace(-mid, mid, size * 4):
        y = int(round(mid - t * math.sin(rad)))
        x = int(round(mid + t * math.cos(rad)))
        if 0 <= y < size and 0 <= x < size:
            foot[y, x] = True
    return foot


def paint(ch, font, cell, scale, baseline_frac, rng, args):
    """Render one character and beat it up until it looks brush-painted."""
    side = cell * scale
    canvas = Image.new("L", (side, side), 0)
    ImageDraw.Draw(canvas).text(
        (side // 2, int(side * baseline_frac)), ch, font=font, fill=255, anchor="ms")
    ink = np.asarray(canvas, dtype=np.float32) / 255.0
    if ink.max() <= 0:
        return None

    # Angled nib: a short directional dilation, just enough to skew the
    # stroke axis. Kept small - a long footprint swallows the counters.
    if args.nib >= 2:
        ink = ndimage.grey_dilation(
            ink, footprint=line_footprint(int(args.nib * scale), args.nib_angle))

    # Brush pressure: a slow field that eats into the stroke wherever the
    # brush lifted. Eroding (rather than dilating) is what gives real
    # thick/thin variation while keeping counters open.
    pressure = smooth_noise(ink.shape, args.pressure_scale * scale, rng)
    depth = args.erode * scale * np.clip(0.55 - 0.45 * pressure, 0.0, 1.6)
    ink = np.where(ndimage.distance_transform_edt(ink > 0.5) > depth, ink, 0.0)

    # Torn edges: two octaves of displacement, coarse wander plus fine fray.
    dy = (smooth_noise(ink.shape, 14.0 * scale, rng) * args.tear * scale
          + smooth_noise(ink.shape, 4.0 * scale, rng) * args.fray * scale)
    dx = (smooth_noise(ink.shape, 14.0 * scale, rng) * args.tear * scale
          + smooth_noise(ink.shape, 4.0 * scale, rng) * args.fray * scale)
    yy, xx = np.mgrid[0:side, 0:side]
    ink = ndimage.map_coordinates(ink, [yy + dy, xx + dx], order=1,
                                  mode="constant", cval=0.0)

    # Dry brush: bristle-shaped gaps, confined to a band along the edge so the
    # skeleton of the letter always survives.
    streaks = ndimage.gaussian_filter(rng.standard_normal(ink.shape),
                                      (1.1 * scale, 13.0 * scale))
    streaks = ndimage.rotate(streaks, args.streak_angle, reshape=False,
                             order=1, mode="reflect")
    spread = streaks.std()
    if spread > 1e-9:
        streaks /= spread
    solid = ink > 0.5
    edge_band = ndimage.distance_transform_edt(solid) < (args.bite * scale)
    ink[np.logical_and(streaks > args.dryness, edge_band)] = 0.0

    # Pooled ink where the brush sat down and bled outward.
    pools = smooth_noise(ink.shape, 16.0 * scale, rng) > args.pool
    if pools.any():
        fat = ndimage.grey_dilation(ink, size=(int(2 * scale) | 1, int(2 * scale) | 1))
        ink = np.where(pools, np.maximum(ink, fat), ink)

    # Splatter thrown off the brush - deliberately small, so --despeckle earns
    # its keep downstream.
    solid = ink > 0.5
    if args.splatter and solid.any():
        ys, xs = np.nonzero(solid)
        for _ in range(int(rng.integers(0, args.splatter + 1))):
            i = int(rng.integers(0, ys.size))
            cy = int(ys[i] + rng.normal(0, 9 * scale))
            cx = int(xs[i] + rng.normal(0, 9 * scale))
            rad = int(rng.integers(1, max(2, int(1.8 * scale))))
            y0, y1 = max(0, cy - rad), min(side, cy + rad + 1)
            x0, x1 = max(0, cx - rad), min(side, cx + rad + 1)
            if y1 > y0 and x1 > x0:
                ink[y0:y1, x0:x1] = 1.0

    # Hand-painted tilt.
    if args.tilt:
        ink = ndimage.rotate(ink, rng.uniform(-args.tilt, args.tilt),
                             reshape=False, order=1, mode="constant", cval=0.0)

    cell_img = Image.fromarray((np.clip(ink, 0, 1) * 255).astype(np.uint8))
    cell_img = cell_img.resize((cell, cell), Image.LANCZOS)
    return Image.eval(cell_img, lambda v: 255 - v)  # ink black on white


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--chars", default=DEFAULT_CHARS)
    ap.add_argument("--cols", type=int, default=13)
    ap.add_argument("--cell", type=int, default=300)
    ap.add_argument("--scale", type=int, default=3, help="supersampling factor")
    ap.add_argument("--baseline", type=float, default=0.8)
    ap.add_argument("--font", default=r"C:\Windows\Fonts\ariblk.ttf")
    ap.add_argument("--seed", type=int, default=1185)

    ap.add_argument("--nib", type=float, default=3, help="angled nib length in px")
    ap.add_argument("--nib-angle", type=float, default=-32)
    ap.add_argument("--erode", type=float, default=6.0,
                    help="max brush-pressure erosion depth, px")
    ap.add_argument("--pressure-scale", type=float, default=22.0,
                    help="size of the pressure variation, px")
    ap.add_argument("--tear", type=float, default=3.4, help="coarse edge wander, px")
    ap.add_argument("--fray", type=float, default=0.55, help="fine edge fray, px")
    ap.add_argument("--dryness", type=float, default=1.05,
                    help="higher = fewer dry-brush gaps")
    ap.add_argument("--bite", type=float, default=5.0,
                    help="how deep dry-brush gaps may cut, px")
    ap.add_argument("--streak-angle", type=float, default=-55.0,
                    help="direction the bristles drag, in degrees")
    ap.add_argument("--pool", type=float, default=0.85, help="higher = less pooling")
    ap.add_argument("--splatter", type=int, default=2, help="max specks per glyph")
    ap.add_argument("--tilt", type=float, default=1.2, help="max tilt in degrees")
    args = ap.parse_args()

    chars = args.chars
    cols = args.cols
    rows = math.ceil(len(chars) / cols)
    cell = args.cell

    font = fit_font(args.font, cell * args.scale, args.baseline)
    sheet = Image.new("L", (cols * cell, rows * cell), 255)
    rng = np.random.default_rng(args.seed)

    for i, ch in enumerate(chars):
        if ch == " ":
            continue
        painted = paint(ch, font, cell, args.scale, args.baseline, rng, args)
        if painted is None:
            continue
        sheet.paste(painted, ((i % cols) * cell, (i // cols) * cell))
        print("  painted %r" % ch, end="\r")

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    sheet.save(args.out)
    print("sheet   : %s" % args.out)
    print("grid    : %d cols x %d rows, cell %dpx, baseline %.2f"
          % (cols, rows, cell, args.baseline))
    print("chars   : %d" % len(chars))


if __name__ == "__main__":
    main()
