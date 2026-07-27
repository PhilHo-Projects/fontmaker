"""Report per-glyph geometry for a generated font, flagging likely trace junk.

Runs under ffpython.exe. Useful for spotting specks the tracer picked up from a
noisy sheet, glyphs that overflow the em box, or cells that came out empty.
"""

import argparse
import sys

import fontforge


# fontforge validation bits worth failing a build over. 0x20 (missing points at
# extrema) is deliberately excluded: it is cosmetic, and build_font.py already
# calls addExtrema() so it should not appear anyway.
SERIOUS = (
    (0x02, "open contour"),
    (0x04, "self-intersecting"),
    (0x08, "wrong direction"),
    (0x10, "flipped reference"),
    (0x40, "missing glyph name in substitution"),
    (0x80, "missing anchor"),
)
COSMETIC = ((0x20, "missing extrema"),)


def contour_bbox(contour):
    xs = [p.x for p in contour]
    ys = [p.y for p in contour]
    return min(xs), min(ys), max(xs), max(ys)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--font", required=True)
    ap.add_argument("--speck", type=float, default=0.06,
                    help="contours smaller than this fraction of em are specks")
    ap.add_argument("--all", action="store_true", help="list every glyph")
    ap.add_argument("--strict", action="store_true",
                    help="also report cosmetic issues such as missing extrema")
    args = ap.parse_args()

    font = fontforge.open(args.font)
    em = float(font.em)
    limit = args.speck * em

    encoded = sum(1 for g in font.glyphs() if g.unicode is not None and g.unicode >= 0)
    print("file    : %s" % args.font)
    print("names   : family=%r full=%r ps=%r" % (font.familyname, font.fullname, font.fontname))
    print("metrics : em=%d ascent=%d descent=%d" % (font.em, font.ascent, font.descent))
    print("coverage: %d glyphs, %d mapped to unicode\n"
          % (len(list(font.glyphs())), encoded))
    print("%-10s %-6s %5s  %-28s %s" % ("glyph", "width", "cont", "bbox", "notes"))

    flagged = 0
    for glyph in font.glyphs():
        layer = glyph.foreground
        notes = []
        for contour in layer:
            cx0, cy0, cx1, cy1 = contour_bbox(contour)
            if (cx1 - cx0) < limit and (cy1 - cy0) < limit:
                notes.append("speck %dx%d @(%d,%d)"
                             % (cx1 - cx0, cy1 - cy0, cx0, cy0))
        bbox = glyph.boundingBox()
        if bbox[3] > font.ascent + 1:
            notes.append("above ascent")
        if bbox[1] < -font.descent - 1:
            notes.append("below descent")
        if len(layer) == 0 and glyph.width == 0:
            notes.append("empty and zero-width")

        state = glyph.validate(True)
        for bit, label in SERIOUS:
            if state & bit:
                notes.append(label)
        if args.strict:
            for bit, label in COSMETIC:
                if state & bit:
                    notes.append(label)

        if notes:
            flagged += 1
        if notes or args.all:
            print("%-10s %-6d %5d  %-28s %s"
                  % (glyph.glyphname, glyph.width, len(layer),
                     "(%d,%d,%d,%d)" % tuple(int(v) for v in bbox),
                     "; ".join(notes)))

    print("\n%d glyph(s) flagged" % flagged)
    return 0


if __name__ == "__main__":
    sys.exit(main())
