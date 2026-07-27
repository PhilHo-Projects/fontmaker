"""Starter for a new face. Copy to draw_<name>.py and fill it in.

Builds as-is (a handful of glyphs), so you can run it before you have a face.
Each glyph below demonstrates one construction pattern; the rest of the
alphabet is more of the same. draw_gravitas.py is the same thing carried to a
full character set - crib from it when a letter gets hard.

    fontforge\\bin\\ffpython.exe scripts/draw_template.py --out output/Demo.ttf
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from glyphlib import rect, poly, oval, band, arc, bracket, hole, Line, xsect, stroke, cw
from fontbuild import Font

# ---------------------------------------------------------------------------
# Metrics. Everything downstream is expressed against these, so set them first
# and do not fight them later.
# ---------------------------------------------------------------------------
EM, ASCENT, DESCENT = 1000, 800, 200
CAP, XH, ASC, DESC = 700, 500, 730, -210
OVS = 10                 # round shapes overshoot flat ones by this much

STEM, HAIR = 90, 40      # thick and thin. STEM/HAIR is the stroke contrast.
TIP, BRK, SERIF = 30, 70, 48   # serif slab thickness, bracket climb, overhang
LAP = 8                  # how far pieces bury into each other at a join

F = Font("Demo Serif", em=EM, ascent=ASCENT, descent=DESCENT)
F.cap_height, F.x_height = CAP, XH
glyph = F.glyph


# ---------------------------------------------------------------------------
# Your own brushes. These three cover most of a serif alphabet; add more as
# the letters demand them.
# ---------------------------------------------------------------------------

def foot(x0, x1, y=0, el=SERIF, er=SERIF, up=True):
    """Bracketed slab serif across a stem spanning x0..x1, sitting at y."""
    d = 1 if up else -1
    parts = [rect(x0 - el, y, x1 + er, y + d * TIP)]
    if el:
        parts.append(bracket(x0, y + d * TIP, -el * 0.66, d * (BRK - TIP)))
    if er:
        parts.append(bracket(x1, y + d * TIP, er * 0.66, d * (BRK - TIP)))
    return parts


def bowl_right(xj, ytop, ybot, xout, wside, wend, xattach, sq=2.06):
    """Half-bowl springing right off a stem (B D P R b p).

    One C-shaped contour whose open side is buried inside the stem, so the
    counter falls out of the union instead of being stated.
    """
    cy, ry = (ytop + ybot) / 2.0, (ytop - ybot) / 2.0
    c = [('m', (xattach, ytop)), ('l', (xj, ytop))]
    c += arc(xj, cy, xout - xj, ry, 90, -90, sq)
    c += [('l', (xattach, ybot)), ('l', (xattach, ybot + wend)),
          ('l', (xj, ybot + wend))]
    c += arc(xj, cy, xout - xj - wside, ry - wend, -90, 90, sq)
    c += [('l', (xattach, ytop - wend)), ('l', (xattach, ytop))]
    return [cw(c)]


def arch(lx0, lx1, rx0, rx1, yext, wend, yjo, yji, up=True):
    """Shoulder linking two stems: n m h (up) and u (down)."""
    s = 1 if up else -1
    return [band((lx0 + rx1) / 2.0, yjo, (rx1 - lx0) / 2.0 - LAP, yext - yjo,
                 180, 0,
                 rxi=(rx0 - lx1) / 2.0 + LAP, ryi=yext - s * wend - yji,
                 cxi=(lx1 + rx0) / 2.0, cyi=yji, sq=2.06)]


# ---------------------------------------------------------------------------
# Glyphs. The width passed to @glyph is a fallback; anything listed in
# F.sidebearings below gets its advance measured from the ink it drew.
# ---------------------------------------------------------------------------

@glyph('I', 340)                      # plain stem, serif top and bottom
def _I():
    x0, x1 = 125, 125 + STEM
    return [rect(x0, 0, x1, CAP)] + foot(x0, x1, 0) + \
        foot(x0, x1, CAP, up=False)


@glyph('O', 760)                      # free-standing ring: outer + a hole
def _O():
    return [oval(380, CAP / 2.0, 340, CAP / 2.0 + OVS, sq=2.06),
            hole(oval(380, CAP / 2.0, 340 - STEM, CAP / 2.0 + OVS - HAIR,
                      sq=2.02))]


@glyph('P', 600)                      # stem plus a bowl; counter is implicit
def _P():
    x0, x1 = 80, 80 + STEM
    return [rect(x0, 0, x1, CAP)] + \
        bowl_right(x1, CAP, 280, 560, STEM, HAIR + 8, x0 + LAP) + \
        foot(x0, x1, 0) + foot(x0, x1, CAP, er=20, up=False)


@glyph('V', 720)                      # two slanted strokes meeting at a point
def _V():
    Lo = Line((36, CAP), (330, 0))            # outer edge of the thick stroke
    Li = Lo.shift(STEM + 14)                  # inner edge
    Ro = Line((684, CAP), (390, 0))           # outer edge of the thin stroke
    Ri = Ro.shift(-(HAIR + 8))
    return [poly((36, CAP), (Li.x(CAP), CAP), xsect(Li, Ri),
                 (Ri.x(CAP), CAP), (684, CAP), (Ro.x(-6), -6),
                 (Lo.x(-6), -6))] + \
        foot(36, Li.x(CAP), CAP, up=False) + \
        foot(Ri.x(CAP), 684, CAP, up=False)


@glyph('n', 540)                      # two stems joined by a shoulder
def _n():
    l0, l1 = 70, 70 + STEM
    r0, r1 = 380, 380 + STEM
    return [rect(l0, 0, l1, XH), rect(r0, 0, r1, 340)] + \
        arch(l0, l1, r0, r1, XH + 6, HAIR + 6, 310, 270) + \
        foot(l0, l1, 0) + foot(r0, r1, 0) + \
        [rect(l0 - SERIF, XH - TIP, l1 + 12, XH),
         bracket(l0, XH - TIP, -SERIF * 0.66, -(BRK - TIP))]


@glyph('period', 280)
def _period():
    return [oval(140, 66, 66, 66, sq=2.25)]


@glyph('space', 260)
def _space():
    return []


# ---------------------------------------------------------------------------
# Spacing. Measured to the ink: flat-sided letters want a touch more than
# round ones, diagonals least of all so they interlock.
# ---------------------------------------------------------------------------
F.sidebearings.update({
    'I': (30, 30), 'O': (26, 26), 'P': (30, 26), 'V': (12, 12),
    'n': (28, 28),
})

# F.accents.update({'A': 'grave acute', ...})   # composites, once you have them
# F.kern += [("V", "a e o", -60)]               # pairs that need help


if __name__ == "__main__":
    sys.exit(F.cli())
