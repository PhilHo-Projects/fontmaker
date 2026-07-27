"""Turn a table of drawn outlines into an installable .ttf.

Runs under fontforge\\bin\\ffpython.exe. Everything font-format-shaped lives
here - glyph naming, outline cleanup, sidebearings, composites, kerning,
vertical metrics - so a face's own file contains nothing but its drawing.

Minimal use:

    from fontbuild import Font
    F = Font("My Face", em=1000, ascent=800, descent=200)

    @F.glyph('A', 722)          # width is a fallback; sidebearings win
    def _A():
        return [rect(0, 0, 100, 680)]

    if __name__ == "__main__":
        sys.exit(F.cli())

See AGENTS.md for the drawing side.
"""

import argparse
import os
import sys

import fontforge
import psMat

from glyphlib import rev

# Glyph names that are not a single character, and the codepoint they carry.
CHARMAP = {
    'space': 0x20, 'exclam': 0x21, 'quotedbl': 0x22, 'numbersign': 0x23,
    'dollar': 0x24, 'percent': 0x25, 'ampersand': 0x26, 'quotesingle': 0x27,
    'parenleft': 0x28, 'parenright': 0x29, 'asterisk': 0x2A, 'plus': 0x2B,
    'comma': 0x2C, 'hyphen': 0x2D, 'period': 0x2E, 'slash': 0x2F,
    'zero': 0x30, 'one': 0x31, 'two': 0x32, 'three': 0x33, 'four': 0x34,
    'five': 0x35, 'six': 0x36, 'seven': 0x37, 'eight': 0x38, 'nine': 0x39,
    'colon': 0x3A, 'semicolon': 0x3B, 'less': 0x3C, 'equal': 0x3D,
    'greater': 0x3E, 'question': 0x3F, 'at': 0x40,
    'bracketleft': 0x5B, 'backslash': 0x5C, 'bracketright': 0x5D,
    'asciicircum': 0x5E, 'underscore': 0x5F, 'grave': 0x60,
    'braceleft': 0x7B, 'bar': 0x7C, 'braceright': 0x7D, 'asciitilde': 0x7E,
    'cent': 0xA2, 'sterling': 0xA3, 'yen': 0xA5, 'section': 0xA7,
    'dieresis': 0xA8, 'copyright': 0xA9, 'registered': 0xAE,
    'macron': 0xAF, 'degree': 0xB0, 'acute': 0xB4, 'paragraph': 0xB6,
    'cedilla': 0xB8, 'circumflex': 0x2C6, 'tilde': 0x2DC, 'breve': 0x2D8,
    'dotaccent': 0x2D9, 'ring': 0x2DA, 'caron': 0x2C7, 'dotlessi': 0x131,
    'endash': 0x2013, 'emdash': 0x2014, 'quoteleft': 0x2018,
    'quoteright': 0x2019, 'quotesinglbase': 0x201A, 'quotedblleft': 0x201C,
    'quotedblright': 0x201D, 'quotedblbase': 0x201E, 'bullet': 0x2022,
    'ellipsis': 0x2026, 'trademark': 0x2122, 'euro': 0x20AC,
}

# base letter + accent -> codepoint, for the composites
ACCENT_CP = {
    'Agrave': 0xC0, 'Aacute': 0xC1, 'Acircumflex': 0xC2, 'Atilde': 0xC3,
    'Adieresis': 0xC4, 'Aring': 0xC5, 'Ccedilla': 0xC7, 'Egrave': 0xC8,
    'Eacute': 0xC9, 'Ecircumflex': 0xCA, 'Edieresis': 0xCB, 'Igrave': 0xCC,
    'Iacute': 0xCD, 'Icircumflex': 0xCE, 'Idieresis': 0xCF, 'Ntilde': 0xD1,
    'Ograve': 0xD2, 'Oacute': 0xD3, 'Ocircumflex': 0xD4, 'Otilde': 0xD5,
    'Odieresis': 0xD6, 'Ugrave': 0xD9, 'Uacute': 0xDA, 'Ucircumflex': 0xDB,
    'Udieresis': 0xDC, 'Yacute': 0xDD,
    'agrave': 0xE0, 'aacute': 0xE1, 'acircumflex': 0xE2, 'atilde': 0xE3,
    'adieresis': 0xE4, 'aring': 0xE5, 'ccedilla': 0xE7, 'egrave': 0xE8,
    'eacute': 0xE9, 'ecircumflex': 0xEA, 'edieresis': 0xEB, 'igrave': 0xEC,
    'iacute': 0xED, 'icircumflex': 0xEE, 'idieresis': 0xEF, 'ntilde': 0xF1,
    'ograve': 0xF2, 'oacute': 0xF3, 'ocircumflex': 0xF4, 'otilde': 0xF5,
    'odieresis': 0xF6, 'ugrave': 0xF9, 'uacute': 0xFA, 'ucircumflex': 0xFB,
    'udieresis': 0xFC, 'yacute': 0xFD, 'ydieresis': 0xFF,
    'Scaron': 0x160, 'scaron': 0x161, 'Zcaron': 0x17D, 'zcaron': 0x17E,
}

