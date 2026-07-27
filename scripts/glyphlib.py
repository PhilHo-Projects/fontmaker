"""Geometry primitives for drawing serif outlines directly, no image involved.

Pure python (no fontforge import), so it can be read by either interpreter.

A CONTOUR is a list of segments:

    [('m', (x, y)), ('l', (x, y)), ('c', (x1,y1), (x2,y2), (x,y)), ...]

Element 0 is always the move. Every contour is **explicitly closed**: the last
segment's end point equals the start point. That invariant is what makes rev()
and area() simple, so builders must honour it.

Winding: solid pieces clockwise, holes counter-clockwise (y-up). Use cw()/ccw()
rather than trusting the traversal order you happened to write.

The drawing model is union-of-parts: a letter is a pile of overlapping solid
pieces (stems, arcs, serif slabs, bracket fillets) and FontForge's removeOverlap
welds them. Counters that are fully enclosed by the union appear on their own -
only free-standing rings (o, O, 0) need an explicit reversed inner contour.
"""

import math

K = 0.5523  # circle-to-cubic constant


# --------------------------------------------------------------------------
# contour utilities
# --------------------------------------------------------------------------

def nodes(c):
    """On-curve points, without the duplicated closing point."""
    return [seg[-1] for seg in c[:-1]]


def area(c):
    """Signed area of the node polygon. Positive = counter-clockwise."""
    p = nodes(c)
    s = 0.0
    for i in range(len(p)):
        x0, y0 = p[i]
        x1, y1 = p[(i + 1) % len(p)]
        s += x0 * y1 - x1 * y0
    return s / 2.0


def rev(c):
    """Reverse a contour, preserving the explicit-closure invariant."""
    pts = [c[0][1]] + [seg[-1] for seg in c[1:]]   # pts[-1] == pts[0]
    out = [('m', pts[0])]
    for i in range(len(c) - 1, 0, -1):
        seg = c[i]
        target = pts[i - 1]
        if seg[0] == 'l':
            out.append(('l', target))
        else:
            out.append(('c', seg[2], seg[1], target))
    return out


def cw(c):
    return rev(c) if area(c) > 0 else c


def ccw(c):
    return rev(c) if area(c) < 0 else c


def hole(c):
    return ccw(c)


def move(c, dx, dy):
    out = []
    for seg in c:
        out.append((seg[0],) + tuple((x + dx, y + dy) for (x, y) in seg[1:]))
    return out


def moveall(cs, dx, dy):
    return [move(c, dx, dy) for c in cs]


def transpose(c):
    """Swap x and y. Used to reuse horizontal builders for vertical ones."""
    out = []
    for seg in c:
        out.append((seg[0],) + tuple((y, x) for (x, y) in seg[1:]))
    return out


def flipx(c, axis):
    """Mirror in x, preserving orientation - a mirrored solid is still a solid.

    Reflection alone flips the winding, which silently turns a mirrored bowl
    into a hole, so the contour is reversed back.
    """
    out = []
    for seg in c:
        out.append((seg[0],) + tuple((2 * axis - x, y) for (x, y) in seg[1:]))
    return rev(out)


def flipy(c, axis):
    """Mirror in y, preserving orientation. See flipx."""
    out = []
    for seg in c:
        out.append((seg[0],) + tuple((x, 2 * axis - y) for (x, y) in seg[1:]))
    return rev(out)


def bbox(cs):
    xs, ys = [], []
    for c in cs:
        for seg in c:
            for (x, y) in seg[1:]:
                xs.append(x)
                ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


# --------------------------------------------------------------------------
# straight shapes
# --------------------------------------------------------------------------

def poly(*pts):
    """Closed polygon through pts, clockwise."""
    c = [('m', tuple(pts[0]))]
    for p in pts[1:]:
        c.append(('l', tuple(p)))
    c.append(('l', tuple(pts[0])))
    return cw(c)


def rect(x0, y0, x1, y1):
    if x0 > x1:
        x0, x1 = x1, x0
    if y0 > y1:
        y0, y1 = y1, y0
    return poly((x0, y0), (x0, y1), (x1, y1), (x1, y0))


class Line(object):
    """A line expressed as x = f(y); handy for slanted stems."""

    def __init__(self, p0, p1):
        (self.x0, self.y0), (self.x1, self.y1) = p0, p1
        dy = self.y1 - self.y0
        self.slope = (self.x1 - self.x0) / dy if dy else 0.0

    def x(self, y):
        return self.x0 + self.slope * (y - self.y0)

    def shift(self, dx):
        return Line((self.x0 + dx, self.y0), (self.x1 + dx, self.y1))


def xsect(a, b):
    """Intersection of two Lines, as (x, y)."""
    dy = a.slope - b.slope
    y = (b.x0 - b.slope * b.y0 - a.x0 + a.slope * a.y0) / dy
    return (a.x(y), y)


def stroke(line, w, y0, y1):
    """Slanted stroke of horizontal thickness w, cut flat at y0 and y1."""
    r = line.shift(w)
    return poly((line.x(y0), y0), (line.x(y1), y1), (r.x(y1), y1), (r.x(y0), y0))


# --------------------------------------------------------------------------
# curved shapes
# --------------------------------------------------------------------------

def _pw(v, e):
    """Signed power, for superellipse sampling."""
    if v >= 0:
        return v ** e
    return -((-v) ** e)


