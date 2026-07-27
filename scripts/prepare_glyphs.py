"""Slice a glyph sheet into per-character bitmaps and vectorise them with potrace.

Runs on the SYSTEM python (needs Pillow). Writes <work>/glyphs.json describing
the sheet geometry plus one SVG per character, ready for build_font.py.

Every cell is emitted at the SAME canvas size, uncropped, so a single
calibration trace is enough for FontForge to recover the pixel->em transform.
"""

import argparse
import json
import math
import os
import shutil
import statistics
import subprocess
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUNDLED_POTRACE = os.path.join(ROOT, "fontforge", "bin", "potrace.exe")


def find_potrace(explicit=None):
    for cand in (explicit, os.environ.get("POTRACE"), BUNDLED_POTRACE,
                 shutil.which("potrace")):
        if cand and os.path.isfile(cand):
            return cand
    raise SystemExit("potrace not found; pass --potrace or set POTRACE")


def to_ink_mask(cell_img, threshold, polarity):
    """Return a mode-'1' image where black pixels are ink."""
    gray = cell_img.convert("L")
    if polarity == "auto":
        dark = sum(gray.histogram()[:threshold])
        polarity = "light-on-dark" if dark > gray.width * gray.height * 0.5 else "dark-on-light"
    if polarity == "light-on-dark":
        gray = gray.point(lambda v: 255 - v)
    return gray.point(lambda v: 0 if v < threshold else 255, mode="1"), polarity


def clean_bleed(mask, ratio):
    """Drop ink that leaked in from a neighbouring cell.

    Bleed-through is a small blob touching a cell border - a descender or
    ascender from the cell next door. Dots on i/j don't touch a border, and a
    real glyph that does touch one is never small relative to its own body, so
    "small AND border-touching" isolates the junk.

    Returns (mask, fragments_removed). Silently a no-op without scipy.
    """
    try:
        import numpy as np
        from scipy import ndimage
    except ImportError:
        return mask, -1

    arr = np.array(mask)
    ink = ~arr if arr.dtype == bool else arr == 0
    labels, count = ndimage.label(ink, structure=np.ones((3, 3), dtype=int))
    if count <= 1:
        return mask, 0

    areas = ndimage.sum_labels(ink, labels, index=range(1, count + 1))
    biggest = areas.max()

    border = set(labels[0, :].tolist()) | set(labels[-1, :].tolist()) \
        | set(labels[:, 0].tolist()) | set(labels[:, -1].tolist())
    border.discard(0)

    drop = [i for i in border if areas[i - 1] < ratio * biggest]
    if not drop:
        return mask, 0

    ink[np.isin(labels, drop)] = False
    return Image.fromarray(np.where(ink, 0, 255).astype("uint8"), "L") \
        .convert("1", dither=Image.Dither.NONE), len(drop)


def ink_bbox(mask):
    """Bounding box of black pixels, or None."""
    # getbbox() finds non-zero pixels; ink is 0, so invert first.
    inverted = mask.point(lambda v: 255 - v, mode="1")
    return inverted.getbbox()


