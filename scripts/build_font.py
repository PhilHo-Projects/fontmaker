"""Turn traced glyph SVGs into a real TTF/OTF.

Runs under FontForge's bundled interpreter (ffpython.exe), NOT the system python.

Vertical placement is driven entirely by the sheet's baseline: a calibration
trace of a full-cell rectangle tells us where the canvas corners land after
import, which pins down the pixel -> em-unit transform. Horizontal metrics are
derived per glyph from its own ink bounds.
"""

import argparse
import json
import os
import re
import sys

import fontforge
import psMat

CALIBRATION_CODEPOINT = 0xE000


def _sanitise_psname(name):
    cleaned = re.sub(r"[^A-Za-z0-9]", "", name)
    return cleaned or "CustomFont"


def add_extrema_safely(glyph, tolerance=2.0):
    """Add points at curve extrema, reverting if FontForge mangles the outline.

    addExtrema() can fling a control point far outside the em on very small or
    nearly-degenerate contours - the bundled build does it in its default mode.
    The added points lie *on* existing splines, so a correct run cannot move the
    bounding box; any real movement means the outline was damaged.

    Returns True if the operation had to be reverted.
    """
    before = glyph.boundingBox()
    try:
        saved = glyph.foreground.dup()
    except Exception:
        saved = None

    glyph.addExtrema("all")

    after = glyph.boundingBox()
    if max(abs(a - b) for a, b in zip(before, after)) <= tolerance:
        return False
    if saved is not None:
        glyph.foreground = saved
    return True


def drop_degenerate_contours(glyph, min_extent=1.0):
    """Remove contours too thin to draw anything.

    Tracing plus integer rounding can leave zero-area slivers. They are
    invisible but they defeat overlap removal, which then reports the glyph as
    self-intersecting. Returns the number dropped.
    """
    layer = glyph.foreground
    keep, dropped = [], 0
    for contour in layer:
        xs = [p.x for p in contour]
        ys = [p.y for p in contour]
        if not xs or min(max(xs) - min(xs), max(ys) - min(ys)) <= min_extent:
            dropped += 1
            continue
        keep.append(contour)

    if not dropped:
        return 0
    try:
        rebuilt = fontforge.layer()
        rebuilt.is_quadratic = layer.is_quadratic
        for contour in keep:
            rebuilt += contour
        glyph.foreground = rebuilt
    except Exception:
        return 0
    return dropped


def calibrate(font, calib_svg, cell_w, cell_h, baseline_px, units_per_cell):
    """Derive the affine mapping from imported-SVG space to font units.

    The calibration SVG is a solid rectangle covering the whole cell, so its
    imported bounding box *is* the canvas. From that we can place any other
    trace of the same canvas size exactly.
    """
    probe = font.createChar(CALIBRATION_CODEPOINT, "calibration.probe")
    probe.importOutlines(calib_svg)
    bbox = probe.boundingBox()
    font.removeGlyph(probe)

    x0, y0, x1, y1 = bbox
    if x1 - x0 <= 0 or y1 - y0 <= 0:
        raise SystemExit("calibration trace produced an empty outline")

    # px_per_unit along each axis, as imported
    ax = (x1 - x0) / float(cell_w)
    by = (y1 - y0) / float(cell_h)

    scale = units_per_cell / float(cell_h)  # font units per sheet pixel
    sx = scale / ax
    sy = scale / by
    ox = -x0 * sx
    oy = scale * baseline_px - y1 * sy

    matrix = psMat.compose(psMat.scale(sx, sy), psMat.translate(ox, oy))
    return matrix, bbox


def build(spec, args):
    cell_w = spec["cell_w"]
    cell_h = spec["cell_h"]
    ascent = args.ascent
    descent = args.em - args.ascent

    font = fontforge.font()
    font.encoding = "UnicodeFull"
    font.ascent = ascent
    font.descent = descent
    font.familyname = args.family
    font.fontname = _sanitise_psname(args.family) + "-" + _sanitise_psname(args.style)
    font.fullname = "%s %s" % (args.family, args.style)
    font.weight = args.style
    font.version = args.version
    if args.copyright:
        font.copyright = args.copyright

    matrix, calib_bbox = calibrate(
        font, spec["calibration_svg"], cell_w, cell_h,
        spec["baseline_px"], float(args.em))

    sb = args.sidebearing
    made, skipped, reverted = [], [], []
    slivers = 0
    for entry in spec["glyphs"]:
        ch = entry["char"]
        cp = entry["codepoint"]

        if entry["svg"] is None:
            if ch == " ":
                space = font.createChar(cp)
                space.width = args.space_width
                made.append(ch)
            else:
                skipped.append(ch)
            continue

        glyph = font.createChar(cp)
        glyph.importOutlines(entry["svg"])
        glyph.transform(matrix)
        glyph.removeOverlap()
        glyph.simplify(args.simplify_error)
        if add_extrema_safely(glyph):
            reverted.append(ch)
        glyph.round()
        # Rounding to integer coordinates can push nearly-touching edges across
        # each other, so intricate traces need a second overlap pass *after* the
        # snap. Without this, ragged outlines ship self-intersecting.
        glyph.removeOverlap()
        glyph.round()
        slivers += drop_degenerate_contours(glyph)
        glyph.correctDirection()

        bbox = glyph.boundingBox()
        if bbox[2] - bbox[0] <= 0:
            font.removeGlyph(glyph)
            skipped.append(ch)
            continue

        # Sit the ink on a consistent left side bearing, then size the advance.
        glyph.transform(psMat.translate(sb - bbox[0], 0))
        bbox = glyph.boundingBox()
        glyph.width = int(round(bbox[2] + sb))
        made.append(ch)

    if " " not in spec_chars(spec):
        space = font.createChar(0x20)
        space.width = args.space_width

    if args.hint:
        try:
            font.autoHint()
            font.autoInstr()
        except Exception as exc:  # hinting is cosmetic; never fail the build on it
            print("warn    : hinting skipped (%s)" % exc)

    out = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    font.generate(out)

    print("calib   : canvas bbox %s for a %dx%dpx cell" %
          (tuple(round(v, 2) for v in calib_bbox), cell_w, cell_h))
    print("glyphs  : %d built, %d skipped" % (len(made), len(skipped)))
    if slivers:
        print("slivers : dropped %d degenerate contour(s)" % slivers)
    if reverted:
        print("extrema : reverted damaged addExtrema on %r" % "".join(reverted))
    if skipped:
        print("skipped : %r" % "".join(skipped))
    print("output  : %s (%d bytes)" % (out, os.path.getsize(out)))
    return font, out


def spec_chars(spec):
    return set(g["char"] for g in spec["glyphs"])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--spec", required=True, help="glyphs.json from prepare_glyphs.py")
    ap.add_argument("--out", required=True, help="output .ttf / .otf path")
    ap.add_argument("--family", default="Test Sheet")
    ap.add_argument("--style", default="Regular")
    ap.add_argument("--version", default="1.0")
    ap.add_argument("--copyright", default="")
    ap.add_argument("--em", type=int, default=1000)
    ap.add_argument("--ascent", type=int, default=800,
                    help="em units above the baseline; the sheet cell maps onto em")
    ap.add_argument("--sidebearing", type=int, default=45)
    ap.add_argument("--space-width", type=int, default=300)
    ap.add_argument("--simplify-error", type=float, default=1.0)
    ap.add_argument("--hint", action="store_true")
    args = ap.parse_args()

    with open(args.spec, "r", encoding="utf-8") as fh:
        spec = json.load(fh)

    build(spec, args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
