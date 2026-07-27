"""Draw "Gravitas Text" - a serious transitional serif - straight to a .ttf.

No glyph sheet, no tracing: every outline is constructed here from stems, arcs
and bracketed serifs, then welded by FontForge's removeOverlap.

Runs under fontforge\\bin\\ffpython.exe.

Design brief: Times-adjacent gravity, but tuned for reading rather than for
1932 newsprint economy - taller x-height, lower stroke contrast, sturdier
hairlines, more open apertures, slightly wider set.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from glyphlib import (rect, poly, oval, band, band_ends, bracket, ept,
                      Line, xsect, stroke, rev, cw, ccw, hole, arc,
                      move, moveall, flipx, flipy, bbox)
from fontbuild import Font

# How far pieces reach into each other at a join. Everything here is built by
# unioning overlapping parts, and FontForge's overlap removal falls apart on
# exactly coincident or tangent edges - so joins are always buried this far
# inside the piece they land on, never laid flush against it.
LAP = 8

# ---------------------------------------------------------------------------
# vertical metrics
# ---------------------------------------------------------------------------
EM = 1000
ASCENT = 800          # em box split; ascender letters do not use all of it
DESCENT = 200

CAP = 680             # cap height
XH = 492              # x-height - generous, this is a reading face
ASC = 712             # b d f h k l
DESC = -214           # g j p q y
FIG = 666             # lining figures, a touch under cap height
OVS = 9               # round overshoot

# ---------------------------------------------------------------------------
# weights
# ---------------------------------------------------------------------------
CSTEM = 100           # cap stem
CHAIR = 44            # cap hairline
CBAR = 56             # cap horizontal arm

STEM = 88             # lowercase stem
HAIR = 38             # lowercase hairline
LBAR = 50             # lowercase arm / crossbar

TIP = 34              # serif slab thickness at the tip
BRK = 74              # height the bracket climbs the stem
SE = 52               # cap serif projection
SL = 46               # lowercase serif projection

SQ = 2.06             # roundness of bowls (2 = ellipse, higher = squarer)
SQI = 2.02


# ---------------------------------------------------------------------------
# shared constructions
# ---------------------------------------------------------------------------

def foot(x0, x1, y=0, el=SL, er=SL, up=True, tip=TIP, brk=BRK):
    """Bracketed slab serif across a stem spanning x0..x1, sitting at y."""
    d = 1 if up else -1
    parts = [rect(x0 - el, y, x1 + er, y + d * tip)]
    if el:
        parts.append(bracket(x0, y + d * tip, -el * 0.66, d * (brk - tip)))
    if er:
        parts.append(bracket(x1, y + d * tip, er * 0.66, d * (brk - tip)))
    return parts


def armend(x, y0, y1, down=0, up=0, inward=1, tip=TIP, brk=BRK):
    """Terminal serif closing a horizontal arm that spans y0..y1 in y.

    x is the outer edge of the arm; inward is +1 for a left-hand terminal.
    """
    parts = [rect(x, y0 - down, x + inward * tip, y1 + up)]
    if down:
        parts.append(bracket(x + inward * tip, y0, inward * (brk - tip), -down))
    if up:
        parts.append(bracket(x + inward * tip, y1, inward * (brk - tip), up))
    return parts


def bowl_right(xj, ytop, ybot, xout, wside, wtop, wbot, xattach, sq=SQ):
    """Half-bowl springing right off a stem, as in B D P R b p.

    Drawn as one C-shaped contour whose open side is buried inside the stem,
    so the counter falls out of the union instead of being stated.
    """
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
    """Mirror of bowl_right, as in d q."""
    parts = bowl_right(0, ytop, ybot, xj - xout, wside, wtop, wbot,
                       xj - xattach, sq=sq)
    return moveall([flipx(c, 0) for c in parts], xj, 0)


def arch(lx0, lx1, rx0, rx1, yext, wend, yjo, yji, sq=SQ, up=True):
    """Shoulder linking two stems: n m h (up) and u (down).

    yext is the crest, wend its thickness there; yjo / yji are where the outer
    and inner curves die into the stems. The radii carry the sign, so a down
    arch is the same construction upside-down rather than a mirrored copy.
    """
    s = 1 if up else -1
    cx = (lx0 + rx1) / 2.0
    cxi = (lx1 + rx0) / 2.0
    rx = (rx1 - lx0) / 2.0 - LAP        # outer curve dies inside the stems
    rxi = (rx0 - lx1) / 2.0 + LAP       # inner curve does too, the other way
    ry = yext - yjo
    ryi = yext - s * wend - yji
    return [band(cx, yjo, rx, ry, 180, 0, rxi=rxi, ryi=ryi, cxi=cxi, cyi=yji,
                 sq=sq, sqi=SQI)]


def beak(o, i, dx, dy, dx2=None):
    """Wedge terminal grown off a band end, from outer point o to inner i."""
    if dx2 is None:
        dx2 = dx * 1.15
    return poly(o, (o[0] + dx, o[1] + dy), (o[0] + dx2, o[1] - dy * 0.75), i)


def dot(cx, cy, r):
    return [oval(cx, cy, r, r, sq=2.25)]


def ring(cx, cy, rx, ry, wside, wend, sq=SQ):
    return [oval(cx, cy, rx, ry, sq=sq),
            hole(oval(cx, cy, rx - wside, ry - wend, sq=SQI))]


def comma(cx, cy, s):
    """Teardrop comma / quote, hanging below cy. s is the ball radius."""
    ball = oval(cx, cy, s, s, sq=2.3)
    tail = [('m', (cx - s * 0.15, cy + s * 0.35)),
            ('c', (cx + s * 0.95, cy - s * 0.2), (cx + s * 0.30, cy - s * 1.6),
             (cx - s * 1.05, cy - s * 2.5)),
            ('c', (cx - s * 0.55, cy - s * 1.5), (cx - s * 0.85, cy - s * 0.7),
             (cx - s * 0.95, cy - s * 0.1)),
            ('l', (cx - s * 0.15, cy + s * 0.35))]
    return [ball, cw(tail)]


def cshape(cx, cy, rx, ry, wside, wend, t0, t1, bk=1.0, sq=SQ):
    """C / c / e-family arc with a beak at each end."""
    kw = dict(wside=wside, wend=wend, sq=sq, sqi=SQI)
    out = [band(cx, cy, rx, ry, t0, t1, **kw)]
    o, i = band_ends(cx, cy, rx, ry, t0, **kw)
    out.append(beak(o, i, 30 * bk, 26 * bk))
    o, i = band_ends(cx, cy, rx, ry, t1, **kw)
    out.append(poly(o, (o[0] + 42 * bk, o[1] + 4),
                    (o[0] + 32 * bk, o[1] + 42 * bk), i))
    return out


def kshape(x0, top, armtip, armw, legw, legfoot, cut, serif):
    """Stem plus a thin upper arm, and a thick leg branching off that arm.

    The leg is cut flat well above the branch and simply buried in the arm and
    the stem: letting the union hide the joinery is far more robust than
    stating the junction polygon exactly.
    """
    arm = poly((x0 + 56, cut + 78), (armtip - armw, top), (armtip, top),
               (x0 + 56, cut))
    leg = Line((x0 + 104, cut + 26), (legfoot - legw, 0))
    out = [arm, stroke(leg, legw, 0, cut + 108)]
    out += foot(armtip - armw, armtip, top, el=serif, er=serif - 6, up=False)
    out += foot(legfoot - legw, legfoot, 0, el=serif, er=serif)
    return out


def sshape(uc, lc, ws, we, tu, tl, bk=1.0):
    """S / s: two flattened bowls plus the spine quad that joins them.

    uc / lc are (cx, cy, rx, ry) for the upper and lower bowl; tu / tl are
    (start, end) parameters. The spine runs from the upper bowl's mid-left to
    the lower bowl's mid-right, which is the only pairing that descends.
    """
    kw = dict(wside=ws, wend=we, sq=2.04, sqi=2.0)
    out = [band(uc[0], uc[1], uc[2], uc[3], tu[0], tu[1], **kw),
           band(lc[0], lc[1], lc[2], lc[3], tl[0], tl[1], **kw)]
    ou, iu = band_ends(uc[0], uc[1], uc[2], uc[3], tu[1], **kw)
    ol, il = band_ends(lc[0], lc[1], lc[2], lc[3], tl[0], **kw)
    out.append(poly(ou, il, ol, iu))
    o, i = band_ends(uc[0], uc[1], uc[2], uc[3], tu[0], **kw)
    out.append(poly(o, (o[0] + 26 * bk, o[1] + 30 * bk),
                    (o[0] + 34 * bk, o[1] - 18 * bk), i))
    o, i = band_ends(lc[0], lc[1], lc[2], lc[3], tl[1], **kw)
    out.append(poly(o, (o[0] - 26 * bk, o[1] - 30 * bk),
                    (o[0] - 34 * bk, o[1] + 18 * bk), i))
    return out


def wshape(top, bot, v1, v2, tops, thick, thin, serif):
    """Two overlapping Vs. tops = the four stroke tops (A left edge, B right
    edge, C left edge, D right edge); v1 / v2 are the baseline vertices."""
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
    out += foot(B_l.x(top), C_r.x(top), top, el=serif - 6, er=serif - 6,
                up=False)
    out += foot(D_l.x(top), dr, top, el=serif - 6, er=serif, up=False)
    return out


# ---------------------------------------------------------------------------
# the face. Widths given to @glyph are fallbacks - anything listed in SB below
# gets its advance measured from the ink it actually drew.
# ---------------------------------------------------------------------------
F = Font("Gravitas Text", em=EM, ascent=ASCENT, descent=DESCENT,
         copyright="Drawn programmatically with FontMaker.")
F.cap_height = CAP
F.x_height = XH
glyph = F.glyph


# =========================== UPPERCASE =====================================

@glyph('A', 722)
def _A():
    top = CAP + 4
    Lo = Line((64, 0), (332, top))
    Li = Lo.shift(52)
    Ro = Line((384, top), (658, 0))
    Ri = Ro.shift(-106)
    ax, ay = xsect(Li, Ri)
    b0, b1 = 186, 186 + CBAR
    body = poly((64, 0), (332, top), (384, top), (658, 0),
                (Ri.x(0), 0), (Ri.x(b0), b0), (Li.x(b0), b0), (Li.x(0), 0))
    counter = hole(poly((Li.x(b1), b1), (ax, ay), (Ri.x(b1), b1)))
    out = [body, counter]
    out += foot(64, 116, 0, el=46, er=46)
    out += foot(Ri.x(0), 658, 0, el=46, er=46)
    return out


@glyph('B', 680)
def _B():
    x0, x1 = 80, 180
    waist = 372
    out = [rect(x0, 0, x1, CAP)]
    out += bowl_right(x1, CAP, waist, 566, 92, 46, 32, x0)
    out += bowl_right(x1, waist, 0, 608, CSTEM, 32, 48, x0)
    out += foot(x0, x1, 0, el=SE, er=22)
    out += foot(x0, x1, CAP, el=SE, er=22, up=False)
    return out


@glyph('C', 700)
def _C():
    return cshape(366, CAP / 2.0, 322, CAP / 2.0 + OVS, CSTEM, CHAIR + 4,
                  62, 306, bk=1.25)


@glyph('D', 722)
def _D():
    x0, x1 = 80, 180
    out = [rect(x0, 0, x1, CAP)]
    out += bowl_right(x1, CAP, 0, 654, CSTEM, 50, 50, x0, sq=2.3)
    out += foot(x0, x1, 0, el=SE, er=22)
    out += foot(x0, x1, CAP, el=SE, er=22, up=False)
    return out


@glyph('E', 622)
def _E():
    x0, x1 = 80, 180
    mid = 316
    out = [rect(x0, 0, x1, CAP),
           rect(x0 - SE, CAP - CBAR, 540, CAP),
           rect(x0 - SE, 0, 566, CBAR),
           rect(x1, mid, 500, mid + LBAR)]
    out.append(bracket(x0, CAP - CBAR, -SE * 0.6, -34))
    out.append(bracket(x0, CBAR, -SE * 0.6, 34))
    out.append(bracket(x1, mid + LBAR, 26, -26))
    out.append(bracket(x1, mid, 26, 26))
    out += armend(540, CAP - CBAR, CAP, down=46, inward=-1)
    out += armend(566, 0, CBAR, up=46, inward=-1)
    out += armend(500, mid, mid + LBAR, down=30, up=30, inward=-1, brk=48)
    return out


@glyph('F', 590)
def _F():
    x0, x1 = 80, 180
    mid = 322
    out = [rect(x0, 0, x1, CAP),
           rect(x0 - SE, CAP - CBAR, 536, CAP),
           rect(x1, mid, 486, mid + LBAR)]
    out.append(bracket(x0, CAP - CBAR, -SE * 0.6, -34))
    out.append(bracket(x1, mid + LBAR, 26, -26))
    out.append(bracket(x1, mid, 26, 26))
    out += armend(536, CAP - CBAR, CAP, down=46, inward=-1)
    out += armend(486, mid, mid + LBAR, down=30, up=30, inward=-1, brk=48)
    out += foot(x0, x1, 0, el=SE, er=SE)
    return out


@glyph('G', 740)
def _G():
    cx, cy, rx, ry = 372, CAP / 2.0, 322, CAP / 2.0 + OVS
    kw = dict(wside=CSTEM, wend=CHAIR + 4, sq=SQ, sqi=SQI)
    out = [band(cx, cy, rx, ry, 62, 330, **kw)]
    o, i = band_ends(cx, cy, rx, ry, 62, **kw)
    out.append(beak(o, i, 38, 32))
    out.append(rect(572, 96, 672, 312))            # spur
    out.append(rect(452, 258, 672, 312))           # bar
    out.append(bracket(572, 312, -34, -30))
    out += armend(452, 258, 312, down=34, inward=1, brk=50)
    return out


@glyph('H', 722)
def _H():
    l0, l1, r0, r1 = 84, 184, 538, 638
    bar = 318
    out = [rect(l0, 0, l1, CAP), rect(r0, 0, r1, CAP),
           rect(l1, bar, r0, bar + CBAR)]
    for x0, x1 in ((l0, l1), (r0, r1)):
        out += foot(x0, x1, 0, el=SE, er=SE)
        out += foot(x0, x1, CAP, el=SE, er=SE, up=False)
    return out


@glyph('I', 350)
def _I():
    x0, x1 = 125, 225
    out = [rect(x0, 0, x1, CAP)]
    out += foot(x0, x1, 0, el=71, er=71)
    out += foot(x0, x1, CAP, el=71, er=71, up=False)
    return out


@glyph('J', 412)
def _J():
    x0, x1 = 216, 316
    hook = dict(rxi=50, ryi=112, cxi=166, cyi=146, sq=2.1)
    out = [rect(x0, 140, x1, CAP),
           band(186, 150, 130, 159, 0, -140, **hook)]
    o, i = band_ends(186, 150, 130, 159, -140, **hook)
    out.append(poly(o, (o[0] - 16, o[1] + 28), (i[0] - 10, i[1] + 20), i))
    out += foot(x0, x1, CAP, el=SE, er=SE, up=False)
    return out


@glyph('K', 722)
def _K():
    x0, x1 = 80, 180
    out = [rect(x0, 0, x1, CAP)]
    out += kshape(x0, CAP, 668, 104, 108, 680, 300, 44)
    out += foot(x0, x1, 0, el=SE, er=SE)
    out += foot(x0, x1, CAP, el=SE, er=SE, up=False)
    return out


@glyph('L', 622)
def _L():
    x0, x1 = 80, 180
    out = [rect(x0, 0, x1, CAP), rect(x0 - SE, 0, 566, CBAR)]
    out.append(bracket(x0, CBAR, -SE * 0.6, 34))
    out += armend(566, 0, CBAR, up=48, inward=-1)
    out += foot(x0, x1, CAP, el=SE, er=SE, up=False)
    return out


@glyph('M', 916)
def _M():
    l0, l1 = 80, 146
    r0, r1 = 770, 836
    L1 = Line((l0, CAP), (438, 0))
    L2 = L1.shift(102)
    L3 = Line((486, 0), (754, CAP))
    L4 = L3.shift(48)
    vx, vy = xsect(L2, L3)
    out = [poly((l0, 0), (l0, CAP), (L2.x(CAP), CAP), (vx, vy),
                (L3.x(CAP), CAP), (r1, CAP), (r1, 0), (r0, 0),
                (r0, L4.y0 + (r0 - L4.x0) / L4.slope), (L4.x(0), 0),
                (L1.x(0), 0), (l1, (L1.x0 - l1) / -L1.slope + L1.y0), (l1, 0))]
    out += foot(l0, l1, 0, el=SE, er=SE)
    out += foot(r0, r1, 0, el=SE, er=SE)
    out += foot(l0, L2.x(CAP), CAP, el=SE, er=0, up=False)
    out += foot(L3.x(CAP), r1, CAP, el=0, er=SE, up=False)
    return out


@glyph('N', 722)
def _N():
    l0, l1 = 80, 146
    r0, r1 = 576, 642
    D = Line((l1 - 4, CAP), (r0 + 4, 0))
    Di = D.shift(-98)
    out = [rect(l0, 0, l1, CAP), rect(r0, 0, r1, CAP),
           poly((D.x(CAP), CAP), (D.x(0), 0), (Di.x(0), 0), (Di.x(CAP), CAP))]
    out += foot(l0, l1, 0, el=SE, er=SE)
    out += foot(r0, r1, 0, el=SE, er=SE)
    out += foot(l0, l1 + 44, CAP, el=SE, er=0, up=False)
    out += foot(r0 - 44, r1, CAP, el=0, er=SE, up=False)
    return out


@glyph('O', 748)
def _O():
    return ring(374, CAP / 2.0, 340, CAP / 2.0 + OVS, CSTEM + 6, CHAIR + 4)


@glyph('P', 600)
def _P():
    x0, x1 = 80, 180
    out = [rect(x0, 0, x1, CAP)]
    out += bowl_right(x1, CAP, 268, 566, 96, 48, 40, x0)
    out += foot(x0, x1, 0, el=SE, er=SE)
    out += foot(x0, x1, CAP, el=SE, er=22, up=False)
    return out


@glyph('Q', 748)
def _Q():
    out = ring(374, CAP / 2.0, 340, CAP / 2.0 + OVS, CSTEM + 6, CHAIR + 4)
    tail = [('m', (430, 60)),
            ('c', (530, -20), (610, -104), (700, -186)),
            ('l', (622, -212)),
            ('c', (540, -122), (452, -46), (376, 6)),
            ('l', (430, 60))]
    out.append(cw(tail))
    return out


@glyph('R', 690)
def _R():
    x0, x1 = 80, 180
    junc = 268
    out = [rect(x0, 0, x1, CAP)]
    out += bowl_right(x1, CAP, junc, 540, 92, 48, 40, x0)
    leg = Line((236, junc + 60), (556, 0))
    out.append(stroke(leg, 108, 0, junc + 78))
    out += foot(leg.x(0), leg.x(0) + 108, 0, el=44, er=44)
    out += foot(x0, x1, 0, el=SE, er=SE)
    out += foot(x0, x1, CAP, el=SE, er=22, up=False)
    return out


@glyph('S', 580)
def _S():
    return sshape((300, 496, 192, 184), (292, 182, 214, 191),
                  96, CHAIR, (18, 218), (38, -162), bk=1.2)


@glyph('T', 640)
def _T():
    x0, x1 = 270, 370
    out = [rect(x0, 0, x1, CAP), rect(46, CAP - CBAR, 594, CAP)]
    out.append(bracket(x0, CAP - CBAR, -30, -34))
    out.append(bracket(x1, CAP - CBAR, 30, -34))
    out += armend(46, CAP - CBAR, CAP, down=48, inward=1)
    out += armend(594, CAP - CBAR, CAP, down=48, inward=-1)
    out += foot(x0, x1, 0, el=SE, er=SE)
    return out


@glyph('U', 722)
def _U():
    l0, l1 = 84, 184
    r0, r1 = 546, 638
    out = [rect(l0, 180, l1, CAP), rect(r0, 0, r1, CAP)]
    out += arch(l0, l1, r0, r1, -OVS, CHAIR + 6, 190, 232, sq=2.12, up=False)
    out += foot(l0, l1, CAP, el=SE, er=SE, up=False)
    out += foot(r0, r1, CAP, el=SE, er=SE, up=False)
    out += foot(r0, r1, 0, el=SE, er=SE)
    return out


@glyph('V', 722)
def _V():
    top = CAP
    Lo = Line((36, top), (330, 0))
    Li = Lo.shift(104)
    Ro = Line((686, top), (392, 0))
    Ri = Ro.shift(-48)
    vx, vy = xsect(Li, Ri)
    out = [poly((36, top), (Li.x(top), top), (vx, vy), (Ri.x(top), top),
                (686, top), (Ro.x(-6), -6), (Lo.x(-6), -6))]
    out += foot(36, Li.x(top), top, el=SE, er=SE, up=False)
    out += foot(Ri.x(top), 686, top, el=SE, er=SE, up=False)
    return out


@glyph('W', 990)
def _W():
    return wshape(CAP, -6, 236, 744, (40, 404, 386, 950), 100, 46, 40)


@glyph('X', 722)
def _X():
    A = Line((60, CAP), (560, 0))          # thick, top-left to bottom-right
    B = Line((608, CAP), (108, 0))         # thin, top-right to bottom-left
    out = [stroke(A, 104, 0, CAP), stroke(B, 50, 0, CAP)]
    out += foot(60, 164, CAP, el=44, er=44, up=False)
    out += foot(608, 658, CAP, el=48, er=48, up=False)
    out += foot(560, 664, 0, el=44, er=44)
    out += foot(108, 158, 0, el=48, er=48)
    return out


@glyph('Y', 722)
def _Y():
    junc = 296
    Lo = Line((34, CAP), (311, junc))
    Li = Lo.shift(104)
    Ro = Line((688, CAP), (411, junc))
    Ri = Ro.shift(-48)
    out = [rect(311, 0, 411, junc + 6),
           poly((34, CAP), (Li.x(CAP), CAP), xsect(Li, Ri),
                (Ri.x(CAP), CAP), (688, CAP), (411, junc), (311, junc))]
    out += foot(34, Li.x(CAP), CAP, el=SE, er=SE, up=False)
    out += foot(Ri.x(CAP), 688, CAP, el=SE, er=SE, up=False)
    out += foot(311, 411, 0, el=SE, er=SE)
    return out


@glyph('Z', 624)
def _Z():
    D = Line((498, CAP - CBAR), (100, CBAR))
    Di = D.shift(112)
    out = [rect(58, CAP - CBAR, 566, CAP),
           rect(46, 0, 578, CBAR),
           poly((D.x(CAP - CBAR), CAP - CBAR), (D.x(CBAR), CBAR),
                (Di.x(CBAR), CBAR), (Di.x(CAP - CBAR), CAP - CBAR))]
    out += armend(58, CAP - CBAR, CAP, down=52, inward=1)
    out += armend(566, CAP - CBAR, CAP, down=30, inward=-1)
    out += armend(46, 0, CBAR, up=30, inward=1)
    out += armend(578, 0, CBAR, up=52, inward=-1)
    return out


# =========================== LOWERCASE =====================================

@glyph('a', 486)
def _a():
    x0, x1 = 322, 410
    out = [rect(x0, 0, x1, 392)]
    out += bowl_left(x0, 280, -OVS, 54, STEM - 6, HAIR + 4, HAIR + 8, x1)
    # top arch: an ellipse whose inner centre is pushed left, so the stroke
    # arrives thick at the stem and leaves thin at the terminal
    ar = dict(rxi=108, ryi=75, cxi=214, cyi=384, sq=2.08, sqi=2.02)
    out.append(band(234, 380, 176, 121, 0, 190, **ar))
    o, i = band_ends(234, 380, 176, 121, 190, **ar)
    out.append(poly(o, (o[0] - 6, o[1] + 44), (o[0] + 46, o[1] + 40), i))
    out += foot(x0, x1, 0, el=0, er=SL)
    out.append(poly((x0, 0), (x0, 78), (x0 - 44, 0)))
    return out


@glyph('b', 522)
def _b():
    x0, x1 = 68, 156
    out = [rect(x0, 0, x1, ASC)]
    out += bowl_right(x1, XH + OVS, -OVS, 500, STEM, HAIR + 6, HAIR + 8,
                      x0 + LAP)
    out += foot(x0, x1, 0, el=SL, er=18)
    out.append(rect(x0 - SL, ASC - TIP, x1 + 12, ASC))
    out.append(bracket(x0, ASC - TIP, -SL * 0.66, -(BRK - TIP)))
    return out


@glyph('c', 466)
def _c():
    return cshape(244, XH / 2.0, 208, XH / 2.0 + OVS, STEM, HAIR + 4,
                  58, 310, bk=0.95, sq=2.1)


@glyph('d', 522)
def _d():
    x0, x1 = 366, 454
    out = [rect(x0, 0, x1, ASC)]
    out += bowl_left(x0, XH + OVS, -OVS, 22, STEM, HAIR + 6, HAIR + 8,
                     x1 - LAP)
    out += foot(x0, x1, 0, el=18, er=SL)
    out += foot(x0, x1, ASC, el=SL, er=SL, up=False)
    return out


@glyph('e', 470)
def _e():
    cx, cy, rx, ry = 240, XH / 2.0, 208, XH / 2.0 + OVS
    bar_t = 300
    kw = dict(wside=STEM, wend=HAIR + 4, sq=2.1, sqi=2.05)
    t0 = math.degrees(math.asin((bar_t - cy) / ry))
    out = [band(cx, cy, rx, ry, t0, 310, **kw),
           rect(cx - rx, bar_t - 46, cx + rx, bar_t)]
    o, i = band_ends(cx, cy, rx, ry, 310, **kw)
    out.append(poly(o, (o[0] + 42, o[1] + 6), (o[0] + 32, o[1] + 44), i))
    return out


@glyph('f', 372)
def _f():
    x0, x1 = 128, 216
    hk = dict(rxi=38, ryi=118, cxi=254, cyi=540, sq=2.06, sqi=2.0)
    out = [rect(x0, 0, x1, 560),
           band(232, 548, 106, 164, 180, 12, **hk)]
    o, i = band_ends(232, 548, 106, 164, 12, **hk)
    out.append(oval((o[0] + i[0]) / 2.0 + 8, (o[1] + i[1]) / 2.0 - 2,
                    46, 44, sq=2.2))
    out.append(rect(20, XH - LBAR + 6, 326, XH + 6))
    out += foot(x0, x1, 0, el=SL, er=SL)
    return out


@glyph('g', 500)
def _g():
    # binocular g: bowl at the x-height, link, and a loop below the baseline
    out = list(ring(236, 322, 172, 178, STEM - 6, HAIR + 2, sq=2.08))
    out.append(poly((338, 438), (446, 500), (462, 452), (376, 396)))   # ear
    out.append(rect(318, 20, 402, 220))                                # link
    lp = dict(rxi=118, ryi=112, cxi=244, cyi=-24, sq=2.06, sqi=2.0)
    out.append(band(236, -30, 200, 150, 30, -212, **lp))
    o, i = band_ends(236, -30, 200, 150, -212, **lp)
    out.append(poly(o, (o[0] + 8, o[1] + 40), (i[0] + 22, i[1] + 26), i))
    return out


@glyph('h', 522)
def _h():
    l0, l1 = 68, 156
    r0, r1 = 366, 454
    out = [rect(l0, 0, l1, ASC), rect(r0, 0, r1, 330)]
    out += arch(l0, l1, r0, r1, XH + 6, HAIR + 6, 300, 262)
    out += foot(l0, l1, 0, el=SL, er=SL)
    out += foot(r0, r1, 0, el=SL, er=SL)
    out.append(rect(l0 - SL, ASC - TIP, l1 + 12, ASC))
    out.append(bracket(l0, ASC - TIP, -SL * 0.66, -(BRK - TIP)))
    return out


@glyph('i', 286)
def _i():
    return _dotlessi() + dot(143, XH + 118, 54)


@glyph('j', 300)
def _j():
    x0, x1 = 96, 184
    hk = dict(rxi=104 - 82, ryi=104 + 30 - 42, sq=2.1)
    out = [rect(x0, -60, x1, XH),
           band(x0 - 8, -70, 104, 104 + 30, 0, -110, **hk)]
    o, i = band_ends(x0 - 8, -70, 104, 104 + 30, -110, **hk)
    out.append(poly(o, (o[0] - 24, o[1] + 36), (i[0] - 16, i[1] + 30), i))
    out.append(rect(x0 - SL, XH - TIP, x1 + 12, XH))
    out.append(bracket(x0, XH - TIP, -SL * 0.66, -(BRK - TIP)))
    out += dot(x0 + 44, XH + 118, 54)
    return out


@glyph('k', 500)
def _k():
    x0, x1 = 68, 156
    out = [rect(x0, 0, x1, ASC)]
    out += kshape(x0, XH, 464, 90, 92, 476, 214, 38)
    out += foot(x0, x1, 0, el=SL, er=SL)
    out.append(rect(x0 - SL, ASC - TIP, x1 + 12, ASC))
    out.append(bracket(x0, ASC - TIP, -SL * 0.66, -(BRK - TIP)))
    return out


@glyph('l', 286)
def _l():
    x0, x1 = 99, 187
    out = [rect(x0, 0, x1, ASC)]
    out += foot(x0, x1, 0, el=SL, er=SL)
    out.append(rect(x0 - SL, ASC - TIP, x1 + 12, ASC))
    out.append(bracket(x0, ASC - TIP, -SL * 0.66, -(BRK - TIP)))
    return out


@glyph('m', 800)
def _m():
    a0, a1 = 68, 156
    b0, b1 = 358, 446
    c0, c1 = 644, 732
    out = [rect(a0, 0, a1, XH), rect(b0, 0, b1, 330), rect(c0, 0, c1, 330)]
    out += arch(a0, a1, b0, b1, XH + 6, HAIR + 4, 300, 262)
    out += arch(b0, b1, c0, c1, XH + 6, HAIR + 4, 300, 262)
    for x0, x1 in ((a0, a1), (b0, b1), (c0, c1)):
        out += foot(x0, x1, 0, el=SL, er=SL)
    out.append(rect(a0 - SL, XH - TIP, a1 + 12, XH))
    out.append(bracket(a0, XH - TIP, -SL * 0.66, -(BRK - TIP)))
    return out


@glyph('n', 522)
def _n():
    l0, l1 = 68, 156
    r0, r1 = 366, 454
    out = [rect(l0, 0, l1, XH), rect(r0, 0, r1, 330)]
    out += arch(l0, l1, r0, r1, XH + 6, HAIR + 6, 300, 262)
    out += foot(l0, l1, 0, el=SL, er=SL)
    out += foot(r0, r1, 0, el=SL, er=SL)
    out.append(rect(l0 - SL, XH - TIP, l1 + 12, XH))
    out.append(bracket(l0, XH - TIP, -SL * 0.66, -(BRK - TIP)))
    return out


@glyph('o', 512)
def _o():
    return ring(256, XH / 2.0, 236, XH / 2.0 + OVS, STEM + 2, HAIR + 6)


@glyph('p', 522)
def _p():
    x0, x1 = 68, 156
    out = [rect(x0, DESC, x1, XH)]
    out += bowl_right(x1, XH + OVS, -OVS, 500, STEM, HAIR + 6, HAIR + 8,
                      x0 + LAP)
    out += foot(x0, x1, DESC, el=SL, er=SL)
    out.append(rect(x0 - SL, XH - TIP, x1 + 12, XH))
    out.append(bracket(x0, XH - TIP, -SL * 0.66, -(BRK - TIP)))
    return out


@glyph('q', 522)
def _q():
    x0, x1 = 366, 454
    out = [rect(x0, DESC, x1, XH)]
    out += bowl_left(x0, XH + OVS, -OVS, 22, STEM, HAIR + 6, HAIR + 8,
                     x1 - LAP)
    out += foot(x0, x1, DESC, el=SL, er=SL)
    return out


@glyph('r', 386)
def _r():
    x0, x1 = 68, 156
    sh = dict(rxi=60, ryi=156, cxi=210, cyi=296, sq=2.06, sqi=2.0)
    out = [rect(x0, 0, x1, XH),
           band(200, 296, 126, 202, 180, 20, **sh)]
    o, i = band_ends(200, 296, 126, 202, 20, **sh)
    out.append(oval((o[0] + i[0]) / 2.0 + 6, (o[1] + i[1]) / 2.0 - 2,
                    50, 47, sq=2.2))
    out += foot(x0, x1, 0, el=SL, er=SL)
    out.append(rect(x0 - SL, XH - TIP, x1 + 12, XH))
    out.append(bracket(x0, XH - TIP, -SL * 0.66, -(BRK - TIP)))
    return out


@glyph('s', 420)
def _s():
    return sshape((214, 356, 140, 136), (208, 132, 156, 141),
                  84, HAIR, (18, 216), (36, -164), bk=0.85)


@glyph('t', 344)
def _t():
    x0, x1 = 74, 162
    # 180 -> 330 goes round the bottom; 180 -> -30 is the same end point the
    # wrong way, over the top.
    tl = dict(rxi=52, ryi=117, cxi=220, cyi=150, sq=2.08, sqi=2.02)
    out = [rect(x0, 140, x1, XH + 148),
           band(200, 150, 120, 159, 180, 330, **tl)]
    o, i = band_ends(200, 150, 120, 159, 330, **tl)
    out.append(poly(o, (o[0] + 30, o[1] + 16), (o[0] + 20, o[1] + 48), i))
    out.append(rect(6, XH - LBAR + 6, 310, XH + 6))
    return out


@glyph('u', 522)
def _u():
    l0, l1 = 68, 156
    r0, r1 = 366, 454
    out = [rect(l0, 150, l1, XH), rect(r0, 0, r1, XH)]
    out += arch(l0, l1, r0, r1, -OVS, HAIR + 6, 160, 196, sq=2.12, up=False)
    out += foot(l0, l1, XH, el=SL, er=SL, up=False)
    out += foot(r0, r1, XH, el=SL, er=12, up=False)
    out += foot(r0, r1, 0, el=SL, er=SL)
    return out


@glyph('v', 504)
def _v():
    Lo = Line((26, XH), (216, 0))
    Li = Lo.shift(92)
    Ro = Line((478, XH), (288, 0))
    Ri = Ro.shift(-44)
    out = [poly((26, XH), (Li.x(XH), XH), xsect(Li, Ri), (Ri.x(XH), XH),
                (478, XH), (Ro.x(-6), -6), (Lo.x(-6), -6))]
    out += foot(26, Li.x(XH), XH, el=SL, er=SL, up=False)
    out += foot(Ri.x(XH), 478, XH, el=SL, er=SL, up=False)
    return out


@glyph('w', 740)
def _w():
    return wshape(XH, -6, 186, 556, (32, 296, 284, 708), 88, 44, 34)


@glyph('x', 506)
def _x():
    A = Line((40, XH), (372, 0))            # thick, top-left to bottom-right
    B = Line((414, XH), (82, 0))            # thin, top-right to bottom-left
    out = [stroke(A, 90, 0, XH), stroke(B, 44, 0, XH)]
    out += foot(40, 130, XH, el=38, er=38, up=False)
    out += foot(414, 458, XH, el=42, er=42, up=False)
    out += foot(372, 462, 0, el=38, er=38)
    out += foot(82, 126, 0, el=42, er=42)
    return out


@glyph('y', 504)
def _y():
    Lo = Line((26, XH), (216, 0))
    Li = Lo.shift(92)
    Ro = Line((486, XH), (236, -160))
    Ri = Ro.shift(-44)
    # the stroke runs a little past where the tail picks it up, so the tail's
    # first cross-section lands inside it rather than on its tip
    out = [poly((26, XH), (Li.x(XH), XH), xsect(Li, Ri), (Ri.x(XH), XH),
                (486, XH), (Ro.x(-124), -124), (Lo.x(-6), -6))]
    tl = dict(rxi=96 - 62, ryi=84 - 36, sq=2.1)
    out.append(band(Ro.x(-116) - 96, -116, 96, 84, 0, -132, **tl))
    o, i = band_ends(Ro.x(-116) - 96, -116, 96, 84, -132, **tl)
    out.append(poly(o, (o[0] - 20, o[1] + 34), (i[0] - 14, i[1] + 24), i))
    out += foot(26, Li.x(XH), XH, el=SL, er=SL, up=False)
    out += foot(Ri.x(XH), 486, XH, el=SL, er=SL, up=False)
    return out


@glyph('z', 450)
def _z():
    D = Line((362, XH - LBAR), (94, LBAR))
    Di = D.shift(96)
    out = [rect(52, XH - LBAR, 408, XH),
           rect(40, 0, 420, LBAR),
           poly((D.x(XH - LBAR), XH - LBAR), (D.x(LBAR), LBAR),
                (Di.x(LBAR), LBAR), (Di.x(XH - LBAR), XH - LBAR))]
    out += armend(52, XH - LBAR, XH, down=40, inward=1, brk=48)
    out += armend(408, XH - LBAR, XH, down=24, inward=-1, brk=48)
    out += armend(40, 0, LBAR, up=24, inward=1, brk=48)
    out += armend(420, 0, LBAR, up=40, inward=-1, brk=48)
    return out


# ============================ FIGURES ======================================

@glyph('zero', 520)
def _zero():
    return ring(260, FIG / 2.0, 216, FIG / 2.0 + OVS, 92, 42, sq=2.06)


@glyph('one', 520)
def _one():
    x0, x1 = 212, 312
    out = [rect(x0, 0, x1, FIG)]
    out.append(poly((x0, FIG), (x0, FIG - 128), (110, FIG - 176),
                    (110, FIG - 116)))
    out += foot(x0, x1, 0, el=112, er=112)
    return out


@glyph('two', 520)
def _two():
    tp = dict(rxi=186 - 84, ryi=186 + 14 - 46, sq=2.05)
    out = [band(258, 452, 186, 186 + 14, 176, -12, **tp)]
    out.append(poly((444, 424), (444, 380), (330, 258), (206, 128),
                    (152, 84), (60, 84), (60, 148)))
    out.append(rect(60, 0, 470, 62))
    o, i = band_ends(258, 452, 186, 186 + 14, 176, **tp)
    out.append(poly(o, (o[0] + 6, o[1] - 46), (i[0] + 18, i[1] - 34), i))
    out += armend(470, 0, 62, up=52, inward=-1, brk=48)
    return out


@glyph('three', 520)
def _three():
    ws = 88
    out = [band(272, 500, 164, 166, 190, -70, wside=ws, wend=44, sq=2.05),
           band(258, 176, 200, 190, 74, -210, wside=ws, wend=44, sq=2.05)]
    out.append(rect(206, 328, 340, 386))
    o, i = band_ends(272, 500, 164, 166, 190, wside=ws, wend=44, sq=2.05)
    out.append(poly(o, (o[0] + 10, o[1] - 44), (i[0] + 22, i[1] - 32), i))
    o, i = band_ends(258, 176, 200, 190, 74, wside=ws, wend=44, sq=2.05)
    out.append(poly(o, (o[0] + 20, o[1] + 34), (i[0] + 14, i[1] + 20), i))
    return out


@glyph('four', 520)
def _four():
    out = [rect(300, 0, 392, FIG),
           rect(40, 132, 470, 196),
           poly((300, 640), (356, 640), (140, 160), (56, 160))]
    out += foot(300, 392, 0, el=54, er=54)
    return out


@glyph('five', 520)
def _five():
    bw = dict(wside=92, wend=44, sq=2.05)
    # The bowl leaves the stem at its upper left, goes over the top and round
    # to a terminal at the lower left - the gap is on the left, not the top.
    # The arm and the stroke down its left are one L, so nothing abuts.
    out = [band(290, 186, 178, 200, 150, -150, **bw),
           poly((110, FIG), (452, FIG), (452, 604), (196, 604), (196, 270),
                (110, 270))]
    o, i = band_ends(290, 186, 178, 200, -150, **bw)
    out.append(poly(o, (o[0] - 26, o[1] + 26), (i[0] - 16, i[1] + 20), i))
    out += armend(452, 604, FIG, down=44, inward=-1, brk=52)
    return out


@glyph('six', 520)
def _six():
    out = [band(266, 208, 202, 208, 100, 440, wside=90, wend=42, sq=2.06)]
    ha = dict(rxi=236 - 88, ryi=246 - 44, sq=2.05)
    out.append(band(300, 420, 236, 246, 58, 176, **ha))
    o, i = band_ends(300, 420, 236, 246, 58, **ha)
    out.append(poly(o, (o[0] + 26, o[1] + 12), (o[0] + 22, o[1] - 30), i))
    return out


@glyph('seven', 520)
def _seven():
    out = [rect(40, FIG - 66, 476, FIG),
           poly((460, 640), (410, 640), (154, 0), (250, 0))]
    out += armend(40, FIG - 66, FIG, down=48, inward=1, brk=48)
    out += foot(154, 250, 0, el=30, er=30)
    return out


@glyph('eight', 520)
def _eight():
    out = list(ring(258, 484, 158, 182, 76, 40, sq=2.04))
    out += ring(262, 176, 196, 190, 90, 42, sq=2.04)
    return out


@glyph('nine', 520)
def _nine():
    # a six turned through 180 degrees, so the two always agree
    return [flipy(flipx(c, 260), FIG / 2.0) for c in _six()]


# ========================== PUNCTUATION ====================================

@glyph('period', 272)
def _period():
    return dot(136, 62, 62)


@glyph('comma', 272)
def _comma():
    return comma(120, 66, 62)


@glyph('colon', 288)
def _colon():
    return dot(144, 62, 62) + dot(144, XH - 62, 62)


@glyph('semicolon', 288)
def _semicolon():
    return comma(128, 66, 62) + dot(144, XH - 62, 62)


@glyph('exclam', 320)
def _exclam():
    return [poly((104, CAP), (216, CAP), (196, 208), (124, 208))] + \
        dot(160, 62, 62)


@glyph('question', 456)
def _question():
    qa = dict(wside=82, wend=42, sq=2.05)
    out = [band(228, 452, 168, 176, 190, -46, **qa)]
    out.append(poly((300, 300), (300, 250), (256, 208), (184, 208),
                    (184, 260), (216, 300)))
    o, i = band_ends(228, 452, 168, 176, 190, **qa)
    out.append(poly(o, (o[0] + 10, o[1] - 44), (i[0] + 22, i[1] - 32), i))
    out += dot(220, 62, 62)
    return out


@glyph('quotesingle', 220)
def _quotesingle():
    return [poly((70, CAP), (150, CAP), (138, CAP - 210), (82, CAP - 210))]


@glyph('quotedbl', 372)
def _quotedbl():
    return [poly((70, CAP), (150, CAP), (138, CAP - 210), (82, CAP - 210)),
            poly((222, CAP), (302, CAP), (290, CAP - 210), (234, CAP - 210))]


@glyph('quoteright', 240)
def _quoteright():
    return comma(126, CAP - 60, 58)


@glyph('quoteleft', 240)
def _quoteleft():
    return [flipy(flipx(c, 126), CAP - 88) for c in comma(126, CAP - 60, 58)]


@glyph('quotedblright', 420)
def _quotedblright():
    return comma(126, CAP - 60, 58) + comma(300, CAP - 60, 58)


@glyph('quotedblleft', 420)
def _quotedblleft():
    a = [flipy(flipx(c, 126), CAP - 88) for c in comma(126, CAP - 60, 58)]
    b = [flipy(flipx(c, 300), CAP - 88) for c in comma(300, CAP - 60, 58)]
    return a + b


@glyph('hyphen', 340)
def _hyphen():
    return [rect(46, 236, 294, 236 + 52)]


@glyph('endash', 500)
def _endash():
    return [rect(30, 240, 470, 240 + 48)]


@glyph('emdash', 1000)
def _emdash():
    return [rect(0, 240, 1000, 240 + 48)]


@glyph('parenleft', 340)
def _parenleft():
    return [band(346, 250, 300, 500, 128, 232,
                 rxi=300 - 74, ryi=500 - 74, sq=2.0)]


@glyph('parenright', 340)
def _parenright():
    return [flipx(c, 170) for c in _parenleft()]


@glyph('bracketleft', 330)
def _bracketleft():
    return [rect(96, -180, 188, 730), rect(96, 638, 268, 730),
            rect(96, -180, 268, -88)]


@glyph('bracketright', 330)
def _bracketright():
    return [flipx(c, 165) for c in _bracketleft()]


@glyph('braceleft', 400)
def _braceleft():
    return [band(320, 502, 240, 228, 180, 90, rxi=240 - 76, ryi=228 - 76),
            band(320, -2, 240, 228, 180, 270, rxi=240 - 76, ryi=228 - 76),
            band(-72, 502, 232, 228, 0, -90, rxi=232 - 76, ryi=228 - 76),
            band(-72, -2, 232, 228, 0, 90, rxi=232 - 76, ryi=228 - 76)]


@glyph('braceright', 400)
def _braceright():
    return [flipx(c, 200) for c in _braceleft()]


@glyph('slash', 320)
def _slash():
    return [poly((14, -18), (222, 712), (306, 712), (98, -18))]


@glyph('backslash', 320)
def _backslash():
    return [flipx(c, 160) for c in _slash()]


@glyph('bar', 220)
def _bar():
    return [rect(76, -180, 144, 730)]


@glyph('underscore', 500)
def _underscore():
    return [rect(0, -150, 500, -96)]


@glyph('asterisk', 460)
def _asterisk():
    out = []
    cx, cy, r = 230, 500, 168
    for i in range(5):
        a = math.radians(90 + i * 72)
        tip = (cx + r * math.cos(a), cy + r * math.sin(a))
        b = (cx + 44 * math.cos(a + 1.6), cy + 44 * math.sin(a + 1.6))
        c = (cx + 44 * math.cos(a - 1.6), cy + 44 * math.sin(a - 1.6))
        out.append(poly(tip, b, c))
    out.append(oval(cx, cy, 62, 62))
    return out


@glyph('plus', 570)
def _plus():
    return [rect(52, 262, 518, 330), rect(251, 63, 319, 529)]


@glyph('equal', 570)
def _equal():
    return [rect(52, 178, 518, 246), rect(52, 346, 518, 414)]


@glyph('less', 570)
def _less():
    return [poly((512, 480), (512, 410), (140, 296), (512, 182), (512, 112),
                 (52, 268), (52, 324))]


@glyph('greater', 570)
def _greater():
    return [flipx(c, 285) for c in _less()]


@glyph('numbersign', 560)
def _numbersign():
    return [poly((150, 0), (222, 0), (352, FIG), (280, FIG)),
            poly((330, 0), (402, 0), (532, FIG), (460, FIG)),
            rect(60, 200, 512, 262), rect(88, 404, 540, 466)]


@glyph('percent', 840)
def _percent():
    out = ring(196, 500, 160, 160, 58, 58, sq=2.05)
    out += ring(644, 166, 160, 160, 58, 58, sq=2.05)
    out.append(poly((560, 700), (664, 700), (280, -20), (176, -20)))
    return out


@glyph('ampersand', 760)
def _ampersand():
    out = list(ring(276, 506, 132, 128, 74, 44, sq=2.05))       # upper loop
    out.append(band(300, 196, 214, 200, 26, 302,                # lower bowl
                    wside=98, wend=46, sq=2.05))
    out.append(stroke(Line((206, 452), (470, 40)), 104, 40, 452))
    out.append(stroke(Line((520, 60), (700, 300)), 74, 60, 300))    # tail
    return out


@glyph('at', 940)
def _at():
    # the thing inside an @ is an a, so use the a - scaled down and centred
    out = ring(470, 300, 430, 380, 64, 58, sq=2.1)
    inner = scaled(_a(), 0.60, 0.60, 250, 246)
    return out + moveall(inner, 470 - 250, 300 - 246)


@glyph('asciitilde', 570)
def _asciitilde():
    return [band(160, 260, 112, 92, 180, 0, rxi=112 - 58, ryi=92 - 52),
            band(410, 316, 112, 92, 180, 360, rxi=112 - 58, ryi=92 - 52)]


@glyph('asciicircum', 500)
def _asciicircum():
    return [poly((30, 380), (232, 690), (268, 690), (470, 380), (398, 380),
                 (250, 606), (102, 380))]


@glyph('grave', 333)
def _grave():
    return [poly((44, 712), (156, 712), (290, 546), (216, 546))]


@glyph('space', 250)
def _space():
    return []


@glyph('acute', 333)
def _acute():
    return [poly((166, 712), (278, 712), (106, 546), (32, 546))]


@glyph('circumflex', 333)
def _circumflex():
    return [poly((166, 726), (296, 552), (222, 552), (166, 634),
                 (110, 552), (36, 552))]


@glyph('caron', 333)
def _caron():
    return [flipy(c, 639) for c in _circumflex()]


@glyph('tilde', 333)
def _tilde():
    return [band(96, 600, 76, 60, 180, 0, rxi=76 - 42, ryi=60 - 38),
            band(238, 638, 76, 60, 180, 360, rxi=76 - 42, ryi=60 - 38)]


@glyph('dieresis', 333)
def _dieresis():
    return dot(88, 640, 54) + dot(246, 640, 54)


@glyph('ring', 333)
def _ringacc():
    return ring(166, 640, 78, 78, 30, 30)


@glyph('cedilla', 333)
def _cedilla():
    return [poly((150, 0), (206, 0), (188, -62), (150, -62)),
            band(160, -110, 74, 62, 40, -230, rxi=74 - 34, ryi=62 - 30)]


@glyph('macron', 333)
def _macron():
    return [rect(30, 592, 302, 646)]


@glyph('breve', 333)
def _breve():
    return [band(166, 660, 116, 108, 180, 360,
                 rxi=116 - 38, ryi=108 - 44)]


@glyph('dotaccent', 333)
def _dotaccent():
    return dot(166, 640, 56)


@glyph('bullet', 460)
def _bullet():
    return dot(230, 280, 118)


@glyph('ellipsis', 900)
def _ellipsis():
    return dot(136, 62, 62) + dot(450, 62, 62) + dot(764, 62, 62)


@glyph('quotedblbase', 420)
def _quotedblbase():
    return comma(126, 60, 58) + comma(300, 60, 58)


@glyph('quotesinglbase', 240)
def _quotesinglbase():
    return comma(126, 60, 58)


@glyph('degree', 400)
def _degree():
    return ring(200, 566, 118, 118, 44, 44)


@glyph('paragraph', 560)
def _paragraph():
    out = [rect(300, -160, 372, CAP), rect(432, -160, 504, CAP)]
    out += bowl_left(300, CAP, 236, 60, 92, 66, 66, 372, sq=2.1)
    return out


@glyph('dotlessi', 286)
def _dotlessi():
    x0, x1 = 99, 187
    out = [rect(x0, 0, x1, XH)]
    out += foot(x0, x1, 0, el=SL, er=SL)
    out.append(rect(x0 - SL, XH - TIP, x1 + 12, XH))
    out.append(bracket(x0, XH - TIP, -SL * 0.66, -(BRK - TIP)))
    return out


def scaled(contours, sx, sy, ox, oy):
    out = []
    for c in contours:
        out.append([(seg[0],) + tuple(((x - ox) * sx + ox, (y - oy) * sy + oy)
                                      for (x, y) in seg[1:]) for seg in c])
    return out


@glyph('section', 520)
def _section():
    up = scaled(_S(), 0.80, 0.62, 290, 340)
    up = moveall(up, -30, 128)
    dn = [flipy(flipx(c, 260), 300) for c in up]
    return up + dn


@glyph('dollar', 520)
def _dollar():
    out = moveall(scaled(_S(), 0.88, 0.90, 290, 340), -30, -4)
    out.append(rect(228, -70, 292, FIG + 74))
    return out


@glyph('sterling', 520)
def _sterling():
    lp = dict(wside=84, wend=44, sq=2.05)
    out = [rect(214, 62, 306, 440),
           band(300, 470, 148, 156, 60, 210, **lp),
           rect(60, 0, 480, 62), rect(96, 258, 372, 312)]
    o, i = band_ends(300, 470, 148, 156, 60, **lp)
    out.append(beak(o, i, 30, 26))
    return out


@glyph('cent', 520)
def _cent():
    out = moveall(_c(), 16, 0)
    out.append(rect(226, -78, 290, XH + 78))
    return out


@glyph('yen', 720)
def _yen():
    out = list(_Y())
    out.append(rect(180, 190, 542, 246))
    out.append(rect(180, 316, 542, 372))
    return out


@glyph('euro', 560)
def _euro():
    cx, cy, rx, ry = 330, CAP / 2.0, 268, CAP / 2.0 + OVS
    out = [band(cx, cy, rx, ry, 58, 306, wside=92, wend=44, sq=SQ, sqi=SQI),
           rect(30, 268, 452, 322), rect(30, 396, 452, 450)]
    return out


@glyph('trademark', 980)
def _trademark():
    return [rect(40, CAP - 56, 380, CAP), rect(166, 420, 254, 660),
            rect(430, 420, 510, 676), rect(830, 420, 910, 676),
            poly((444, 656), (652, 430), (896, 656), (832, 656),
                 (670, 520), (508, 656))]


@glyph('copyright', 780)
def _copyright():
    out = ring(390, 340, 350, 350, 52, 52)
    return out + moveall(scaled(_C(), 0.5, 0.5, 366, 340), 22, 0)


@glyph('registered', 780)
def _registered():
    out = ring(390, 340, 350, 350, 52, 52)
    return out + moveall(scaled(_R(), 0.48, 0.48, 330, 340), 60, 0)

# ---------------------------------------------------------------------------
# face data: spacing, accents, kerning
# ---------------------------------------------------------------------------

# Sidebearings in font units, measured to the ink - the advance is derived from
# what was actually drawn rather than guessed up front. Round letters get a
# little less than flat-sided ones because their extreme is a tangent point,
# and diagonals less again so they interlock. Anything absent here (punctuation,
# accents) keeps the width declared at @glyph.
F.sidebearings.update({
    'A': (12, 12), 'B': (30, 26), 'C': (26, 30), 'D': (30, 26),
    'E': (30, 26), 'F': (30, 20), 'G': (26, 30), 'H': (30, 30),
    'I': (30, 30), 'J': (18, 30), 'K': (30, 20), 'L': (30, 20),
    'M': (28, 28), 'N': (30, 30), 'O': (26, 26), 'P': (30, 26),
    'Q': (26, 26), 'R': (30, 20), 'S': (28, 28), 'T': (16, 16),
    'U': (30, 30), 'V': (12, 12), 'W': (10, 10), 'X': (14, 14),
    'Y': (12, 12), 'Z': (24, 24),

    'a': (28, 26), 'b': (28, 26), 'c': (26, 22), 'd': (26, 28),
    'e': (26, 22), 'f': (22, 6), 'g': (26, 24), 'h': (28, 28),
    'i': (28, 28), 'j': (20, 20), 'k': (28, 20), 'l': (28, 28),
    'm': (28, 28), 'n': (28, 28), 'o': (26, 26), 'p': (28, 26),
    'q': (26, 28), 'r': (28, 14), 's': (24, 24), 't': (18, 16),
    'u': (28, 28), 'v': (16, 16), 'w': (14, 14), 'x': (16, 16),
    'y': (16, 16), 'z': (20, 20), 'dotlessi': (28, 28),

    'zero': (32, 32), 'two': (32, 32), 'three': (32, 32),
    'four': (26, 26), 'five': (32, 32), 'six': (32, 32),
    'seven': (28, 28), 'eight': (32, 32), 'nine': (32, 32),
})

# base letter -> accents to compose onto it. Placement is worked out at build
# time from the two glyphs' real ink boxes, so no offsets are given here.
F.accents.update({
    'A': 'grave acute circumflex tilde dieresis ring',
    'E': 'grave acute circumflex dieresis',
    'I': 'grave acute circumflex dieresis',
    'O': 'grave acute circumflex tilde dieresis',
    'U': 'grave acute circumflex dieresis',
    'N': 'tilde', 'Y': 'acute', 'C': 'cedilla', 'S': 'caron', 'Z': 'caron',
    'a': 'grave acute circumflex tilde dieresis ring',
    'e': 'grave acute circumflex dieresis',
    'i': 'grave acute circumflex dieresis',
    'o': 'grave acute circumflex tilde dieresis',
    'u': 'grave acute circumflex dieresis',
    'n': 'tilde', 'y': 'acute dieresis', 'c': 'cedilla',
    's': 'caron', 'z': 'caron',
})

# pairs that need help, in font units
F.kern += [
    ("A", "V W Y T", -60), ("A", "C G O Q", -20), ("A", "quoteright", -80),
    ("F", "A", -60), ("L", "V W Y T", -70), ("L", "quoteright", -90),
    ("P", "A", -70), ("T", "A", -60), ("V", "A", -60), ("W", "A", -50),
    ("Y", "A", -70), ("T", "a c e o s u y", -110),
    ("V", "a c e o s u y", -70), ("W", "a c e o s u y", -50),
    ("Y", "a c e o s u y", -100), ("F", "a c e o s", -40),
    ("P", "a c e o s", -30), ("r", "a c d e g o q", -20),
    ("r", "comma period", -80), ("y", "comma period", -70),
    ("v", "comma period", -70), ("w", "comma period", -50),
    ("f", "quoteright", -40), ("T", "comma period", -110),
    ("V", "comma period", -90), ("W", "comma period", -70),
    ("Y", "comma period", -100), ("A", "T", -50),
    ("o", "v w y", -20), ("e", "v w y", -20),
]


if __name__ == "__main__":
    sys.exit(F.cli())