def trace(potrace, src, dst, despeckle, alphamax, opttolerance):
    subprocess.run(
        [potrace, "--backend", "svg", "--turdsize", str(despeckle),
         "--alphamax", str(alphamax), "--opttolerance", str(opttolerance),
         "--output", dst, src],
        check=True, capture_output=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sheet", required=True)
    ap.add_argument("--work", required=True, help="scratch directory for bitmaps/SVGs")
    ap.add_argument("--chars", required=True)
    ap.add_argument("--cols", type=int, required=True)
    ap.add_argument("--baseline", type=float, default=0.8)
    ap.add_argument("--threshold", type=int, default=128)
    ap.add_argument("--polarity", choices=["auto", "dark-on-light", "light-on-dark"],
                    default="auto")
    ap.add_argument("--despeckle", type=int, default=4,
                    help="potrace --turdsize: drop specks smaller than N px")
    ap.add_argument("--alphamax", type=float, default=1.0,
                    help="potrace corner threshold; 0 = all corners, 1.334 = all curves")
    ap.add_argument("--opttolerance", type=float, default=0.2)
    ap.add_argument("--bleed-ratio", type=float, default=0.15,
                    help="drop border-touching blobs smaller than this fraction of the "
                         "glyph body (neighbouring-cell bleed); 0 disables")
    ap.add_argument("--min-ink", type=int, default=8,
                    help="cells with fewer ink pixels than this count as blank")
    ap.add_argument("--baseline-tolerance", type=float, default=0.05,
                    help="max baseline drift across rows, as a fraction of cell height")
    ap.add_argument("--strict-grid", action="store_true",
                    help="exit non-zero when the grid looks misaligned")
    ap.add_argument("--potrace", default=None)
    args = ap.parse_args()

    potrace = find_potrace(args.potrace)
    os.makedirs(args.work, exist_ok=True)
    for name in os.listdir(args.work):
        if name.endswith((".pbm", ".svg")):
            os.remove(os.path.join(args.work, name))

    sheet = Image.open(args.sheet)
    chars = args.chars
    cols = args.cols
    rows = math.ceil(len(chars) / cols)
    cell_w = sheet.width // cols
    cell_h = sheet.height // rows
    if cell_w < 8 or cell_h < 8:
        raise SystemExit(f"cells too small ({cell_w}x{cell_h}px) for a {cols}x{rows} grid")

    baseline_px = cell_h * args.baseline
    detected_polarity = args.polarity

    glyphs = []
    blank = []
    cleaned = []
    touching = []
    row_bottoms = {}
    warned_scipy = False
    for i, ch in enumerate(chars):
        r, c = divmod(i, cols)
        box = (c * cell_w, r * cell_h, (c + 1) * cell_w, (r + 1) * cell_h)
        mask, detected_polarity = to_ink_mask(sheet.crop(box), args.threshold, args.polarity)
        if args.bleed_ratio > 0:
            mask, removed = clean_bleed(mask, args.bleed_ratio)
            if removed > 0:
                cleaned.append("%s(%d)" % (ch, removed))
            elif removed < 0 and not warned_scipy:
                print("warn    : scipy not installed; cell-bleed cleanup disabled")
                warned_scipy = True

        bbox = ink_bbox(mask)
        if bbox is not None and (bbox[0] <= 0 or bbox[1] <= 0
                                 or bbox[2] >= cell_w or bbox[3] >= cell_h):
            touching.append(ch)
        if bbox is not None:
            row_bottoms.setdefault(r, []).append(bbox[3] / float(cell_h))
        ink_px = 0 if bbox is None else (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
        if bbox is None or ink_px < args.min_ink:
            blank.append(ch)
            glyphs.append({"char": ch, "codepoint": ord(ch), "svg": None, "cell": [r, c]})
            continue

        stem = f"u{ord(ch):04X}"
        pbm = os.path.join(args.work, stem + ".pbm")
        svg = os.path.join(args.work, stem + ".svg")
        mask.save(pbm)
        trace(potrace, pbm, svg, args.despeckle, args.alphamax, args.opttolerance)
        glyphs.append({"char": ch, "codepoint": ord(ch), "svg": svg, "cell": [r, c]})

    # Calibration target: a solid cell-sized rectangle. Tracing it tells
    # build_font.py exactly where the canvas corners land in font units.
    calib_pbm = os.path.join(args.work, "_calibration.pbm")
    calib_svg = os.path.join(args.work, "_calibration.svg")
    Image.new("1", (cell_w, cell_h), 0).save(calib_pbm)
    trace(potrace, calib_pbm, calib_svg, 0, 1.0, 0.2)

    spec = {
        "sheet": os.path.abspath(args.sheet),
        "cols": cols,
        "rows": rows,
        "cell_w": cell_w,
        "cell_h": cell_h,
        "baseline_px": baseline_px,
        "baseline_frac": args.baseline,
        "polarity": detected_polarity,
        "calibration_svg": calib_svg,
        "glyphs": glyphs,
    }
    spec_path = os.path.join(args.work, "glyphs.json")
    with open(spec_path, "w", encoding="utf-8") as fh:
        json.dump(spec, fh, indent=2)

    traced = sum(1 for g in glyphs if g["svg"])
    print(f"grid    : {cols}x{rows}, cell {cell_w}x{cell_h}px, polarity {detected_polarity}")
    print(f"traced  : {traced}/{len(chars)} cells")
    if cleaned:
        print(f"debleed : removed neighbour-cell ink from {' '.join(cleaned)}")
    if blank:
        print(f"blank   : {''.join(blank)!r} (will become spaces or be skipped)")
    print(f"spec    : {spec_path}")

    # Ink running into a cell edge means the grid we sliced on is not the grid
    # the sheet was drawn on. This is the usual failure for generated images,
    # which almost always carry a margin around the artwork, and it is otherwise
    # silent - the build "succeeds" and the glyphs drift off the baseline.
    problems = []
    if len(touching) > max(3, len(chars) // 20):
        problems.append("%d of %d cells have ink running into a cell edge: %s"
                        % (len(touching), len(chars), "".join(touching)))

    # A margin around the grid leaves the row pitch slightly wrong, so each
    # successive row's glyphs sit a little higher inside their cell. Ink never
    # touches an edge, but the baseline walks. Most glyphs in a row rest on the
    # baseline, so the median ink bottom is a robust estimate of where it is.
    medians = [statistics.median(v) for _, v in sorted(row_bottoms.items()) if v]
    if len(medians) > 1:
        drift = max(medians) - min(medians)
        if drift > args.baseline_tolerance:
            problems.append(
                "the baseline drifts %.1f%% of cell height across rows "
                "(per-row medians %s); rows should agree within ~2%%"
                % (drift * 100, [round(m, 3) for m in medians]))

    if problems:
        print()
        print("!! GRID LOOKS MISALIGNED")
        for problem in problems:
            print("!! %s" % problem)
        print("!! Sliced a %dx%d grid of %dx%dpx cells, assuming the grid fills"
              " the image exactly." % (cols, rows, cell_w, cell_h))
        print("!! Usual causes: the sheet has a margin around the artwork (crop"
              " it off), --cols is wrong, or --chars does not match the cells.")
        if args.strict_grid:
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
