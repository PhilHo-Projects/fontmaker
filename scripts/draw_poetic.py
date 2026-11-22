"""Draw "Poetic Grace" - A slender, high-contrast literary serif for poetry and verse.

Runs under fontforge\\bin\\ffpython.exe.

Design brief: Didone-meets-Garamond literary elegance - tall capitals and soaring
ascenders over a petite x-height, crisp ~3:1 vertical contrast, razor-fine bracketed
hairline serifs, and Didone ball terminals.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from glyphlib import (
    rect, poly, oval, band, band_ends, bracket, ept, Line, xsect, stroke,
    rev, cw, ccw, hole, arc, move, moveall, flipx, flipy, bbox
)
from fontbuild import Font

LAP = 8

# ---------------------------------------------------------------------------
# Vertical Metrics (Slender, Tall, Literary Proportions)
# ---------------------------------------------------------------------------
EM = 1000
ASCENT = 800
DESCENT = 200

CAP = 710             # Tall, stately capitals (safely under 760 typo ascent)
XH = 445              # Petite literary x-height (~0.63 of CAP)
ASC = 740             # Soaring ascenders rising gracefully above CAP
DESC = -200           # Long slender descenders
FIG = 695             # Lining figures slightly below CAP
OVS = 10              # Optical overshoot on round extremes

# ---------------------------------------------------------------------------
# Weights & Contrast (~3:1 Literary Didone Contrast)
# ---------------------------------------------------------------------------
CSTEM = 68            # Slender capital main stem
CHAIR = 22            # Delicate capital hairline
CBAR = 24             # Capital horizontal bar / arm

STEM = 58             # Slender lowercase vertical stem
HAIR = 20             # Lowercase hairline
LBAR = 22             # Lowercase horizontal bar

TIP = 16              # Fine hairline serif slab
BRK = 52              # Graceful concave bracket climb
SE = 50               # Cap serif projection
SL = 40               # Lowercase serif projection

SQ = 2.04             # Smooth classical superellipse
SQI = 2.00


# ---------------------------------------------------------------------------
# Shared Brushes
# ---------------------------------------------------------------------------

def foot(x0, x1, y=0, el=SL, er=SL, up=True, tip=TIP, brk=BRK):
    """Delicate bracketed serif across a stem spanning x0..x1 at y.

    Brackets are buried 3 units into both the stem and the slab so no edge is
    laid flush (avoiding FontForge overlap degeneracy).
    """
    d = 1 if up else -1
    b = 3
    parts = [rect(x0 - el, y, x1 + er, y + d * tip)]
    if el:
        parts.append(bracket(x0 + b, y + d * (tip - b),
                             -(el * 0.68 + b), d * (brk - tip + b),
                             tension=0.38))
    if er:
        parts.append(bracket(x1 - b, y + d * (tip - b),
                             er * 0.68 + b, d * (brk - tip + b),
                             tension=0.38))
    return parts


def armend(x, y0, y1, down=0, up=0, inward=1, tip=TIP, brk=BRK):
    """Crisp terminal serif closing a horizontal arm spanning y0..y1."""
    b = 3
    parts = [rect(x, y0 - down, x + inward * tip, y1 + up)]
    if down:
        parts.append(bracket(x + inward * (tip - b), y0 + b,
                             inward * (brk - tip + b), -(down * 0.78 + b),
                             tension=0.38))
    if up:
        parts.append(bracket(x + inward * (tip - b), y1 - b,
                             inward * (brk - tip + b), up * 0.78 + b,
                             tension=0.38))
    return parts


def head_serif(x0, x1, y=XH, el=SL, er=10, tip=TIP, brk=BRK):
    """Asymmetric left-pointing head serif for lowercase ascenders/stems."""
    return foot(x0, x1, y, el=el, er=er, up=False, tip=tip, brk=brk)


def bowl_right(xj, ytop, ybot, xout, wside, wtop, wbot, xattach, sq=SQ):
    """Slender half-bowl springing right off a stem (B D P R b p)."""
    cy = (ytop + ybot) / 2.0
    ry = (ytop - ybot) / 2.0
    rx = xout - xj
    cyi = cy - (wtop - wbot) / 2.0
    ryi = ry - (wtop + wbot) / 2.0
    c = [('m', (xattach, ytop)), ('l', (xj, ytop))]
    c += arc(xj, cy, rx, ry, 90, -90, sq)
    c += [('l', (xattach, ybot)), ('l', (xattach, ybot + wbot)),
          ('l', (xj, ybot + wbot))]
    c += arc(xj, cyi, rx - wside, ryi, -90, 90, SQI)
    c += [('l', (xattach, ytop - wtop)), ('l', (xattach, ytop))]
    return [cw(c)]


def bowl_left(xj, ytop, ybot, xout, wside, wtop, wbot, xattach, sq=SQ):
    """Mirror of bowl_right (d q a-bowl)."""
    parts = bowl_right(0, ytop, ybot, xj - xout, wside, wtop, wbot,
                       xj - xattach, sq=sq)
    return moveall([flipx(c, 0) for c in parts], xj, 0)


def arch(lx0, lx1, rx0, rx1, yext, wend, yjo, yji, sq=SQ, up=True):
    """Graceful shoulder linking two stems: n m h (up=True) and U u (up=False)."""
    s = 1 if up else -1
    cx = (lx0 + rx1) / 2.0
    cxi = (lx1 + rx0) / 2.0
    rx = (rx1 - lx0) / 2.0 - LAP
    rxi = (rx0 - lx1) / 2.0 + LAP
    ry = yext - yjo
    ryi = yext - s * wend - yji
    return [band(cx, yjo, rx, ry, 180, 0, rxi=rxi, ryi=ryi, cxi=cxi, cyi=yji,
                 sq=sq, sqi=SQI)]


def ring(cx, cy, rx, ry, wside, wend, sq=SQ):
    return [oval(cx, cy, rx, ry, sq=sq),
            hole(oval(cx, cy, rx - wside, ry - wend, sq=SQI))]


def dot(cx, cy, r, ry=None):
    return [oval(cx, cy, r, r if ry is None else ry, sq=2.12)]


def ball_at(o, i, r, dx=0, dy=0):
    """Didone ball terminal welded onto a band end (o, i)."""
    mx = (o[0] + i[0]) / 2.0 + dx
    my = (o[1] + i[1]) / 2.0 + dy
    return oval(mx, my, r, r * 0.96, sq=2.08)


def comma_shape(cx, cy, s):
    """Delicate teardrop comma / quote hanging below cy."""
    ball = oval(cx, cy, s, s, sq=2.15)
    tail = [('m', (cx - s * 0.10, cy + s * 0.35)),
            ('c', (cx + s * 1.05, cy - s * 0.25), (cx + s * 0.25, cy - s * 1.75),
             (cx - s * 1.15, cy - s * 2.65)),
            ('c', (cx - s * 0.55, cy - s * 1.60), (cx - s * 0.70, cy - s * 0.70),
             (cx - s * 0.85, cy - s * 0.05)),
            ('l', (cx - s * 0.10, cy + s * 0.35))]
    return [ball, cw(tail)]


def scaled(cs, sx, sy, cx, cy):
    """Scale contours around (cx, cy)."""
    out = []
    for c in cs:
        nc = []
        for seg in c:
            pts = tuple((cx + (x - cx) * sx, cy + (y - cy) * sy)
                        for (x, y) in seg[1:])
            nc.append((seg[0],) + pts)
        out.append(nc)
    return out


def cshape(cx, cy, rx, ry, wside, wend, t0, t1, r_top=30, sq=SQ):
    """Open C/c arc with a Didone ball terminal at top and crisp sheared end below."""
    kw = dict(wside=wside, wend=wend, sq=sq, sqi=SQI)
    out = [band(cx, cy, rx, ry, t0, t1, **kw)]
    o, i = band_ends(cx, cy, rx, ry, t0, **kw)
    # Ball terminal tucked softly inside the upper stroke end
    out.append(oval((o[0] + i[0]) / 2.0 - r_top * 0.18,
                    (o[1] + i[1]) / 2.0 - r_top * 0.22,
                    r_top, r_top * 0.94, sq=2.1))
    # Subtle flare on lower terminal
    o, i = band_ends(cx, cy, rx, ry, t1, **kw)
    out.append(poly(o, (o[0] + 18, o[1] + 6), (i[0] + 10, i[1] + 12), i))
    return out


def sshape(uc, lc, ws, we, tu, tl, r_top=28, r_bot=30):
    """High-contrast Didone S / s with smooth sinuous spine and ball terminals."""
    kw = dict(wside=ws, wend=we, sq=2.04, sqi=2.00)
    out = [band(uc[0], uc[1], uc[2], uc[3], tu[0], tu[1], **kw),
           band(lc[0], lc[1], lc[2], lc[3], tl[0], tl[1], **kw)]
    # Smoothly blended spine connecting upper-left to lower-right
    ou, iu = band_ends(uc[0], uc[1], uc[2], uc[3], tu[1], **kw)
    ol, il = band_ends(lc[0], lc[1], lc[2], lc[3], tl[0], **kw)
    # Cubic-curved spine so the transition out of both bowls has zero kink
    dx = (ol[0] - ou[0]) * 0.45
    spine = [
        ('m', ou),
        ('c', (ou[0] + dx * 0.65, ou[1] - 18), (il[0] - dx * 0.35, il[1] + 22), il),
        ('l', ol),
        ('c', (ol[0] - dx * 0.65, ol[1] + 18), (iu[0] + dx * 0.35, iu[1] - 22), iu),
        ('l', ou),
    ]
    out.append(cw(spine))
    # Upper right ball terminal
    o, i = band_ends(uc[0], uc[1], uc[2], uc[3], tu[0], **kw)
    out.append(oval((o[0] + i[0]) / 2.0 - r_top * 0.22,
                    (o[1] + i[1]) / 2.0 - r_top * 0.26,
                    r_top, r_top * 0.95, sq=2.1))
    # Lower left ball terminal
    o, i = band_ends(lc[0], lc[1], lc[2], lc[3], tl[1], **kw)
    out.append(oval((o[0] + i[0]) / 2.0 + r_bot * 0.22,
                    (o[1] + i[1]) / 2.0 + r_bot * 0.26,
                    r_bot, r_bot * 0.95, sq=2.1))
    return out


def wshape(top, bot, v1, v2, tops, thick, thin, serif):
    """Two clean overlapping Didone Vs."""
    al, br, cl, dr = tops
    A_l = Line((al, top), (v1, bot))
    A_r = A_l.shift(thick)
    B_r = Line((br, top), (v1, bot))
    B_l = B_r.shift(-thin)
    C_l = Line((cl, top), (v2, bot))
    C_r = C_l.shift(thick)
    D_r = Line((dr, top), (v2, bot))
    D_l = D_r.shift(-thin)
    out = [poly((al, top), (A_r.x(top), top), xsect(A_r, B_l),
                (B_l.x(top), top), (C_r.x(top), top), xsect(C_r, D_l),
                (D_l.x(top), top), (dr, top), (v2, bot), xsect(B_r, C_l),
                (v1, bot))]
    out += foot(al, A_r.x(top), top, el=serif, er=serif - 6, up=False)
    out += foot(B_l.x(top), C_r.x(top), top, el=serif - 8, er=serif - 8, up=False)
    out += foot(D_l.x(top), dr, top, el=serif - 6, er=serif, up=False)
    return out


def kshape(x0, top, armtip, armw, legw, legfoot, cut, serif):
    """Thin upper arm + slender thick lower leg buried cleanly into the stem."""
    arm = poly((x0 + 36, cut + 46), (armtip - armw, top), (armtip, top),
               (x0 + 36, cut))
    leg = Line((x0 + 70, cut + 20), (legfoot - legw, 0))
    out = [arm, stroke(leg, legw, 0, cut + 76)]
    out += foot(armtip - armw, armtip, top, el=serif, er=serif - 4, up=False)
    out += foot(legfoot - legw, legfoot, 0, el=serif - 6, er=serif)
    return out


# ---------------------------------------------------------------------------
# Font Setup
# ---------------------------------------------------------------------------
F = Font("Poetic Grace", style="Regular", em=EM, ascent=ASCENT, descent=DESCENT,
         vendor="POET", weight=400,
         copyright="Poetic Grace - High-contrast literary serif drawn with FontMaker.")
F.cap_height = CAP
F.x_height = XH
glyph = F.glyph


# =========================== UPPERCASE =====================================

@glyph('A', 580)
def _A():
    top = CAP + 6
    Lo = Line((54, 0), (274, top))
    Li = Lo.shift(CHAIR + 8)
    Ro = Line((294, top), (520, 0))
    Ri = Ro.shift(-(CSTEM + 4))
    ax, ay = xsect(Li, Ri)
    b0, b1 = 205, 205 + CBAR
    body = poly((54, 0), (274, top), (294, top), (520, 0),
                (Ri.x(0), 0), (Ri.x(b0), b0), (Li.x(b0), b0), (Li.x(0), 0))
    counter = hole(poly((Li.x(b1), b1), (ax, ay), (Ri.x(b1), b1)))
    out = [body, counter]
    out += foot(54, Li.x(0), 0, el=SE - 4, er=SE - 4)
    out += foot(Ri.x(0), 520, 0, el=SE - 8, er=SE - 2)
    return out


@glyph('B', 530)
def _B():
    x0, x1 = 70, 70 + CSTEM
    waist = 382
    out = [rect(x0, 0, x1, CAP)]
    out += bowl_right(x1, CAP, waist - 10, 444, 62, CBAR, 20, x0 + LAP)
    out += bowl_right(x1, waist + 12, 0, 478, CSTEM + 2, 20, CBAR, x0 + LAP)
    out += foot(x0, x1, 0, el=SE, er=16)
    out += foot(x0, x1, CAP, el=SE, er=16, up=False)
    return out


@glyph('C', 560)
def _C():
    return cshape(296, CAP / 2.0, 244, CAP / 2.0 + OVS, CSTEM + 4, CHAIR + 2,
                  52, 314, r_top=36, sq=2.04)


@glyph('D', 580)
def _D():
    x0, x1 = 70, 70 + CSTEM
    out = [rect(x0, 0, x1, CAP)]
    out += bowl_right(x1, CAP, 0, 526, CSTEM + 4, CBAR, CBAR, x0 + LAP, sq=2.12)
    out += foot(x0, x1, 0, el=SE, er=16)
    out += foot(x0, x1, CAP, el=SE, er=16, up=False)
    return out


@glyph('E', 500)
def _E():
    x0, x1 = 70, 70 + CSTEM
    mid = 360
    out = [rect(x0, 0, x1, CAP),
           rect(x0 - SE, CAP - CBAR, 434, CAP),
           rect(x0 - SE, 0, 452, CBAR),
           rect(x1 - LAP, mid, 384, mid + LBAR)]
    out.append(bracket(x0 + 3, CAP - CBAR + 3, -(SE * 0.68 + 3), -(BRK - CBAR + 3), 0.38))
    out.append(bracket(x0 + 3, CBAR - 3, -(SE * 0.68 + 3), BRK - CBAR + 3, 0.38))
    out += armend(434, CAP - CBAR, CAP, down=52, inward=-1, brk=56)
    out += armend(452, 0, CBAR, up=56, inward=-1, brk=56)
    out += armend(384, mid, mid + LBAR, down=30, up=30, inward=-1, brk=40)
    return out


@glyph('F', 470)
def _F():
    x0, x1 = 70, 70 + CSTEM
    mid = 356
    out = [rect(x0, 0, x1, CAP),
           rect(x0 - SE, CAP - CBAR, 424, CAP),
           rect(x1 - LAP, mid, 372, mid + LBAR)]
    out.append(bracket(x0 + 3, CAP - CBAR + 3, -(SE * 0.68 + 3), -(BRK - CBAR + 3), 0.38))
    out += armend(424, CAP - CBAR, CAP, down=52, inward=-1, brk=56)
    out += armend(372, mid, mid + LBAR, down=30, up=30, inward=-1, brk=40)
    out += foot(x0, x1, 0, el=SE, er=SE)
    return out


@glyph('G', 590)
def _G():
    cx, cy, rx, ry = 296, CAP / 2.0, 246, CAP / 2.0 + OVS
    kw = dict(wside=CSTEM + 4, wend=CHAIR + 2, sq=2.04, sqi=2.00)
    # Sweep cleanly into the vertical spur without poking past it
    out = [band(cx, cy, rx, ry, 52, 326, **kw)]
    o, i = band_ends(cx, cy, rx, ry, 52, **kw)
    out.append(oval((o[0] + i[0]) / 2.0 - 6, (o[1] + i[1]) / 2.0 - 8, 36, 34, sq=2.1))
    # Clean Didone spur dropping to baseline-aligned jaw (no corner notch)
    sx0, sx1 = 442, 442 + CSTEM - 6
    out.append(rect(sx0, 22, sx1, 316))
    # Smooth fill joining lower bowl to vertical spur
    out.append(poly((396, 12), (446, 22), (446, 118), (376, 52)))
    out += foot(sx0, sx1, 316, el=50, er=28, up=False)
    return out


@glyph('H', 600)
def _H():
    l0, l1 = 70, 70 + CSTEM
    r0, r1 = 456, 456 + CSTEM
    bar = 362
    out = [rect(l0, 0, l1, CAP), rect(r0, 0, r1, CAP),
           rect(l1 - LAP, bar, r0 + LAP, bar + CBAR)]
    for x0, x1 in ((l0, l1), (r0, r1)):
        out += foot(x0, x1, 0, el=SE, er=SE)
        out += foot(x0, x1, CAP, el=SE, er=SE, up=False)
    return out


@glyph('I', 280)
def _I():
    x0, x1 = 106, 106 + CSTEM
    out = [rect(x0, 0, x1, CAP)]
    out += foot(x0, x1, 0, el=SE + 4, er=SE + 4)
    out += foot(x0, x1, CAP, el=SE + 4, er=SE + 4, up=False)
    return out


@glyph('J', 370)
def _J():
    x0, x1 = 210, 210 + CSTEM
    # Smooth Didone J descending just below baseline with ball terminal
    cx, cy, rx, ry = 148, 126, 130, 142
    hk = dict(rxi=64, ryi=118, cxi=146, cyi=126, sq=2.04, sqi=2.00)
    out = [rect(x0, 114, x1, CAP),
           band(cx, cy, rx, ry, 0, -142, **hk)]
    o, i = band_ends(cx, cy, rx, ry, -142, **hk)
    out.append(oval((o[0] + i[0]) / 2.0 + 4, (o[1] + i[1]) / 2.0 + 10, 34, 32, sq=2.1))
    out += foot(x0, x1, CAP, el=SE, er=SE, up=False)
    return out


@glyph('K', 560)
def _K():
    x0, x1 = 70, 70 + CSTEM
    out = [rect(x0, 0, x1, CAP)]
    out += kshape(x0, CAP, 496, CHAIR + 14, CSTEM + 4, 514, 290, SE - 6)
    out += foot(x0, x1, 0, el=SE, er=SE)
    out += foot(x0, x1, CAP, el=SE, er=SE, up=False)
    return out


@glyph('L', 480)
def _L():
    x0, x1 = 70, 70 + CSTEM
    out = [rect(x0, 0, x1, CAP), rect(x0 - SE, 0, 446, CBAR)]
    out.append(bracket(x0 + 3, CBAR - 3, -(SE * 0.68 + 3), BRK - CBAR + 3, 0.38))
    out += armend(446, 0, CBAR, up=66, inward=-1, brk=60)
    out += foot(x0, x1, CAP, el=SE, er=SE, up=False)
    return out


@glyph('M', 740)
def _M():
    # Classical high-contrast literary M: thin left stem, thick left diag,
    # thin right diag, thick right stem!
    l0, l1 = 68, 68 + CHAIR + 8        # thin left vertical (30)
    r0, r1 = 602, 602 + CSTEM          # thick right vertical (68)
    mid_x = 342
    L_out = Line((l0, CAP), (mid_x - 30, 0))
    L_in = L_out.shift(CSTEM + 2)
    R_in = Line((r1, CAP), (mid_x + 2, 0))
    R_out = R_in.shift(-(CHAIR + 8))
    # Build cleanly from overlapping pieces: left stem, right stem, and V strokes
    out = [
        rect(l0, 0, l1, CAP),
        rect(r0, 0, r1, CAP),
        stroke(L_out, CSTEM + 2, 0, CAP),
        stroke(R_out, CHAIR + 8, 0, CAP),
    ]
    out += foot(l0, l1, 0, el=SE, er=SE)
    out += foot(r0, r1, 0, el=SE, er=SE)
    out += foot(l0, L_in.x(CAP), CAP, el=SE, er=0, up=False)
    out += foot(R_out.x(CAP), r1, CAP, el=0, er=SE, up=False)
    return out


@glyph('N', 580)
def _N():
    # Classic high-contrast N: thin stems, thick diagonal
    w_thin = CHAIR + 10
    l0, l1 = 70, 70 + w_thin
    r0, r1 = 480, 480 + w_thin
    D = Line((l0, CAP), (r1 - CSTEM, 0))
    out = [rect(l0, 0, l1, CAP),
           rect(r0, 0, r1, CAP),
           stroke(D, CSTEM, 0, CAP)]
    out += foot(l0, l1, 0, el=SE, er=SE)
    out += foot(l0, l0 + CSTEM, CAP, el=SE, er=0, up=False)
    out += foot(r0, r1, CAP, el=SE, er=SE, up=False)
    return out


@glyph('O', 600)
def _O():
    return ring(300, CAP / 2.0, 256, CAP / 2.0 + OVS, CSTEM + 4, CHAIR + 2)


@glyph('P', 510)
def _P():
    x0, x1 = 70, 70 + CSTEM
    out = [rect(x0, 0, x1, CAP)]
    out += bowl_right(x1, CAP, 316, 464, 62, CBAR, CBAR, x0 + LAP)
    out += foot(x0, x1, 0, el=SE, er=SE)
    out += foot(x0, x1, CAP, el=SE, er=16, up=False)
    return out


@glyph('Q', 600)
def _Q():
    out = ring(300, CAP / 2.0, 256, CAP / 2.0 + OVS, CSTEM + 4, CHAIR + 2)
    # Sweeping poetic calligraphic tail
    tail = [('m', (310, 60)),
            ('c', (370, 52), (430, -35), (496, -110)),
            ('c', (540, -158), (595, -152), (620, -118)),
            ('c', (592, -182), (518, -198), (452, -138)),
            ('c', (390, -82), (344, -12), (282, 16)),
            ('l', (310, 60))]
    out.append(cw(tail))
    return out


@glyph('R', 560)
def _R():
    x0, x1 = 70, 70 + CSTEM
    junc = 326
    out = [rect(x0, 0, x1, CAP)]
    out += bowl_right(x1, CAP, junc, 456, 62, CBAR, CBAR, x0 + LAP)
    # Graceful flared leg
    leg = Line((266, junc + 18), (420, 0))
    out.append(stroke(leg, CSTEM, 0, junc + 22))
    out += foot(420, 420 + CSTEM, 0, el=22, er=SE - 4)
    out += foot(x0, x1, 0, el=SE, er=SE)
    out += foot(x0, x1, CAP, el=SE, er=16, up=False)
    return out


@glyph('S', 490)
def _S():
    return sshape((246, 542, 160, 178), (242, 184, 184, 194),
                  CSTEM + 4, CHAIR + 2, (28, 206), (28, -160),
                  r_top=33, r_bot=36)


@glyph('T', 520)
def _T():
    x0, x1 = 226, 226 + CSTEM
    out = [rect(x0, 0, x1, CAP), rect(36, CAP - CBAR, 484, CAP)]
    out += armend(36, CAP - CBAR, CAP, down=60, inward=1, brk=56)
    out += armend(484, CAP - CBAR, CAP, down=60, inward=-1, brk=56)
    out += foot(x0, x1, 0, el=SE + 6, er=SE + 6)
    return out


@glyph('U', 570)
def _U():
    # Classical Didone U: thick left stem, thin right stem, clean curved base (no bottom-right spur!)
    l0, l1 = 70, 70 + CSTEM
    r0, r1 = 468, 468 + CHAIR + 10
    out = [rect(l0, 195, l1, CAP), rect(r0, 195, r1, CAP)]
    out += arch(l0, l1, r0, r1, -OVS, CHAIR + 4, 210, 236, sq=2.08, up=False)
    out += foot(l0, l1, CAP, el=SE, er=SE, up=False)
    out += foot(r0, r1, CAP, el=SE, er=SE, up=False)
    return out


@glyph('V', 560)
def _V():
    Lo = Line((46, CAP), (262, 0))
    Li = Lo.shift(CSTEM + 4)
    Ro = Line((514, CAP), (298, 0))
    Ri = Ro.shift(-(CHAIR + 8))
    vx, vy = xsect(Li, Ri)
    out = [poly((46, CAP), (Li.x(CAP), CAP), (vx, vy), (Ri.x(CAP), CAP),
                (514, CAP), (Ro.x(-6), -6), (Lo.x(-6), -6))]
    out += foot(46, Li.x(CAP), CAP, el=SE - 4, er=SE - 4, up=False)
    out += foot(Ri.x(CAP), 514, CAP, el=SE - 4, er=SE - 4, up=False)
    return out


@glyph('W', 780)
def _W():
    return wshape(CAP, -6, 198, 578, (40, 318, 304, 740),
                  CSTEM + 2, CHAIR + 8, SE - 8)


@glyph('X', 540)
def _X():
    A = Line((54, CAP), (420, 0))
    B = Line((456, CAP), (90, 0))
    out = [stroke(A, CSTEM + 4, 0, CAP), stroke(B, CHAIR + 10, 0, CAP)]
    out += foot(54, 54 + CSTEM + 4, CAP, el=SE - 8, er=SE - 8, up=False)
    out += foot(456, 456 + CHAIR + 10, CAP, el=SE - 6, er=SE - 6, up=False)
    out += foot(420, 420 + CSTEM + 4, 0, el=SE - 8, er=SE - 8)
    out += foot(90, 90 + CHAIR + 10, 0, el=SE - 6, er=SE - 6)
    return out


@glyph('Y', 540)
def _Y():
    junc = 304
    Lo = Line((44, CAP), (236, junc))
    Li = Lo.shift(CSTEM + 4)
    Ro = Line((496, CAP), (304, junc))
    Ri = Ro.shift(-(CHAIR + 10))
    out = [rect(236, 0, 236 + CSTEM, junc + 8),
           poly((44, CAP), (Li.x(CAP), CAP), xsect(Li, Ri),
                (Ri.x(CAP), CAP), (496, CAP), (304, junc), (236, junc))]
    out += foot(44, Li.x(CAP), CAP, el=SE - 4, er=SE - 4, up=False)
    out += foot(Ri.x(CAP), 496, CAP, el=SE - 4, er=SE - 4, up=False)
    out += foot(236, 236 + CSTEM, 0, el=SE + 4, er=SE + 4)
    return out


@glyph('Z', 490)
def _Z():
    D = Line((398, CAP - CBAR), (66, CBAR))
    Di = D.shift(CSTEM + 6)
    out = [rect(46, CAP - CBAR, 444, CAP),
           rect(36, 0, 454, CBAR),
           poly((D.x(CAP - CBAR), CAP - CBAR), (D.x(CBAR), CBAR),
                (Di.x(CBAR), CBAR), (Di.x(CAP - CBAR), CAP - CBAR))]
    out += armend(46, CAP - CBAR, CAP, down=52, inward=1, brk=52)
    out += armend(454, 0, CBAR, up=56, inward=-1, brk=54)
    return out


# =========================== LOWERCASE =====================================

@glyph('a', 410)
def _a():
    x0, x1 = 278, 278 + STEM
    out = [rect(x0, 0, x1, 310)]
    # Lower bowl: gentle teardrop resting on baseline
    out += bowl_left(x0, 240, -OVS, 42, STEM - 4, HAIR, HAIR + 2, x1 - LAP)
    # Upper overhanging arch with higher, perched Didone ball terminal
    ar = dict(rxi=96, ryi=116, cxi=180, cyi=304, sq=2.06, sqi=2.00)
    out.append(band(188, 304, 148, 150, 0, 166, **ar))
    o, i = band_ends(188, 304, 148, 150, 166, **ar)
    out.append(oval((o[0] + i[0]) / 2.0 + 12, (o[1] + i[1]) / 2.0 + 2, 31, 30, sq=2.1))
    # Refined outward foot serif
    out += foot(x0, x1, 0, el=0, er=SL)
    return out


@glyph('b', 430)
def _b():
    x0, x1 = 60, 60 + STEM
    out = [rect(x0, 0, x1, ASC)]
    out += bowl_right(x1, XH + OVS, -OVS, 396, STEM, HAIR + 2, HAIR + 2, x0 + LAP)
    out += foot(x0, x1, 0, el=SL - 6, er=12)
    out += head_serif(x0, x1, ASC)
    return out


@glyph('c', 380)
def _c():
    return cshape(204, XH / 2.0, 168, XH / 2.0 + OVS, STEM, HAIR + 2,
                  52, 314, r_top=30, sq=2.05)


@glyph('d', 430)
def _d():
    x0, x1 = 308, 308 + STEM
    out = [rect(x0, 0, x1, ASC)]
    out += bowl_left(x0, XH + OVS, -OVS, 30, STEM, HAIR + 2, HAIR + 2, x1 - LAP)
    out += foot(x0, x1, 0, el=12, er=SL)
    out += head_serif(x0, x1, ASC)
    return out


@glyph('e', 380)
def _e():
    cx, cy, rx, ry = 196, XH / 2.0, 168, XH / 2.0 + OVS
    bar_t = 258
    kw = dict(wside=STEM, wend=HAIR + 2, sq=2.06, sqi=2.00)
    t0 = math.degrees(math.asin((bar_t - cy) / ry))
    # Crossbar inset cleanly inside left & right walls (no protruding ears!)
    x_bar_r = ept(cx, cy, rx, ry, t0, 2.06)[0]
    x_bar_l = cx - rx + LAP
    out = [band(cx, cy, rx, ry, t0, 316, **kw),
           rect(x_bar_l, bar_t - LBAR, x_bar_r, bar_t)]
    o, i = band_ends(cx, cy, rx, ry, 316, **kw)
    out.append(poly(o, (o[0] + 16, o[1] + 6), (i[0] + 10, i[1] + 12), i))
    return out


@glyph('f', 300)
def _f():
    x0, x1 = 96, 96 + STEM
    hk = dict(rxi=42, ryi=146, cxi=204, cyi=566, sq=2.04, sqi=2.00)
    out = [rect(x0, 0, x1, 576),
           band(188, 566, 92, 174, 180, 10, **hk)]
    o, i = band_ends(188, 566, 92, 174, 10, **hk)
    out.append(oval((o[0] + i[0]) / 2.0 + 4, (o[1] + i[1]) / 2.0 - 4, 30, 29, sq=2.1))
    out.append(rect(24, XH - LBAR, 250, XH))
    out += foot(x0, x1, 0, el=SL, er=SL)
    return out


@glyph('g', 420)
def _g():
    # Classic literary binocular g: crisp upper oval, delicate curved ear,
    # slim S-link neck, and closed lower loop!
    out = list(ring(196, 304, 134, 150, STEM - 6, HAIR, sq=2.04))
    # Delicate ear at upper right with tiny ball tip
    out.append(poly((292, 412), (374, 444), (378, 418), (310, 384)))
    out.append(oval(376, 430, 22, 21, sq=2.1))
    # Graceful neck descending from lower-left of upper bowl cleanly into lower loop
    neck = [('m', (118, 184)),
            ('c', (78, 138), (74, 84), (118, 48)),
            ('l', (154, 66)),
            ('c', (116, 92), (114, 134), (148, 168)),
            ('l', (118, 184))]
    out.append(cw(neck))
    # Closed horizontal lower loop below baseline
    out += ring(206, -66, 168, 132, STEM - 6, HAIR + 2, sq=2.08)
    return out


@glyph('h', 430)
def _h():
    l0, l1 = 60, 60 + STEM
    r0, r1 = 308, 308 + STEM
    out = [rect(l0, 0, l1, ASC), rect(r0, 0, r1, 286)]
    out += arch(l0, l1, r0, r1, XH + OVS, HAIR + 2, 266, 232)
    out += foot(l0, l1, 0, el=SL, er=SL)
    out += foot(r0, r1, 0, el=SL, er=SL)
    out += head_serif(l0, l1, ASC)
    return out


@glyph('dotlessi', 240)
def _dotlessi():
    x0, x1 = 91, 91 + STEM
    out = [rect(x0, 0, x1, XH)]
    out += foot(x0, x1, 0, el=SL, er=SL)
    out += head_serif(x0, x1, XH)
    return out


@glyph('i', 240)
def _i():
    return _dotlessi() + dot(120, XH + 124, 34)


@glyph('j', 250)
def _j():
    x0, x1 = 104, 104 + STEM
    # Smooth sweeping descender hook ending in a Didone ball terminal
    cx, cy, rx, ry = 54, -54, 108, 146
    hk = dict(rxi=52, ryi=124, cxi=52, cyi=-54, sq=2.04, sqi=2.00)
    out = [rect(x0, -64, x1, XH),
           band(cx, cy, rx, ry, 0, -130, **hk)]
    o, i = band_ends(cx, cy, rx, ry, -130, **hk)
    out.append(oval((o[0] + i[0]) / 2.0 + 2, (o[1] + i[1]) / 2.0 + 10, 30, 28, sq=2.1))
    out += head_serif(x0, x1, XH)
    out += dot(x0 + STEM / 2.0, XH + 124, 34)
    return out


@glyph('k', 420)
def _k():
    x0, x1 = 60, 60 + STEM
    out = [rect(x0, 0, x1, ASC)]
    out += kshape(x0, XH, 378, HAIR + 12, STEM, 392, 196, SL - 6)
    out += foot(x0, x1, 0, el=SL, er=SL)
    out += head_serif(x0, x1, ASC)
    return out


@glyph('l', 240)
def _l():
    x0, x1 = 91, 91 + STEM
    out = [rect(x0, 0, x1, ASC)]
    out += foot(x0, x1, 0, el=SL, er=SL)
    out += head_serif(x0, x1, ASC)
    return out


@glyph('m', 660)
def _m():
    a0, a1 = 60, 60 + STEM
    b0, b1 = 300, 300 + STEM
    c0, c1 = 540, 540 + STEM
    out = [rect(a0, 0, a1, XH), rect(b0, 0, b1, 286), rect(c0, 0, c1, 286)]
    out += arch(a0, a1, b0, b1, XH + OVS, HAIR + 2, 266, 232)
    out += arch(b0, b1, c0, c1, XH + OVS, HAIR + 2, 266, 232)
    for x0, x1 in ((a0, a1), (b0, b1), (c0, c1)):
        out += foot(x0, x1, 0, el=SL - 4, er=SL - 4)
    out += head_serif(a0, a1, XH)
    return out


@glyph('n', 430)
def _n():
    l0, l1 = 60, 60 + STEM
    r0, r1 = 308, 308 + STEM
    out = [rect(l0, 0, l1, XH), rect(r0, 0, r1, 286)]
    out += arch(l0, l1, r0, r1, XH + OVS, HAIR + 2, 266, 232)
    out += foot(l0, l1, 0, el=SL, er=SL)
    out += foot(r0, r1, 0, el=SL, er=SL)
    out += head_serif(l0, l1, XH)
    return out


@glyph('o', 410)
def _o():
    return ring(205, XH / 2.0, 174, XH / 2.0 + OVS, STEM + 2, HAIR + 2)


@glyph('p', 430)
def _p():
    x0, x1 = 60, 60 + STEM
    out = [rect(x0, DESC, x1, XH)]
    out += bowl_right(x1, XH + OVS, -OVS, 396, STEM, HAIR + 2, HAIR + 2, x0 + LAP)
    out += foot(x0, x1, DESC, el=SL, er=SL)
    out += head_serif(x0, x1, XH)
    return out


@glyph('q', 430)
def _q():
    x0, x1 = 308, 308 + STEM
    out = [rect(x0, DESC, x1, XH)]
    out += bowl_left(x0, XH + OVS, -OVS, 30, STEM, HAIR + 2, HAIR + 2, x1 - LAP)
    out += foot(x0, x1, DESC, el=SL, er=SL)
    return out


@glyph('r', 310)
def _r():
    x0, x1 = 60, 60 + STEM
    # Smooth rising shoulder into lush Didone ball terminal
    sh = dict(rxi=48, ryi=146, cxi=178, cyi=274, sq=2.04, sqi=2.00)
    out = [rect(x0, 0, x1, XH),
           band(166, 274, 102, 180, 180, 34, **sh)]
    o, i = band_ends(166, 274, 102, 180, 34, **sh)
    out.append(oval((o[0] + i[0]) / 2.0 + 4, (o[1] + i[1]) / 2.0 - 10, 35, 34, sq=2.1))
    out += foot(x0, x1, 0, el=SL, er=SL)
    out += head_serif(x0, x1, XH)
    return out


@glyph('s', 340)
def _s():
    return sshape((172, 340, 114, 115), (168, 120, 128, 128),
                  STEM + 4, HAIR, (26, 206), (26, -160),
                  r_top=25, r_bot=27)


@glyph('t', 290)
def _t():
    x0, x1 = 76, 76 + STEM
    tl = dict(rxi=44, ryi=108, cxi=192, cyi=138, sq=2.06, sqi=2.00)
    out = [rect(x0, 126, x1, XH + 140),
           band(178, 138, 102, 146, 180, 326, **tl)]
    o, i = band_ends(178, 138, 102, 146, 326, **tl)
    out.append(poly(o, (o[0] + 18, o[1] + 12), (i[0] + 10, i[1] + 20), i))
    out.append(rect(22, XH - LBAR, 256, XH))
    return out


@glyph('u', 430)
def _u():
    l0, l1 = 60, 60 + STEM
    r0, r1 = 308, 308 + STEM
    # Left stem curves cleanly into arch; right stem descends to baseline with outward foot only
    out = [rect(l0, 154, l1, XH), rect(r0, 0, r1, XH)]
    out += arch(l0, l1, r0, r1, -OVS, HAIR + 2, 168, 198, sq=2.08, up=False)
    out += head_serif(l0, l1, XH)
    out += head_serif(r0, r1, XH)
    out += foot(r0, r1, 0, el=0, er=SL)
    return out


@glyph('v', 390)
def _v():
    Lo = Line((32, XH), (178, 0))
    Li = Lo.shift(STEM + 2)
    Ro = Line((358, XH), (212, 0))
    Ri = Ro.shift(-(HAIR + 6))
    out = [poly((32, XH), (Li.x(XH), XH), xsect(Li, Ri), (Ri.x(XH), XH),
                (358, XH), (Ro.x(-6), -6), (Lo.x(-6), -6))]
    out += foot(32, Li.x(XH), XH, el=SL - 6, er=SL - 6, up=False)
    out += foot(Ri.x(XH), 358, XH, el=SL - 6, er=SL - 6, up=False)
    return out


@glyph('w', 560)
def _w():
    return wshape(XH, -6, 146, 414, (28, 232, 220, 532),
                  STEM, HAIR + 6, SL - 10)


@glyph('x', 390)
def _x():
    A = Line((38, XH), (294, 0))
    B = Line((326, XH), (70, 0))
    out = [stroke(A, STEM + 2, 0, XH), stroke(B, HAIR + 8, 0, XH)]
    out += foot(38, 38 + STEM + 2, XH, el=SL - 8, er=SL - 8, up=False)
    out += foot(326, 326 + HAIR + 8, XH, el=SL - 6, er=SL - 6, up=False)
    out += foot(294, 294 + STEM + 2, 0, el=SL - 8, er=SL - 8)
    out += foot(70, 70 + HAIR + 8, 0, el=SL - 6, er=SL - 6)
    return out


@glyph('y', 390)
def _y():
    Lo = Line((30, XH), (174, 0))
    Li = Lo.shift(STEM + 2)
    Ro = Line((360, XH), (176, -138))
    Ri = Ro.shift(-(HAIR + 6))
    out = [poly((30, XH), (Li.x(XH), XH), xsect(Li, Ri), (Ri.x(XH), XH),
                (360, XH), (Ro.x(-110), -110), (Lo.x(-6), -6))]
    # Smooth poetic tail curving into a ball terminal
    cx = Ro.x(-102) - 72
    cy = -102
    tl = dict(rxi=48, ryi=66, cxi=cx - 2, cyi=cy, sq=2.06, sqi=2.00)
    out.append(band(cx, cy, 74, 90, 0, -135, **tl))
    o, i = band_ends(cx, cy, 74, 90, -135, **tl)
    out.append(oval((o[0] + i[0]) / 2.0 + 4, (o[1] + i[1]) / 2.0 + 8, 29, 28, sq=2.1))
    out += foot(30, Li.x(XH), XH, el=SL - 6, er=SL - 6, up=False)
    out += foot(Ri.x(XH), 360, XH, el=SL - 6, er=SL - 6, up=False)
    return out


@glyph('z', 360)
def _z():
    D = Line((284, XH - LBAR), (52, LBAR))
    Di = D.shift(STEM + 4)
    out = [rect(38, XH - LBAR, 326, XH),
           rect(30, 0, 334, LBAR),
           poly((D.x(XH - LBAR), XH - LBAR), (D.x(LBAR), LBAR),
                (Di.x(LBAR), LBAR), (Di.x(XH - LBAR), XH - LBAR))]
    out += armend(38, XH - LBAR, XH, down=38, inward=1, brk=40)
    out += armend(334, 0, LBAR, up=40, inward=-1, brk=42)
    return out


# =========================== FIGURES (Full FIG=695) ========================

@glyph('zero', 480)
def _zero():
    return ring(240, FIG / 2.0, 202, FIG / 2.0 + OVS, CSTEM, CHAIR + 2)


@glyph('one', 380)
def _one():
    x0, x1 = 156, 156 + CSTEM
    out = [rect(x0, 0, x1, FIG)]
    out.append(poly((x0 + LAP, FIG), (x0 + LAP, FIG - 78),
                    (66, FIG - 122), (66, FIG - 94)))
    out += foot(x0, x1, 0, el=84, er=84)
    return out


@glyph('two', 460)
def _two():
    # Full FIG=695 height! Upper Didone arch with ball terminal + crisp sweep to baseline
    cx, cy, rx, ry = 232, 518, 168, 186
    tp = dict(wside=CSTEM, wend=CHAIR + 2, sq=2.04, sqi=2.00)
    out = [band(cx, cy, rx, ry, 178, -14, **tp)]
    o, i = band_ends(cx, cy, rx, ry, 178, **tp)
    out.append(oval((o[0] + i[0]) / 2.0 + 6, (o[1] + i[1]) / 2.0 - 6, 34, 33, sq=2.1))
    # Smooth tapered diagonal sweeping down from right arc to bottom-left
    diag = [('m', (398, 496)),
            ('c', (394, 384), (272, 240), (124, 56)),
            ('l', (54, 56)),
            ('l', (54, 84)),
            ('c', (188, 224), (326, 370), (334, 496)),
            ('l', (398, 496))]
    out.append(cw(diag))
    out.append(rect(54, 0, 412, 34))
    out += armend(412, 0, 34, up=52, inward=-1, brk=46)
    return out


@glyph('three', 460)
def _three():
    # Full FIG=695 height! Upper bowl 356..705, lower bowl -10..374
    kw = dict(wside=CSTEM, wend=CHAIR + 2, sq=2.04, sqi=2.00)
    out = [
        band(234, 534, 158, 170, 178, -86, **kw),
        band(226, 186, 184, 196, 86, -184, **kw),
    ]
    # Crisp horizontal waist tie
    out.append(rect(182, 356, 260, 382))
    # Upper and lower ball terminals
    o, i = band_ends(234, 534, 158, 170, 178, **kw)
    out.append(oval((o[0] + i[0]) / 2.0 + 6, (o[1] + i[1]) / 2.0 - 4, 31, 30, sq=2.1))
    o, i = band_ends(226, 186, 184, 196, -184, **kw)
    out.append(oval((o[0] + i[0]) / 2.0 + 8, (o[1] + i[1]) / 2.0 + 6, 35, 34, sq=2.1))
    return out


@glyph('four', 460)
def _four():
    x0, x1 = 278, 278 + CSTEM
    bar_y = 186
    # Diagonal left side meeting top of stem cleanly (thin stroke -> counter stays crisp!)
    D = Line((x0 + 18, FIG), (40, bar_y))
    out = [rect(x0, 0, x1, FIG),
           rect(40, bar_y, 424, bar_y + CBAR),
           stroke(D, CHAIR + 10, bar_y, FIG)]
    out += foot(x0, x1, 0, el=52, er=52)
    return out


@glyph('five', 460)
def _five():
    # Full FIG=695 height: crisp top bar + clean vertical drop seamlessly meeting bowl
    bw = dict(wside=CSTEM, wend=CHAIR + 2, sq=2.04, sqi=2.00)
    top_bar = 30
    out = [
        band(226, 210, 180, 220, 134, -178, **bw),
        rect(96, FIG - top_bar, 386, FIG),
        rect(96, 360, 96 + CHAIR + 10, FIG),
    ]
    o, i = band_ends(226, 210, 180, 220, -178, **bw)
    out.append(oval((o[0] + i[0]) / 2.0 + 6, (o[1] + i[1]) / 2.0 + 6, 34, 33, sq=2.1))
    out += armend(386, FIG - top_bar, FIG, down=34, inward=-1, brk=38)
    return out


@glyph('six', 460)
def _six():
    # Full FIG=695 height: full oval bowl + graceful arching spine with lush ball terminal
    out = list(ring(234, 214, 180, 224, CSTEM, CHAIR + 2, sq=2.04))
    ha = dict(rxi=210 - CSTEM, ryi=286 - (CHAIR + 4), sq=2.04, sqi=2.00)
    out.append(band(264, 418, 210, 286, 46, 186, **ha))
    o, i = band_ends(264, 418, 210, 286, 46, **ha)
    out.append(oval((o[0] + i[0]) / 2.0 - 4, (o[1] + i[1]) / 2.0 - 10, 35, 34, sq=2.1))
    return out


@glyph('seven', 450)
def _seven():
    # Clean perimeter-ordered polygon (no bow-tie!)
    out = [
        rect(44, FIG - 34, 412, FIG),
        poly((412, FIG), (376, FIG), (144, 0), (218, 0)),
    ]
    out += armend(44, FIG - 34, FIG, down=52, inward=1, brk=48)
    out += foot(144, 218, 0, el=24, er=24)
    return out


@glyph('eight', 460)
def _eight():
    # Overlapping upper & lower rings so waist merges smoothly (no floating snowman!)
    out = list(ring(230, 524, 148, 180, CSTEM - 8, CHAIR + 2, sq=2.04))
    out += ring(230, 186, 178, 196, CSTEM, CHAIR + 2, sq=2.04)
    return out


@glyph('nine', 460)
def _nine():
    # Exact 180-degree rotation of six - guaranteed harmony!
    return [flipy(flipx(c, 234), FIG / 2.0) for c in _six()]


# =========================== PUNCTUATION & SYMBOLS =========================

@glyph('period', 200)
def _period():
    return dot(100, 42, 42)


@glyph('comma', 210)
def _comma():
    return comma_shape(106, 46, 42)


@glyph('colon', 220)
def _colon():
    return dot(110, 42, 42) + dot(110, XH - 42, 42)


@glyph('semicolon', 220)
def _semicolon():
    return comma_shape(110, 46, 42) + dot(110, XH - 42, 42)


@glyph('exclam', 250)
def _exclam():
    return [poly((92, CAP), (158, CAP), (138, 178), (112, 178))] + dot(125, 42, 42)


@glyph('question', 420)
def _question():
    qa = dict(wside=CSTEM - 4, wend=CHAIR + 2, sq=2.04, sqi=2.00)
    out = [band(210, 540, 152, 176, 184, -48, **qa)]
    # Ball terminal on left tip
    o, i = band_ends(210, 540, 152, 176, 184, **qa)
    out.append(oval((o[0] + i[0]) / 2.0 + 6, (o[1] + i[1]) / 2.0 - 4, 30, 29, sq=2.1))
    # Smooth curved neck dropping straight into the dot stem
    neck = [('m', (314, 412)),
            ('c', (264, 356), (222, 314), (222, 180)),
            ('l', (194, 180)),
            ('c', (194, 326), (234, 378), (282, 434)),
            ('l', (314, 412))]
    out.append(cw(neck))
    out += dot(208, 42, 42)
    return out


@glyph('quotesingle', 190)
def _quotesingle():
    return [poly((68, CAP), (122, CAP), (108, CAP - 190), (82, CAP - 190))]


@glyph('quotedbl', 320)
def _quotedbl():
    return [poly((58, CAP), (112, CAP), (98, CAP - 190), (72, CAP - 190)),
            poly((208, CAP), (262, CAP), (248, CAP - 190), (222, CAP - 190))]


@glyph('quoteright', 210)
def _quoteright():
    return comma_shape(106, CAP - 46, 40)


@glyph('quoteleft', 210)
def _quoteleft():
    return [flipy(flipx(c, 106), CAP - 76) for c in comma_shape(106, CAP - 46, 40)]


@glyph('quotedblright', 360)
def _quotedblright():
    return comma_shape(104, CAP - 46, 38) + comma_shape(256, CAP - 46, 38)


@glyph('quotedblleft', 360)
def _quotedblleft():
    return [flipy(flipx(c, 180), CAP - 76) for c in _quotedblright()]


@glyph('hyphen', 300)
def _hyphen():
    return [rect(36, XH / 2.0 - 12, 264, XH / 2.0 + 12)]


@glyph('endash', 480)
def _endash():
    return [rect(30, XH / 2.0 - 12, 450, XH / 2.0 + 12)]


@glyph('emdash', 760)
def _emdash():
    return [rect(20, XH / 2.0 - 12, 740, XH / 2.0 + 12)]


@glyph('ellipsis', 580)
def _ellipsis():
    return dot(90, 42, 42) + dot(290, 42, 42) + dot(490, 42, 42)


@glyph('parenleft', 290)
def _parenleft():
    return [band(320, 265, 250, 465, 114, 246, wside=50, wend=24, sq=2.0)]


@glyph('parenright', 290)
def _parenright():
    return [flipx(c, 145) for c in _parenleft()]


@glyph('bracketleft', 280)
def _bracketleft():
    return [rect(80, -165, 80 + 44, CAP + 10),
            rect(80, CAP - 16, 234, CAP + 10),
            rect(80, -165, 234, -139)]


@glyph('bracketright', 280)
def _bracketright():
    return [flipx(c, 140) for c in _bracketleft()]


@glyph('braceleft', 340)
def _braceleft():
    # Seamless welded vertical stem + four overlapping quarter-arcs (no middle gap!)
    w = 42
    return [
        band(268, 492, 168, 228, 180, 92, rxi=168 - w, ryi=228 - w),
        band(268, 38, 168, 228, 180, 268, rxi=168 - w, ryi=228 - w),
        band(-18, 492, 160, 232, 0, -90, rxi=160 - w, ryi=232 - w),
        band(-18, 38, 160, 232, 0, 90, rxi=160 - w, ryi=232 - w),
        rect(100, 480, 142, 504),
        rect(100, 26, 142, 50),
    ]


@glyph('braceright', 340)
def _braceright():
    return [flipx(c, 170) for c in _braceleft()]


@glyph('slash', 320)
def _slash():
    return [poly((26, -30), (242, CAP + 15), (294, CAP + 15), (78, -30))]


@glyph('backslash', 320)
def _backslash():
    return [flipx(c, 160) for c in _slash()]


@glyph('bar', 200)
def _bar():
    return [rect(82, -170, 118, CAP + 20)]


@glyph('underscore', 460)
def _underscore():
    return [rect(0, -135, 460, -108)]


@glyph('ampersand', 640)
def _ampersand():
    # Classic high-contrast literary ampersand with cleanly joined tail
    out = list(ring(236, 526, 110, 118, 54, 24, sq=2.04))
    out.append(band(248, 204, 184, 206, 26, 316, wside=68, wend=26, sq=2.04))
    out.append(stroke(Line((176, 470), (438, 0)), 66, 0, 470))
    out.append(stroke(Line((428, 18), (566, 276)), 38, 18, 276))
    return out


@glyph('at', 800)
def _at():
    out = ring(400, 290, 360, 356, 44, 34, sq=2.06)
    inner = scaled(_a(), 0.64, 0.64, 205, 222)
    return out + moveall(inner, 400 - 205, 290 - 222)


@glyph('numbersign', 500)
def _numbersign():
    return [
        poly((126, 0), (170, 0), (284, FIG), (240, FIG)),
        poly((292, 0), (336, 0), (450, FIG), (406, FIG)),
        rect(48, 212, 442, 244),
        rect(74, 424, 468, 456),
    ]


@glyph('dollar', 490)
def _dollar():
    return _S() + [rect(232, -68, 260, CAP + 46)]


@glyph('percent', 720)
def _percent():
    out = ring(168, 534, 128, 152, 44, 24, sq=2.04)
    out += ring(552, 162, 128, 152, 44, 24, sq=2.04)
    out.append(poly((488, FIG + 8), (540, FIG + 8), (232, -16), (180, -16)))
    return out


@glyph('asterisk', 400)
def _asterisk():
    out = []
    cx, cy, r = 200, 540, 146
    for i in range(5):
        a = math.radians(90 + i * 72)
        tip = (cx + r * math.cos(a), cy + r * math.sin(a))
        b = (cx + 28 * math.cos(a + 1.6), cy + 28 * math.sin(a + 1.6))
        c = (cx + 28 * math.cos(a - 1.6), cy + 28 * math.sin(a - 1.6))
        out.append(poly(tip, b, c))
    out.append(oval(cx, cy, 40, 40))
    return out


@glyph('plus', 480)
def _plus():
    cx, cy = 240, 290
    return [rect(cx - 170, cy - 16, cx + 170, cy + 16),
            rect(cx - 16, cy - 170, cx + 16, cy + 170)]


@glyph('equal', 480)
def _equal():
    return [rect(70, 206, 410, 238),
            rect(70, 342, 410, 374)]


@glyph('less', 480)
def _less():
    return [poly((418, 464), (418, 424), (116, 290), (418, 156), (418, 116),
                 (62, 272), (62, 308))]


@glyph('greater', 480)
def _greater():
    return [flipx(c, 240) for c in _less()]


@glyph('asciicircum', 420)
def _asciicircum():
    return [poly((40, 420), (196, CAP), (224, CAP), (380, 420),
                 (334, 420), (210, 634), (86, 420))]


@glyph('asciitilde', 480)
def _asciitilde():
    return [band(148, 276, 94, 72, 180, 0, rxi=94 - 36, ryi=72 - 32),
            band(332, 314, 94, 72, 180, 360, rxi=94 - 36, ryi=72 - 32)]


@glyph('space', 230)
def _space():
    return []


# ---------------------------------------------------------------------------
# Accents (drawn in standard standalone range 540..700; composites shift them)
# ---------------------------------------------------------------------------

@glyph('grave', 280)
def _grave():
    return [poly((46, 686), (118, 686), (222, 540), (174, 540))]


@glyph('acute', 280)
def _acute():
    return [poly((162, 686), (234, 686), (106, 540), (58, 540))]


@glyph('circumflex', 300)
def _circumflex():
    return [poly((150, 696), (264, 546), (212, 546), (150, 634),
                 (88, 546), (36, 546))]


@glyph('tilde', 300)
def _tilde():
    return [band(92, 594, 64, 48, 180, 0, rxi=64 - 28, ryi=48 - 26),
            band(208, 616, 64, 48, 180, 360, rxi=64 - 28, ryi=48 - 26)]


@glyph('dieresis', 300)
def _dieresis():
    return dot(86, 620, 36) + dot(214, 620, 36)


@glyph('ring', 280)
def _ring():
    return ring(140, 612, 66, 66, 22, 22, sq=2.02)


@glyph('cedilla', 240)
def _cedilla():
    out = [rect(108, -76, 134, 8),
           band(120, -112, 62, 52, 92, -148, wside=28, wend=22, sq=2.04)]
    return out


# ---------------------------------------------------------------------------
# Sidebearings (Measured to Ink for Airy, Literary Rhythm)
# ---------------------------------------------------------------------------

F.sidebearings.update({
    'A': (14, 14), 'B': (30, 24), 'C': (24, 20), 'D': (30, 24), 'E': (30, 22),
    'F': (30, 18), 'G': (24, 26), 'H': (30, 30), 'I': (28, 28), 'J': (18, 28),
    'K': (30, 16), 'L': (30, 20), 'M': (26, 28), 'N': (28, 28), 'O': (24, 24),
    'P': (30, 22), 'Q': (24, 24), 'R': (30, 18), 'S': (24, 24), 'T': (16, 16),
    'U': (26, 26), 'V': (14, 14), 'W': (14, 14), 'X': (16, 16), 'Y': (14, 14),
    'Z': (24, 24),
    'a': (22, 22), 'b': (26, 22), 'c': (22, 18), 'd': (22, 26), 'e': (22, 18),
    'f': (16, 12), 'g': (22, 20), 'h': (26, 24), 'i': (24, 24), 'j': (16, 24),
    'k': (26, 16), 'l': (24, 24), 'm': (26, 26), 'n': (26, 24), 'o': (22, 22),
    'p': (26, 22), 'q': (22, 26), 'r': (26, 14), 's': (22, 22), 't': (16, 18),
    'u': (24, 24), 'v': (14, 14), 'w': (14, 14), 'x': (16, 16), 'y': (14, 14),
    'z': (22, 22),
    'dotlessi': (24, 24),
    'zero': (28, 28), 'one': (32, 32), 'two': (24, 24), 'three': (24, 24),
    'four': (22, 24), 'five': (24, 24), 'six': (26, 24), 'seven': (22, 22),
    'eight': (26, 26), 'nine': (24, 26),
    'period': (42, 42), 'comma': (42, 42), 'colon': (44, 44), 'semicolon': (44, 44),
    'exclam': (44, 44), 'question': (26, 26),
    'parenleft': (34, 18), 'parenright': (18, 34),
    'bracketleft': (36, 18), 'bracketright': (18, 36),
    'braceleft': (30, 18), 'braceright': (18, 30),
    'ampersand': (24, 24), 'at': (24, 24), 'dollar': (24, 24), 'percent': (24, 24),
})

F.accents.update({
    'A': 'grave acute circumflex tilde dieresis ring',
    'E': 'grave acute circumflex dieresis',
    'I': 'grave acute circumflex dieresis',
    'O': 'grave acute circumflex tilde dieresis',
    'U': 'grave acute circumflex dieresis',
    'C': 'cedilla',
    'N': 'tilde',
    'a': 'grave acute circumflex tilde dieresis ring',
    'e': 'grave acute circumflex dieresis',
    'i': 'grave acute circumflex dieresis',
    'o': 'grave acute circumflex tilde dieresis',
    'u': 'grave acute circumflex dieresis',
    'c': 'cedilla',
    'n': 'tilde',
})

F.kern += [
    ("A", "V W Y T v w y", -55),
    ("A", "C G O Q", -22),
    ("V", "A a e o c r u", -62),
    ("W", "A a e o c r u", -48),
    ("Y", "A a e o c r u", -64),
    ("T", "A a e o c r s u w y", -60),
    ("P", "A a e o", -42),
    ("F", "A a e o r", -45),
    ("K", "O C G e o", -26),
    ("L", "T V W Y", -52),
    ("f", "i l f", -12),
    ("r", "a e o c d g q", -20),
    ("v", "a e o", -24),
    ("w", "a e o", -20),
    ("y", "a e o", -24),
]


if __name__ == "__main__":
    sys.exit(F.cli())