def ept(cx, cy, rx, ry, t, sq=2.0):
    a = math.radians(t)
    e = 2.0 / sq
    return (cx + rx * _pw(math.cos(a), e), cy + ry * _pw(math.sin(a), e))


def _tangent(cx, cy, rx, ry, t, sq):
    """Unit tangent. Taken numerically and normalised on purpose: for sq > 2
    the parametric speed is infinite where the curve crosses an axis, but the
    direction there is still exactly horizontal/vertical, so normalising is
    what keeps the control points finite."""
    h = 1e-4
    a = ept(cx, cy, rx, ry, t + h, sq)
    b = ept(cx, cy, rx, ry, t - h, sq)
    dx, dy = a[0] - b[0], a[1] - b[1]
    n = math.hypot(dx, dy)
    return (dx / n, dy / n)


def _arc_segs(cx, cy, rx, ry, t0, t1, sq=2.0, maxstep=30.0):
    """Cubic segments along an ellipse (sq=2) or a squarer superellipse.

    Control-point distances are solved so the Bezier's midpoint lands on the
    true curve's midpoint, rather than derived from the parametric speed -
    same result for a circle, but well behaved for any sq.
    """
    span = t1 - t0
    n = max(1, int(math.ceil(abs(span) / maxstep)))
    step = span / n
    segs = []
    for i in range(n):
        u0 = t0 + i * step
        u1 = t0 + (i + 1) * step
        p0 = ept(cx, cy, rx, ry, u0, sq)
        p1 = ept(cx, cy, rx, ry, u1, sq)
        m = ept(cx, cy, rx, ry, (u0 + u1) / 2.0, sq)
        e0 = _tangent(cx, cy, rx, ry, u0, sq)
        e1 = _tangent(cx, cy, rx, ry, u1, sq)
        vx = (m[0] - (p0[0] + p1[0]) / 2.0) * 8.0 / 3.0
        vy = (m[1] - (p0[1] + p1[1]) / 2.0) * 8.0 / 3.0
        # solve  a*e0 - b*e1 = v
        det = -e0[0] * e1[1] + e1[0] * e0[1]
        if abs(det) < 1e-9:
            a = b = math.hypot(p1[0] - p0[0], p1[1] - p0[1]) / 3.0
        else:
            a = (vx * -e1[1] + e1[0] * vy) / det
            b = (e0[0] * vy - vx * e0[1]) / det
        c1 = (p0[0] + a * e0[0], p0[1] + a * e0[1])
        c2 = (p1[0] - b * e1[0], p1[1] - b * e1[1])
        segs.append(('c', c1, c2, p1))
    return segs


def arc(cx, cy, rx, ry, t0, t1, sq=2.0):
    """Bare cubic segments along an (super)ellipse - for splicing into a
    hand-built contour."""
    return _arc_segs(cx, cy, rx, ry, t0, t1, sq)


def oval(cx, cy, rx, ry, sq=2.0):
    c = [('m', ept(cx, cy, rx, ry, 0, sq))]
    c += _arc_segs(cx, cy, rx, ry, 0, 360, sq)
    return cw(c)


def band(cx, cy, rx, ry, t0, t1, wside=None, wend=None,
         rxi=None, ryi=None, cxi=None, cyi=None, sq=2.0, sqi=None):
    """An arc of a stroke: outer ellipse t0->t1, inner ellipse back again.

    Either give wside/wend (thickness at the horizontal / vertical extremes,
    i.e. vertical stress) or the inner ellipse outright. Offsetting the inner
    centre with cxi/cyi biases the weight to one side of the arc, which is how
    the asymmetric arches (a, f, r, t terminals) get their taper.
    """
    if rxi is None:
        rxi = rx - wside
    if ryi is None:
        ryi = ry - wend
    if cxi is None:
        cxi = cx
    if cyi is None:
        cyi = cy
    if sqi is None:
        sqi = sq
    p0 = ept(cx, cy, rx, ry, t0, sq)
    c = [('m', p0)]
    c += _arc_segs(cx, cy, rx, ry, t0, t1, sq)
    c.append(('l', ept(cxi, cyi, rxi, ryi, t1, sqi)))
    c += _arc_segs(cxi, cyi, rxi, ryi, t1, t0, sqi)
    c.append(('l', p0))
    return cw(c)


def band_ends(cx, cy, rx, ry, t, wside=None, wend=None,
              rxi=None, ryi=None, cxi=None, cyi=None, sq=2.0, sqi=None):
    """(outer, inner) points of a band's cross-section at parameter t."""
    if rxi is None:
        rxi = rx - wside
    if ryi is None:
        ryi = ry - wend
    if cxi is None:
        cxi = cx
    if cyi is None:
        cyi = cy
    if sqi is None:
        sqi = sq
    return ept(cx, cy, rx, ry, t, sq), ept(cxi, cyi, rxi, ryi, t, sqi)


def bracket(cx, cy, dx, dy, tension=0.42):
    """Concave fillet welding a horizontal edge to a vertical one.

    Corner at (cx, cy); the piece reaches dx horizontally and dy vertically
    (either sign). This is the single ingredient that makes a serif look drawn
    rather than stuck on.
    """
    p = (cx + dx, cy)
    q = (cx, cy + dy)
    c = [('m', (cx, cy)), ('l', p),
         ('c', (cx + tension * dx, cy), (cx, cy + tension * dy), q),
         ('l', (cx, cy))]
    return cw(c)