ACCENT_NAMES = ('grave acute circumflex tilde dieresis ring cedilla caron '
                'breve macron dotaccent').split()


def codepoint(name):
    if len(name) == 1:
        return ord(name)
    return CHARMAP.get(name, ACCENT_CP.get(name, -1))


def gname(name):
    """Glyph name for a table key: 'A' -> 'A', 'ampersand' -> 'ampersand'."""
    return name if len(name) > 1 else fontforge.nameFromUnicode(ord(name))


def draw(g, contours):
    """Emit contours through FontForge's pen.

    glyphlib authors solids clockwise; FontForge works in PostScript order
    (outer counter-clockwise), and removeOverlap believes it - hand it a
    clockwise outer contour and it quietly subtracts instead of unioning. So
    every contour is reversed on the way in.
    """
    pen = g.glyphPen()
    for c in [rev(x) for x in contours]:
        pen.moveTo(c[0][1])
        for seg in c[1:-1]:
            if seg[0] == 'l':
                pen.lineTo(seg[1])
            else:
                pen.curveTo(seg[1], seg[2], seg[3])
        last = c[-1]
        if last[0] == 'c':
            pen.curveTo(last[1], last[2], last[3])
        pen.closePath()
    pen = None


def tidy(g, min_extent=1.0):
    """Drop degenerate contours and re-close whatever removeOverlap left open.

    Both are invisible on their own, and both make correctDirection give up -
    which is where "wrong direction" and phantom "self-intersecting" reports
    come from.
    """
    layer = g.foreground
    keep, dropped, closed = [], 0, 0
    for c in layer:
        xs = [p.x for p in c]
        ys = [p.y for p in c]
        if not xs or min(max(xs) - min(xs), max(ys) - min(ys)) <= min_extent:
            dropped += 1
            continue
        if not c.closed:
            c.closed = True
            closed += 1
        keep.append(c)
    if not (dropped or closed):
        return 0
    rebuilt = fontforge.layer()
    rebuilt.is_quadratic = layer.is_quadratic
    for c in keep:
        rebuilt += c
    g.foreground = rebuilt
    return dropped


def clean(g):
    """The cleanup sequence. Do not reorder it - see AGENTS.md, Traps."""
    g.removeOverlap()
    g.simplify(0.4, ('setstarttoextremum', 'removesingletonpoints'))
    g.addExtrema("all")
    g.round()
    # Rounding to integers pushes nearly-touching edges across each other, so
    # the second overlap pass has to come after the snap - and nothing may
    # round after it, or correctDirection inherits the intersections.
    g.removeOverlap()
    tidy(g)
    g.correctDirection()


