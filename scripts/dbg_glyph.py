"""Dissect one glyph: its parts, and what each cleanup stage does to them.

Runs under ffpython. Reach for this when a glyph vanishes, fills in solid, or
gets reported as self-intersecting and you cannot see why.

    ffpython scripts/dbg_glyph.py --face draw_gravitas b d q

Reading it:
  area          sign is the winding. All solid parts should share a sign; a
                lone odd one out is a mirrored piece that lost its direction.
  drawn         contour count before any welding - one per part.
  overlap       after removeOverlap. Should collapse to the real contour count
                (1 for n, 2 for o). More means pieces did not touch; a stray
                2-point contour means a degenerate sliver.
  closed=0      removeOverlap left it open, which reads downstream as
                "wrong direction".
"""

import argparse
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fontforge

import fontbuild
from glyphlib import area, bbox

FLAGS = {0x2: 'open', 0x4: 'self-intersecting', 0x8: 'wrong-direction',
         0x10: 'flipped-refs', 0x20: 'missing-extrema', 0x40: 'too-many-points'}


def flags(g):
    v = g.validate(1)
    named = [n for b, n in FLAGS.items() if v & b]
    return ", ".join(named) if named else "ok"


def report(g, stage):
    print("  %-9s %2d contours   %s" % (stage, len(g.foreground), flags(g)))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--face", default="draw_gravitas",
                    help="module in scripts/ holding the Font as F")
    ap.add_argument("names", nargs="+", help="glyph table keys, e.g. b d q")
    args = ap.parse_args()

    face = importlib.import_module(args.face)
    table = face.F.glyphs

    for name in args.names:
        if name not in table:
            print("== %s : not in %s" % (name, args.face))
            continue
        parts = table[name]()
        print("== %s : %d parts" % (name, len(parts)))
        for i, c in enumerate(parts):
            print("   %2d  segs=%3d  area=%10.0f  bbox=%s"
                  % (i, len(c), area(c), tuple(int(v) for v in bbox([c]))))

        f = fontforge.font()
        f.em = face.F.em
        g = f.createChar(-1, "probe")
        fontbuild.draw(g, parts)
        report(g, "drawn")
        g.removeOverlap()
        report(g, "overlap")
        fontbuild.tidy(g)
        g.correctDirection()
        report(g, "tidied")
        for c in g.foreground:
            print("     contour closed=%s clockwise=%s points=%d"
                  % (c.closed, c.isClockwise(), len(c)))
        print("   bbox %s  width %s"
              % (tuple(int(v) for v in g.boundingBox()), g.width))
    return 0


if __name__ == "__main__":
    sys.exit(main())
