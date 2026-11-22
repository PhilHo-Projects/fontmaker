"""Over-The-Top Cartoony Font Generator (ToonBoom Heavy / Cartoony)

Generates a super bubbly, chunky, bouncy, over-the-top cartoony TrueType font.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from glyphlib import (
    rect, poly, oval, band, arc, hole, Line, xsect, stroke, cw, ccw, rev, move, bbox
)
from fontbuild import Font

EM, ASCENT, DESCENT = 1000, 800, 200
CAP, XH = 760, 530
OVS = 15

# Hyper-chunky cartoony stroke dimensions
STEM = 180      # Extra thick & juicy stems
HAIR = 130      # Thick crossbars / secondary strokes
SQ_BALLOON = 2.45  # Squishy superellipse exponent for pillowy look
LAP = 12        # Deep burial for clean unioning

F = Font("Toon Boom", style="Bold", em=EM, ascent=ASCENT, descent=DESCENT, vendor="TOON", weight=800)
F.cap_height, F.x_height = CAP, XH
glyph = F.glyph

# ---------------------------------------------------------------------------
# Cartoony Helper Brushes
# ---------------------------------------------------------------------------

def balloon_rect(x0, y0, x1, y1, sq=SQ_BALLOON):
    """Pillowy, superellipse-rounded box."""
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    rx, ry = abs(x1 - x0) / 2.0, abs(y1 - y0) / 2.0
    return oval(cx, cy, rx, ry, sq=sq)

def balloon_donut(cx, cy, rx, ry, rxi, ryi, sq=SQ_BALLOON, sqi=2.1):
    """Bulbous outer ring with a playful inner cutout."""
    return [oval(cx, cy, rx, ry, sq=sq), hole(oval(cx, cy, rxi, ryi, sq=sqi))]

def cartoony_bowl_right(x_attach, y_top, y_bot, x_max, w_side=STEM, w_end=HAIR, sq=2.35):
    """Juicy bulbous bowl springing right off a stem."""
    cy = (y_top + y_bot) / 2.0
    ry = (y_top - y_bot) / 2.0
    rx = x_max - x_attach
    c = [('m', (x_attach - LAP, y_top)), ('l', (x_attach, y_top))]
    c += arc(x_attach, cy, rx, ry, 90, -90, sq)
    c += [('l', (x_attach - LAP, y_bot)), ('l', (x_attach - LAP, y_bot + w_end)),
          ('l', (x_attach, y_bot + w_end))]
    c += arc(x_attach, cy, max(30, rx - w_side), max(30, ry - w_end), -90, 90, sq)
    c += [('l', (x_attach - LAP, y_top - w_end)), ('l', (x_attach - LAP, y_top))]
    return [cw(c)]

def cartoony_arch(lx0, lx1, rx0, rx1, y_top, w_end=HAIR, y_join=300, sq=2.3):
    """Playful rounded shoulder connecting two vertical stems."""
    cx = (lx0 + rx1) / 2.0
    rx = (rx1 - lx0) / 2.0 + LAP
    ry = y_top - y_join
    return [band(cx, y_join, rx, ry, 180, 0,
                 rxi=max(30, (rx0 - lx1) / 2.0 - LAP), ryi=max(30, ry - w_end),
                 cxi=(lx1 + rx0) / 2.0, cyi=y_join, sq=sq)]


# ---------------------------------------------------------------------------
# Capital Letters (A-Z) - Over-The-Top Cartoony Style
# ---------------------------------------------------------------------------

@glyph('A', 780)
def _A():
    return [
        poly((390, CAP + OVS), (740, 0), (560, 0), (390, CAP - 240),
             (220, 0), (40, 0)),
        oval(390, CAP - 120, 160, 160, sq=SQ_BALLOON),
        rect(120, 200, 660, 200 + HAIR),
    ]

@glyph('B', 760)
def _B():
    x0, x1 = 80, 80 + STEM
    return [
        rect(x0, 0, x1, CAP),
        oval(x0 + 40, CAP, 90, 90, sq=SQ_BALLOON),
        oval(x0 + 40, 0, 90, 90, sq=SQ_BALLOON),
    ] + cartoony_bowl_right(x1 - LAP, CAP, 360, 710, STEM, HAIR + 10) \
      + cartoony_bowl_right(x1 - LAP, 380, 0, 750, STEM + 20, HAIR + 10)

@glyph('C', 750)
def _C():
    return [
        band(400, CAP/2.0, 350, CAP/2.0 + OVS, 40, 320, wside=STEM, wend=HAIR + 20, sq=2.4),
        oval(640, CAP - 130, 100, 90, sq=SQ_BALLOON),
        oval(640, 130, 100, 90, sq=SQ_BALLOON),
    ]

@glyph('D', 780)
def _D():
    x0, x1 = 90, 90 + STEM
    return [
        rect(x0, 0, x1, CAP),
        oval(x0 + 40, CAP, 90, 90, sq=SQ_BALLOON),
        oval(x0 + 40, 0, 90, 90, sq=SQ_BALLOON),
    ] + cartoony_bowl_right(x1 - LAP, CAP, 0, 760, STEM + 10, HAIR + 25, sq=2.3)

@glyph('E', 680)
def _E():
    x0, x1 = 90, 90 + STEM
    return [
        rect(x0, 0, x1, CAP),
        balloon_rect(x0, CAP - HAIR - 20, 650, CAP + OVS),
        balloon_rect(x0, (CAP - HAIR)/2.0 - 10, 580, (CAP + HAIR)/2.0 + 10),
        balloon_rect(x0, -OVS, 660, HAIR + 20),
    ]

@glyph('F', 640)
def _F():
    x0, x1 = 90, 90 + STEM
    return [
        rect(x0, 0, x1, CAP),
        oval(x0 + 40, 0, 90, 90, sq=SQ_BALLOON),
        balloon_rect(x0, CAP - HAIR - 20, 620, CAP + OVS),
        balloon_rect(x0, (CAP - HAIR)/2.0, 540, (CAP + HAIR)/2.0 + 20),
    ]

@glyph('G', 790)
def _G():
    return [
        band(400, CAP/2.0, 350, CAP/2.0 + OVS, 40, 330, wside=STEM, wend=HAIR + 20, sq=2.4),
        oval(640, CAP - 130, 100, 90, sq=SQ_BALLOON),
        rect(460, 0, 460 + STEM, 360),
        balloon_rect(420, 240, 750, 240 + HAIR + 10),
    ]

@glyph('H', 800)
def _H():
    l0, l1 = 90, 90 + STEM
    r0, r1 = 800 - 90 - STEM, 800 - 90
    return [
        rect(l0, 0, l1, CAP),
        rect(r0, 0, r1, CAP),
        oval(l0 + 40, CAP, 90, 90, sq=SQ_BALLOON),
        oval(r0 + 40, CAP, 90, 90, sq=SQ_BALLOON),
        oval(l0 + 40, 0, 90, 90, sq=SQ_BALLOON),
        oval(r0 + 40, 0, 90, 90, sq=SQ_BALLOON),
        balloon_rect(l1 - LAP, 330, r0 + LAP, 330 + HAIR + 30),
    ]

@glyph('I', 400)
def _I():
    x0, x1 = (400 - STEM)/2.0, (400 + STEM)/2.0
    return [
        rect(x0, 0, x1, CAP),
        oval(400/2.0, CAP, 130, 80, sq=SQ_BALLOON),
        oval(400/2.0, 0, 130, 80, sq=SQ_BALLOON),
    ]

@glyph('J', 580)
def _J():
    x0, x1 = 340, 340 + STEM
    return [
        rect(x0, 180, x1, CAP),
        oval(x0 + 40, CAP, 100, 80, sq=SQ_BALLOON),
        band(250, 190, 190, 200, 180, 360, wside=STEM, wend=HAIR + 20, sq=2.3),
        oval(80, 240, 90, 90, sq=SQ_BALLOON),
    ]

@glyph('K', 780)
def _K():
    x0, x1 = 90, 90 + STEM
    return [
        rect(x0, 0, x1, CAP),
        oval(x0 + 40, CAP, 90, 90, sq=SQ_BALLOON),
        oval(x0 + 40, 0, 90, 90, sq=SQ_BALLOON),
        poly((x0 + 50, 320), (660, CAP), (750, CAP - 80), (x0 + 50, 200)),
        poly((x0 + 50, 160), (x0 + 100, 260), (730, 0), (620, 0)),
        oval(680, CAP - 40, 90, 90, sq=SQ_BALLOON),
        oval(670, 40, 90, 90, sq=SQ_BALLOON),
    ]

@glyph('L', 630)
def _L():
    x0, x1 = 90, 90 + STEM
    return [
        rect(x0, 0, x1, CAP),
        oval(x0 + 40, CAP, 90, 90, sq=SQ_BALLOON),
        balloon_rect(x0, -OVS, 600, HAIR + 40),
    ]

@glyph('M', 900)
def _M():
    w = STEM - 20
    return [
        rect(70, 0, 70 + w, CAP),
        rect(900 - 70 - w, 0, 900 - 70, CAP),
        poly((70, CAP), (70 + w + 40, CAP), (450 + w, 100), (450, 100)),
        poly((450, 100), (450 - w, 100), (900 - 70, CAP), (900 - 70 - w - 40, CAP)),
        oval(450, 100, 110, 110, sq=SQ_BALLOON),
        oval(70 + w/2.0, CAP, 80, 80, sq=SQ_BALLOON),
        oval(900 - 70 - w/2.0, CAP, 80, 80, sq=SQ_BALLOON),
        oval(70 + w/2.0, 0, 80, 80, sq=SQ_BALLOON),
        oval(900 - 70 - w/2.0, 0, 80, 80, sq=SQ_BALLOON),
    ]

@glyph('N', 800)
def _N():
    w = STEM - 20
    return [
        rect(80, 0, 80 + w, CAP),
        rect(800 - 80 - w, 0, 800 - 80, CAP),
        poly((80, CAP), (80 + w, CAP), (800 - 80, w + 40), (800 - 80, 0)),
        oval(80 + w/2.0, CAP, 80, 80, sq=SQ_BALLOON),
        oval(800 - 80 - w/2.0, 0, 80, 80, sq=SQ_BALLOON),
        oval(80 + w/2.0, 0, 80, 80, sq=SQ_BALLOON),
        oval(800 - 80 - w/2.0, CAP, 80, 80, sq=SQ_BALLOON),
    ]

@glyph('O', 820)
def _O():
    return balloon_donut(410, CAP/2.0, 370, CAP/2.0 + OVS, 160, CAP/2.0 - STEM + 10, sq=2.45, sqi=2.1)

@glyph('P', 740)
def _P():
    x0, x1 = 90, 90 + STEM
    return [
        rect(x0, 0, x1, CAP),
        oval(x0 + 40, CAP, 90, 90, sq=SQ_BALLOON),
        oval(x0 + 40, 0, 90, 90, sq=SQ_BALLOON),
    ] + cartoony_bowl_right(x1 - LAP, CAP, 280, 710, STEM, HAIR + 15, sq=2.35)

@glyph('Q', 840)
def _Q():
    return _O() + [
        poly((400, 80), (480, 160), (780, -60), (740, -140)),
        oval(760, -100, 90, 90, sq=SQ_BALLOON),
    ]

@glyph('R', 780)
def _R():
    x0, x1 = 90, 90 + STEM
    return [
        rect(x0, 0, x1, CAP),
        oval(x0 + 40, CAP, 90, 90, sq=SQ_BALLOON),
        oval(x0 + 40, 0, 90, 90, sq=SQ_BALLOON),
        poly((x0 + 50, 240), (x0 + 100, 320), (720, 0), (600, 0)),
        oval(660, 40, 90, 90, sq=SQ_BALLOON),
    ] + cartoony_bowl_right(x1 - LAP, CAP, 300, 730, STEM, HAIR + 15, sq=2.35)

@glyph('S', 720)
def _S():
    return [
        band(360, CAP * 0.72, 300, CAP * 0.28, 30, 250, wside=STEM, wend=HAIR + 10, sq=2.35),
        band(360, CAP * 0.28, 310, CAP * 0.29, 210, 430, wside=STEM, wend=HAIR + 10, sq=2.35),
        oval(600, CAP - 130, 100, 100, sq=SQ_BALLOON),
        oval(120, 140, 100, 100, sq=SQ_BALLOON),
    ]

@glyph('T', 720)
def _T():
    cx = 360
    x0, x1 = cx - STEM/2.0, cx + STEM/2.0
    return [
        rect(x0, 0, x1, CAP),
        oval(cx, 0, 100, 80, sq=SQ_BALLOON),
        balloon_rect(40, CAP - HAIR - 30, 680, CAP + OVS),
    ]

@glyph('U', 780)
def _U():
    l0, l1 = 90, 90 + STEM
    r0, r1 = 780 - 90 - STEM, 780 - 90
    return [
        rect(l0, 240, l1, CAP),
        rect(r0, 240, r1, CAP),
        oval(l0 + 40, CAP, 90, 90, sq=SQ_BALLOON),
        oval(r0 + 40, CAP, 90, 90, sq=SQ_BALLOON),
        band(390, 260, 300, 260 + OVS, 180, 360, wside=STEM, wend=HAIR + 20, sq=2.35),
    ]

@glyph('V', 760)
def _V():
    return [
        poly((40, CAP), (220, CAP), (420, 0), (240, 0)),
        poly((540, CAP), (720, CAP), (500, 0), (320, 0)),
        oval(130, CAP - 30, 90, 90, sq=SQ_BALLOON),
        oval(630, CAP - 30, 90, 90, sq=SQ_BALLOON),
        oval(380, 40, 100, 80, sq=SQ_BALLOON),
    ]

@glyph('W', 960)
def _W():
    return [
        poly((50, CAP), (210, CAP), (380, 0), (220, 0)),
        poly((220, 0), (380, 0), (570, CAP - 150), (410, CAP - 150)),
        poly((410, CAP - 150), (570, CAP - 150), (760, 0), (600, 0)),
        poly((600, 0), (760, 0), (930, CAP), (770, CAP)),
        oval(130, CAP - 30, 80, 80, sq=SQ_BALLOON),
        oval(830, CAP - 30, 80, 80, sq=SQ_BALLOON),
        oval(275, 40, 80, 80, sq=SQ_BALLOON),
        oval(735, 40, 80, 80, sq=SQ_BALLOON),
    ]

@glyph('X', 760)
def _X():
    return [
        poly((60, CAP), (240, CAP), (700, 0), (520, 0)),
        poly((520, CAP), (700, CAP), (240, 0), (60, 0)),
        oval(130, CAP - 30, 90, 90, sq=SQ_BALLOON),
        oval(630, CAP - 30, 90, 90, sq=SQ_BALLOON),
        oval(130, 30, 90, 90, sq=SQ_BALLOON),
        oval(630, 30, 90, 90, sq=SQ_BALLOON),
    ]

@glyph('Y', 760)
def _Y():
    cx = 380
    return [
        poly((60, CAP), (220, CAP), (cx + STEM/2.0, 320), (cx - STEM/2.0, 320)),
        poly((540, CAP), (700, CAP), (cx + STEM/2.0, 320), (cx - STEM/2.0, 320)),
        rect(cx - STEM/2.0, 0, cx + STEM/2.0, 350),
        oval(130, CAP - 30, 90, 90, sq=SQ_BALLOON),
        oval(630, CAP - 30, 90, 90, sq=SQ_BALLOON),
        oval(cx, 0, 90, 80, sq=SQ_BALLOON),
    ]

@glyph('Z', 720)
def _Z():
    return [
        balloon_rect(50, CAP - HAIR - 30, 670, CAP + OVS),
        poly((100, 0), (260, 0), (670, CAP - HAIR), (670, CAP - HAIR - 120)),
        balloon_rect(50, -OVS, 670, HAIR + 30),
    ]


# ---------------------------------------------------------------------------
# Lowercase Letters (a-z) - Matching Bubbly Style
# ---------------------------------------------------------------------------

@glyph('a', 680)
def _a():
    return [
        band(340, XH/2.0, 280, XH/2.0 + OVS, 0, 360, wside=STEM - 40, wend=HAIR - 30, sq=2.35),
        rect(500, 0, 500 + STEM - 30, XH),
        oval(500 + (STEM - 30)/2.0, 0, 80, 70, sq=SQ_BALLOON),
    ]

@glyph('b', 680)
def _b():
    x0, x1 = 80, 80 + STEM - 20
    return [
        rect(x0, 0, x1, CAP),
        oval(x0 + 35, CAP, 80, 80, sq=SQ_BALLOON),
        oval(x0 + 35, 0, 80, 80, sq=SQ_BALLOON),
    ] + cartoony_bowl_right(x1 - LAP, XH, 0, 640, STEM - 20, HAIR + 10, sq=2.35)

@glyph('c', 600)
def _c():
    return [
        band(310, XH/2.0, 260, XH/2.0 + OVS, 40, 320, wside=STEM - 20, wend=HAIR + 10, sq=2.35),
        oval(500, XH - 90, 80, 80, sq=SQ_BALLOON),
        oval(500, 90, 80, 80, sq=SQ_BALLOON),
    ]

@glyph('d', 680)
def _d():
    r0, r1 = 680 - 80 - (STEM - 20), 680 - 80
    return [
        rect(r0, 0, r1, CAP),
        oval(r0 + 35, CAP, 80, 80, sq=SQ_BALLOON),
        oval(r0 + 35, 0, 80, 80, sq=SQ_BALLOON),
        band(320, XH/2.0, 260, XH/2.0 + OVS, 0, 360, wside=STEM - 40, wend=HAIR - 30, sq=2.35),
    ]

@glyph('e', 640)
def _e():
    return [
        band(320, XH/2.0, 270, XH/2.0 + OVS, 20, 330, wside=STEM - 20, wend=HAIR + 10, sq=2.35),
        balloon_rect(100, XH/2.0 - HAIR/2.0, 580, XH/2.0 + HAIR/2.0),
        oval(520, 90, 80, 80, sq=SQ_BALLOON),
    ]

@glyph('f', 480)
def _f():
    x0, x1 = 140, 140 + STEM - 20
    return [
        rect(x0, 0, x1, CAP - 120),
        oval(x0 + 35, 0, 80, 80, sq=SQ_BALLOON),
        band(260, CAP - 160, 150, 160, 0, 180, wside=STEM - 20, wend=HAIR - 20, sq=2.3),
        balloon_rect(40, XH - HAIR/2.0 - 20, 440, XH + HAIR/2.0 + 20),
    ]

@glyph('g', 680)
def _g():
    return [
        band(340, XH/2.0, 260, XH/2.0 + OVS, 0, 360, wside=STEM - 40, wend=HAIR - 30, sq=2.35),
        rect(500, -100, 500 + STEM - 20, XH),
        band(340, -100, 200, 120, 180, 360, wside=STEM - 30, wend=HAIR - 30, sq=2.3),
        oval(140, -100, 80, 80, sq=SQ_BALLOON),
    ]

@glyph('h', 680)
def _h():
    l0, l1 = 80, 80 + STEM - 20
    r0, r1 = 680 - 80 - (STEM - 20), 680 - 80
    return [
        rect(l0, 0, l1, CAP),
        rect(r0, 0, r1, XH - 50),
        oval(l0 + 35, CAP, 80, 80, sq=SQ_BALLOON),
        oval(l0 + 35, 0, 80, 80, sq=SQ_BALLOON),
        oval(r0 + 35, 0, 80, 80, sq=SQ_BALLOON),
    ] + cartoony_arch(l0, l1, r0, r1, XH, HAIR + 10, y_join=XH - 200)

@glyph('i', 360)
def _i():
    x0, x1 = (360 - (STEM - 20))/2.0, (360 + (STEM - 20))/2.0
    return [
        rect(x0, 0, x1, XH),
        oval(360/2.0, 0, 70, 70, sq=SQ_BALLOON),
        oval(360/2.0, XH + 130, 90, 90, sq=SQ_BALLOON),
    ]

@glyph('dotlessi', 360)
def _dotlessi():
    x0, x1 = (360 - (STEM - 20))/2.0, (360 + (STEM - 20))/2.0
    return [
        rect(x0, 0, x1, XH),
        oval(360/2.0, 0, 70, 70, sq=SQ_BALLOON),
        oval(360/2.0, XH, 70, 70, sq=SQ_BALLOON),
    ]

@glyph('j', 400)
def _j():
    x0, x1 = 220, 220 + STEM - 20
    return [
        rect(x0, -100, x1, XH),
        oval(x0 + 35, XH + 130, 90, 90, sq=SQ_BALLOON),
        band(140, -100, 120, 120, 180, 360, wside=STEM - 30, wend=HAIR - 30, sq=2.3),
        oval(20, -100, 70, 70, sq=SQ_BALLOON),
    ]

@glyph('k', 660)
def _k():
    x0, x1 = 80, 80 + STEM - 20
    return [
        rect(x0, 0, x1, CAP),
        oval(x0 + 35, CAP, 80, 80, sq=SQ_BALLOON),
        oval(x0 + 35, 0, 80, 80, sq=SQ_BALLOON),
        poly((x0 + 30, XH/2.0 - 50), (x0 + 30, XH/2.0 + 30), (640, XH - 70), (560, XH)),
        poly((x0 + 30, XH/2.0 - 80), (x0 + 50, XH/2.0), (620, 0), (520, 0)),
        oval(580, XH - 30, 75, 75, sq=SQ_BALLOON),
        oval(570, 35, 75, 75, sq=SQ_BALLOON),
    ]

@glyph('l', 360)
def _l():
    x0, x1 = (360 - (STEM - 20))/2.0, (360 + (STEM - 20))/2.0
    return [
        rect(x0, 0, x1, CAP),
        oval(360/2.0, CAP, 75, 75, sq=SQ_BALLOON),
        oval(360/2.0, 0, 75, 75, sq=SQ_BALLOON),
    ]

@glyph('m', 920)
def _m():
    w = STEM - 30
    l0, l1 = 70, 70 + w
    m0, m1 = 460 - w/2.0, 460 + w/2.0
    r0, r1 = 920 - 70 - w, 920 - 70
    return [
        rect(l0, 0, l1, XH),
        rect(m0, 0, m1, XH - 40),
        rect(r0, 0, r1, XH - 40),
        oval(l0 + w/2.0, 0, 65, 65, sq=SQ_BALLOON),
        oval(m0 + w/2.0, 0, 65, 65, sq=SQ_BALLOON),
        oval(r0 + w/2.0, 0, 65, 65, sq=SQ_BALLOON),
    ] + cartoony_arch(l0, l1, m0, m1, XH, HAIR, y_join=XH - 170) \
      + cartoony_arch(m0, m1, r0, r1, XH, HAIR, y_join=XH - 170)

@glyph('n', 660)
def _n():
    l0, l1 = 80, 80 + STEM - 20
    r0, r1 = 660 - 80 - (STEM - 20), 660 - 80
    return [
        rect(l0, 0, l1, XH),
        rect(r0, 0, r1, XH - 40),
        oval(l0 + 35, 0, 75, 75, sq=SQ_BALLOON),
        oval(r0 + 35, 0, 75, 75, sq=SQ_BALLOON),
    ] + cartoony_arch(l0, l1, r0, r1, XH, HAIR, y_join=XH - 180)

@glyph('o', 660)
def _o():
    return balloon_donut(330, XH/2.0, 290, XH/2.0 + OVS, 130, XH/2.0 - HAIR - 10, sq=2.45, sqi=2.1)

@glyph('p', 680)
def _p():
    x0, x1 = 80, 80 + STEM - 20
    return [
        rect(x0, -180, x1, XH),
        oval(x0 + 35, -180, 80, 80, sq=SQ_BALLOON),
        oval(x0 + 35, XH, 80, 80, sq=SQ_BALLOON),
    ] + cartoony_bowl_right(x1 - LAP, XH, 0, 640, STEM - 20, HAIR + 10, sq=2.35)

@glyph('q', 680)
def _q():
    r0, r1 = 680 - 80 - (STEM - 20), 680 - 80
    return [
        rect(r0, -180, r1, XH),
        oval(r0 + 35, -180, 80, 80, sq=SQ_BALLOON),
        oval(r0 + 35, XH, 80, 80, sq=SQ_BALLOON),
        band(320, XH/2.0, 260, XH/2.0 + OVS, 0, 360, wside=STEM - 40, wend=HAIR - 30, sq=2.35),
    ]

@glyph('r', 520)
def _r():
    x0, x1 = 80, 80 + STEM - 20
    return [
        rect(x0, 0, x1, XH),
        oval(x0 + 35, 0, 75, 75, sq=SQ_BALLOON),
        band(250, XH - 120, 170, 130, 0, 150, wside=STEM - 60, wend=HAIR - 50, sq=2.3),
        oval(420, XH - 30, 75, 75, sq=SQ_BALLOON),
    ]

@glyph('s', 580)
def _s():
    return [
        band(290, XH * 0.72, 230, XH * 0.28, 30, 250, wside=STEM - 20, wend=HAIR, sq=2.35),
        band(290, XH * 0.28, 240, XH * 0.29, 210, 430, wside=STEM - 20, wend=HAIR, sq=2.35),
        oval(480, XH - 90, 75, 75, sq=SQ_BALLOON),
        oval(100, 90, 75, 75, sq=SQ_BALLOON),
    ]

@glyph('t', 460)
def _t():
    x0, x1 = 130, 130 + STEM - 20
    return [
        rect(x0, 120, x1, CAP - 160),
        oval(x0 + 35, CAP - 160, 75, 75, sq=SQ_BALLOON),
        balloon_rect(30, XH - HAIR/2.0 - 20, 430, XH + HAIR/2.0 + 20),
        band(250, 140, 140, 140, 180, 360, wside=STEM - 60, wend=HAIR - 50, sq=2.3),
        oval(390, 230, 75, 75, sq=SQ_BALLOON),
    ]

@glyph('u', 660)
def _u():
    l0, l1 = 80, 80 + STEM - 20
    r0, r1 = 660 - 80 - (STEM - 20), 660 - 80
    return [
        rect(l0, 160, l1, XH),
        rect(r0, 0, r1, XH),
        oval(l0 + 35, XH, 75, 75, sq=SQ_BALLOON),
        oval(r0 + 35, XH, 75, 75, sq=SQ_BALLOON),
        oval(r0 + 35, 0, 75, 75, sq=SQ_BALLOON),
        band(330, 180, 250, 180 + OVS, 180, 360, wside=STEM - 20, wend=HAIR + 10, sq=2.35),
    ]

@glyph('v', 620)
def _v():
    return [
        poly((30, XH), (175, XH), (380, 0), (235, 0)),
        poly((445, XH), (590, XH), (385, 0), (240, 0)),
        oval(105, XH - 25, 75, 75, sq=SQ_BALLOON),
        oval(515, XH - 25, 75, 75, sq=SQ_BALLOON),
        oval(310, 35, 80, 70, sq=SQ_BALLOON),
    ]

@glyph('w', 840)
def _w():
    return [
        poly((40, XH), (180, XH), (320, 0), (180, 0)),
        poly((180, 0), (320, 0), (500, XH - 100), (360, XH - 100)),
        poly((360, XH - 100), (500, XH - 100), (680, 0), (540, 0)),
        poly((540, 0), (680, 0), (800, XH), (660, XH)),
        oval(110, XH - 25, 70, 70, sq=SQ_BALLOON),
        oval(730, XH - 25, 70, 70, sq=SQ_BALLOON),
    ]

@glyph('x', 620)
def _x():
    return [
        poly((50, XH), (190, XH), (570, 0), (430, 0)),
        poly((430, XH), (570, XH), (190, 0), (50, 0)),
        oval(120, XH - 25, 75, 75, sq=SQ_BALLOON),
        oval(500, XH - 25, 75, 75, sq=SQ_BALLOON),
        oval(120, 25, 75, 75, sq=SQ_BALLOON),
        oval(500, 25, 75, 75, sq=SQ_BALLOON),
    ]

@glyph('y', 640)
def _y():
    cx = 320
    return [
        poly((40, XH), (180, XH), (cx + (STEM-20)/2.0, 220), (cx - (STEM-20)/2.0, 220)),
        poly((460, XH), (600, XH), (cx + (STEM-20)/2.0, 220), (cx - (STEM-20)/2.0, 220)),
        rect(cx - (STEM - 20)/2.0, -100, cx + (STEM - 20)/2.0, 250),
        band(210, -100, 110, 110, 180, 360, wside=STEM - 40, wend=HAIR - 30, sq=2.3),
        oval(100, XH - 25, 75, 75, sq=SQ_BALLOON),
        oval(530, XH - 25, 75, 75, sq=SQ_BALLOON),
    ]

@glyph('z', 580)
def _z():
    return [
        balloon_rect(40, XH - HAIR - 20, 540, XH + OVS),
        poly((80, 0), (220, 0), (540, XH - HAIR), (540, XH - HAIR - 100)),
        balloon_rect(40, -OVS, 540, HAIR + 20),
    ]


# ---------------------------------------------------------------------------
# Numbers (0-9)
# ---------------------------------------------------------------------------

@glyph('zero', 760)
def _zero():
    return balloon_donut(380, CAP/2.0, 330, CAP/2.0 + OVS, 130, CAP/2.0 - STEM, sq=2.45, sqi=2.1)

@glyph('one', 480)
def _one():
    cx = 260
    return [
        rect(cx - STEM/2.0, 0, cx + STEM/2.0, CAP),
        poly((80, CAP - 180), (cx - STEM/2.0, CAP), (cx - STEM/2.0 + LAP, CAP - 120), (140, CAP - 240)),
        oval(cx, 0, 110, 80, sq=SQ_BALLOON),
        oval(cx, CAP, 90, 80, sq=SQ_BALLOON),
    ]

@glyph('two', 720)
def _two():
    return [
        band(360, CAP - 240, 300, 240, 0, 190, wside=STEM, wend=HAIR + 20, sq=2.35),
        poly((60, 0), (230, 0), (660, CAP - 280), (600, CAP - 240)),
        balloon_rect(50, -OVS, 670, HAIR + 40),
    ]

@glyph('three', 720)
def _three():
    return [
        band(360, CAP - 190, 290, 190, -40, 180, wside=STEM, wend=HAIR + 10, sq=2.35),
        band(360, 190, 300, 190, 180, 400, wside=STEM, wend=HAIR + 10, sq=2.35),
        oval(120, CAP - 100, 90, 90, sq=SQ_BALLOON),
        oval(120, 100, 90, 90, sq=SQ_BALLOON),
    ]

@glyph('four', 760)
def _four():
    x0, x1 = 500, 500 + STEM
    return [
        rect(x0, 0, x1, CAP),
        poly((40, 140), (40, 220), (x0 + LAP, CAP), (x0 + LAP, 140)),
        balloon_rect(30, 140, 720, 140 + HAIR + 30),
        oval(x0 + STEM/2.0, 0, 90, 80, sq=SQ_BALLOON),
    ]

@glyph('five', 720)
def _five():
    return [
        balloon_rect(70, CAP - HAIR - 30, 650, CAP + OVS),
        rect(70, CAP - 300, 70 + STEM, CAP - HAIR),
        band(360, 220, 300, 220, -40, 190, wside=STEM, wend=HAIR + 10, sq=2.35),
        oval(120, 110, 90, 90, sq=SQ_BALLOON),
    ]

@glyph('six', 740)
def _six():
    return [band(390, CAP - 320, 320, 320, 90, 210, wside=STEM, wend=HAIR, sq=2.35)] + \
        balloon_donut(370, 230, 310, 230 + OVS, 130, 230 - STEM + 20, sq=2.4, sqi=2.1)

@glyph('seven', 720)
def _seven():
    return [
        balloon_rect(50, CAP - HAIR - 30, 670, CAP + OVS),
        poly((180, 0), (350, 0), (670, CAP - HAIR), (670, CAP - HAIR - 140)),
        oval(265, 0, 90, 70, sq=SQ_BALLOON),
    ]

@glyph('eight', 740)
def _eight():
    return balloon_donut(370, CAP - 200, 270, 200, 110, 200 - STEM + 30, sq=2.4, sqi=2.1) + \
        balloon_donut(370, 220, 310, 220, 130, 220 - STEM + 30, sq=2.4, sqi=2.1)

@glyph('nine', 740)
def _nine():
    return balloon_donut(370, CAP - 230, 310, 230 + OVS, 130, 230 - STEM + 20, sq=2.4, sqi=2.1) + \
        [band(350, 320, 320, 320, -90, 30, wside=STEM, wend=HAIR, sq=2.35)]


# ---------------------------------------------------------------------------
# Punctuation & Symbols
# ---------------------------------------------------------------------------

@glyph('period', 320)
def _period():
    return [oval(160, 80, 100, 100, sq=SQ_BALLOON)]

@glyph('comma', 320)
def _comma():
    return [
        oval(160, 100, 90, 90, sq=SQ_BALLOON),
        poly((100, 40), (160, 100), (220, -80), (120, -100)),
    ]

@glyph('exclam', 380)
def _exclam():
    return [
        poly((140, 260), (240, 260), (300, CAP), (80, CAP)),
        oval(190, CAP - 60, 110, 60, sq=SQ_BALLOON),
        oval(190, 80, 100, 100, sq=SQ_BALLOON),
    ]

@glyph('question', 620)
def _question():
    return [
        band(310, CAP - 220, 250, 220, -20, 180, wside=STEM, wend=HAIR, sq=2.35),
        poly((210, 260), (350, 260), (310 + 250 - STEM, CAP - 220), (310 - 50, CAP - 220)),
        oval(280, 80, 100, 100, sq=SQ_BALLOON),
    ]

@glyph('colon', 320)
def _colon():
    return [
        oval(160, 100, 80, 80, sq=SQ_BALLOON),
        oval(160, XH - 60, 80, 80, sq=SQ_BALLOON),
    ]

@glyph('semicolon', 320)
def _semicolon():
    return [
        oval(160, XH - 60, 80, 80, sq=SQ_BALLOON),
        oval(160, 100, 80, 80, sq=SQ_BALLOON),
        poly((100, 40), (160, 100), (220, -60), (120, -80)),
    ]

@glyph('quotesingle', 300)
def _quotesingle():
    return [
        poly((130, CAP - 200), (170, CAP - 200), (210, CAP), (90, CAP)),
        oval(150, CAP - 30, 60, 40, sq=SQ_BALLOON),
    ]

@glyph('quotedbl', 480)
def _quotedbl():
    return [
        poly((110, CAP - 200), (150, CAP - 200), (190, CAP), (70, CAP)),
        oval(130, CAP - 30, 60, 40, sq=SQ_BALLOON),
        poly((310, CAP - 200), (350, CAP - 200), (390, CAP), (270, CAP)),
        oval(330, CAP - 30, 60, 40, sq=SQ_BALLOON),
    ]

@glyph('hyphen', 440)
def _hyphen():
    return [balloon_rect(40, XH/2.0 - 50, 400, XH/2.0 + 50)]

@glyph('plus', 600)
def _plus():
    cx, cy = 300, XH/2.0 + 40
    return [
        balloon_rect(cx - STEM/2.0, cy - 200, cx + STEM/2.0, cy + 200),
        balloon_rect(cx - 200, cy - STEM/2.0, cx + 200, cy + STEM/2.0),
    ]

@glyph('equal', 540)
def _equal():
    return [
        balloon_rect(50, XH/2.0 + 40, 490, XH/2.0 + 120),
        balloon_rect(50, XH/2.0 - 120, 490, XH/2.0 - 40),
    ]

@glyph('slash', 500)
def _slash():
    return [
        poly((-60, -50), (320, CAP + 50), (440, CAP + 50), (60, -50)),
        oval(380, CAP + 25, 60, 60, sq=SQ_BALLOON),
        oval(0, -25, 60, 60, sq=SQ_BALLOON),
    ]

@glyph('space', 320)
def _space():
    return []


# ---------------------------------------------------------------------------
# Accents for Composites
# ---------------------------------------------------------------------------

@glyph('grave', 360)
def _grave():
    return [poly((40, CAP + 60), (140, CAP + 40), (220, CAP + 180), (60, CAP + 180))]

@glyph('acute', 360)
def _acute():
    return [poly((120, CAP + 40), (220, CAP + 60), (300, CAP + 180), (140, CAP + 180))]

@glyph('circumflex', 440)
def _circumflex():
    return [
        poly((220, CAP + 140), (300, CAP + 40), (400, CAP + 60), (220, CAP + 220)),
        poly((140, CAP + 40), (220, CAP + 140), (220, CAP + 220), (40, CAP + 60)),
    ]

@glyph('tilde', 440)
def _tilde():
    return [
        band(140, CAP + 120, 100, 60, 0, 180, wside=60, wend=40, sq=2.2),
        band(300, CAP + 120, 100, 60, 180, 360, wside=60, wend=40, sq=2.2),
    ]

@glyph('dieresis', 440)
def _dieresis():
    return [
        oval(120, CAP + 100, 60, 60, sq=SQ_BALLOON),
        oval(320, CAP + 100, 60, 60, sq=SQ_BALLOON),
    ]

@glyph('ring', 360)
def _ring():
    return balloon_donut(180, CAP + 100, 80, 80, 30, 30, sq=2.2, sqi=2.0)

@glyph('cedilla', 320)
def _cedilla():
    return [
        poly((120, -40), (100, -160), (220, -140), (160, 0)),
        oval(160, -140, 60, 60, sq=SQ_BALLOON),
    ]


# ---------------------------------------------------------------------------
# Sidebearings & Composites Registration
# ---------------------------------------------------------------------------

F.sidebearings.update({
    'A': (30, 30), 'B': (35, 30), 'C': (35, 25), 'D': (35, 30), 'E': (35, 30),
    'F': (35, 25), 'G': (35, 30), 'H': (35, 35), 'I': (30, 30), 'J': (25, 30),
    'K': (35, 25), 'L': (35, 30), 'M': (35, 35), 'N': (35, 35), 'O': (30, 30),
    'P': (35, 30), 'Q': (30, 30), 'R': (35, 30), 'S': (30, 30), 'T': (25, 25),
    'U': (35, 35), 'V': (20, 20), 'W': (25, 25), 'X': (25, 25), 'Y': (20, 20),
    'Z': (30, 30),
    'a': (25, 25), 'b': (30, 25), 'c': (25, 20), 'd': (25, 30), 'e': (25, 20),
    'f': (20, 20), 'g': (25, 25), 'h': (30, 25), 'i': (25, 25), 'j': (20, 25),
    'k': (30, 20), 'l': (25, 25), 'm': (30, 30), 'n': (30, 25), 'o': (25, 25),
    'p': (30, 25), 'q': (25, 30), 'r': (25, 20), 's': (25, 25), 't': (20, 20),
    'u': (25, 25), 'v': (20, 20), 'w': (20, 20), 'x': (20, 20), 'y': (20, 20),
    'z': (25, 25),
    'zero': (30, 30), 'one': (25, 25), 'two': (25, 25), 'three': (25, 25),
    'four': (25, 25), 'five': (25, 25), 'six': (30, 25), 'seven': (25, 25),
    'eight': (30, 30), 'nine': (25, 30),
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

# Kerning pairs for tight comic spacing
F.kern += [
    ("A", "V W Y T O Q C", -50),
    ("V W Y", "A a e o c", -60),
    ("T", "A a e o c r", -70),
    ("P F K", "A a e o", -40),
    ("L", "T V W Y", -50),
]


if __name__ == "__main__":
    sys.exit(F.cli())