class Font(object):
    """Collects drawn glyphs and assembles them into a font."""

    def __init__(self, family, style="Regular", em=1000, ascent=800,
                 descent=200, version="1.000", copyright="",
                 vendor="FMKR", weight=400):
        self.family = family
        self.style = style
        self.em = em
        self.ascent = ascent
        self.descent = descent
        self.version = version
        self.copyright = copyright
        self.vendor = vendor
        self.weight = weight

        self.glyphs = {}          # name -> callable() -> [contour]
        self.widths = {}          # name -> advance width (fallback)
        self.sidebearings = {}    # name -> (left, right), measured to the ink
        self.kern = []            # (left, "r i g h t s", value)
        self.accents = {}         # base letter -> "grave acute ..."
        self.accent_gap = 24      # how far an accent clears its base
        self.ring_gap = 16
        self.cap_height = None    # for accent placement; defaults to bbox
        self.x_height = None

        # OS/2 and hhea. Defaults leave room for accented capitals.
        self.typo = (760, -240, 100)
        self.win = (980, 260)
        self.hhea = (960, -260, 0)

    # -- registration ----------------------------------------------------
    def glyph(self, name, width):
        """Decorator: register a glyph function under `name`."""
        def deco(fn):
            self.glyphs[name] = fn
            self.widths[name] = width
            return fn
        return deco

    # -- build -----------------------------------------------------------
    def _place(self, g, name, drew):
        sb = self.sidebearings.get(name)
        if sb and drew:
            b = g.boundingBox()
            g.transform(psMat.translate(sb[0] - b[0], 0))
            b = g.boundingBox()
            g.width = int(round(b[2] + sb[1]))
        else:
            g.width = self.widths[name]

    def _composites(self, font):
        made = 0
        for base, acclist in sorted(self.accents.items()):
            for acc in acclist.split():
                name = base + acc
                if name not in ACCENT_CP:
                    print("warn    : no codepoint for %s, skipped" % name)
                    continue
                # accents above an i or j go on the dotless form
                bn = gname(base)
                if base == 'i' and acc != 'cedilla' and 'dotlessi' in self.glyphs:
                    bn = 'dotlessi'
                if bn not in font or acc not in font:
                    print("warn    : %s needs %s + %s, skipped" % (name, bn, acc))
                    continue
                bb = font[bn].boundingBox()
                ab = font[acc].boundingBox()
                # centre on the base's ink, not on its advance
                dx = (bb[0] + bb[2]) / 2.0 - (ab[0] + ab[2]) / 2.0
                if acc == 'cedilla':
                    dy = 0            # hangs off the baseline instead
                else:
                    gap = self.ring_gap if acc == 'ring' else self.accent_gap
                    top = self.cap_height if base.isupper() else self.x_height
                    dy = top + gap - ab[1]
                g = font.createChar(ACCENT_CP[name], name)
                g.addReference(bn)
                g.addReference(acc, psMat.translate(int(round(dx)), int(round(dy))))
                g.width = font[bn].width
                made += 1
        return made

    def _kerning(self, font):
        if not self.kern:
            return
        font.addLookup("kern", "gpos_pair", (),
                       (("kern", (("latn", ("dflt",)),
                                  ("DFLT", ("dflt",)))),))
        font.addLookupSubtable("kern", "kern-1")
        for left, rights, value in self.kern:
            ln = gname(left)
            if ln not in font:
                continue
            for right in rights.split():
                rn = gname(right)
                if rn not in font:
                    continue
                font[ln].addPosSub("kern-1", rn, 0, 0, value, 0, 0, 0, 0, 0)

    def build(self, out, hint=True, quiet=False):
        font = fontforge.font()
        font.encoding = "UnicodeFull"
        font.em = self.em
        font.ascent = self.ascent
        font.descent = self.descent
        font.familyname = self.family
        font.fontname = self.family.replace(" ", "") + "-" + self.style
        font.fullname = "%s %s" % (self.family, self.style)
        font.weight = self.style
        font.version = self.version
        if self.copyright:
            font.copyright = self.copyright

        n = 0
        for name in sorted(self.glyphs):
            g = font.createChar(codepoint(name), gname(name))
            contours = self.glyphs[name]()
            if contours:
                draw(g, contours)
                clean(g)
            self._place(g, name, bool(contours))
            n += 1

        if self.cap_height is None:
            self.cap_height = font['H'].boundingBox()[3] if 'H' in font else 700
        if self.x_height is None:
            self.x_height = font['x'].boundingBox()[3] if 'x' in font else 500
        n += self._composites(font)

        try:
            self._kerning(font)
        except Exception as exc:
            print("warn    : kerning skipped (%s)" % exc)

        ta, td, tg = self.typo
        wa, wd = self.win
        ha, hd, hg = self.hhea
        font.os2_typoascent_add = False
        font.os2_typodescent_add = False
        font.os2_typoascent, font.os2_typodescent, font.os2_typolinegap = ta, td, tg
        font.os2_winascent_add = False
        font.os2_windescent_add = False
        font.os2_winascent, font.os2_windescent = wa, wd
        font.hhea_ascent_add = False
        font.hhea_descent_add = False
        font.hhea_ascent, font.hhea_descent, font.hhea_linegap = ha, hd, hg
        font.os2_use_typo_metrics = True
        font.os2_family_class = 0x0203
        font.os2_weight = self.weight
        font.os2_vendor = self.vendor

        if hint:
            try:
                font.selection.all()
                font.autoHint()
                font.autoInstr()
            except Exception as exc:
                print("warn    : hinting skipped (%s)" % exc)

        out = os.path.abspath(out)
        d = os.path.dirname(out)
        if d and not os.path.isdir(d):
            os.makedirs(d)
        font.generate(out)
        if not quiet:
            print("glyphs  : %d" % n)
            print("output  : %s (%d bytes)" % (out, os.path.getsize(out)))
        return out

    def cli(self, argv=None):
        ap = argparse.ArgumentParser(
            description="Build %s to a .ttf" % self.family)
        ap.add_argument("--out", default="output/%s-%s.ttf" % (
            self.family.replace(" ", ""), self.style))
        ap.add_argument("--family", default=self.family)
        ap.add_argument("--style", default=self.style)
        ap.add_argument("--no-hint", action="store_true",
                        help="skip the autohinter and TrueType instructor")
        args = ap.parse_args(argv)
        self.family, self.style = args.family, args.style
        self.build(args.out, hint=not args.no_hint)
        return 0
