# AGENTS.md

Working notes for coding agents. Human docs in [README.md](README.md).

**Read this file and `scripts/glyphlib.py`. That is enough to draw a font.**
Do not read `scripts/draw_gravitas.py` end to end — it is 1,400 lines of a
finished face. When you need to see how one letter was solved, grep it:
`grep -n "@glyph('S'" -A 12 scripts/draw_gravitas.py`.

## The two paths

| goal | entry point | interpreter |
| --- | --- | --- |
| draw letterforms in code | `scripts/draw_template.py` (copy it) | `ffpython` |
| trace an image of a glyph grid | `scripts/make_font.py` | dispatches both |

`ffpython` = anything that can `import fontforge`. On Windows that is
`fontforge\bin\ffpython.exe`; on Linux, system `python3`. **Pillow lives on
the system Python and the `fontforge` module lives on FontForge's. They are
different builds and cannot share packages. Never pip install into ffpython.**

---

# Drawing

## The model

A glyph is a **pile of overlapping solid pieces** welded by `removeOverlap`.
Counters are not drawn — they are whatever the union leaves empty. Only a
free-standing ring (o, O, 0) needs an explicit reversed inner contour via
`hole()`.

So `n` is: left stem rect + right stem rect + an arch band + three serif
slabs. Not one 60-point outline.

## Contour format

```python
[('m', (x, y)), ('l', (x, y)), ('c', (cx1, cy1), (cx2, cy2), (x, y)), ...]
```

Element 0 is the move. **Explicitly closed**: the last segment ends on the
start point. Solids clockwise, holes counter-clockwise, y up. A glyph function
returns a *list* of contours.

## glyphlib API

```python
poly(*pts)                     # closed polygon through pts
rect(x0, y0, x1, y1)
oval(cx, cy, rx, ry, sq=2.0)   # sq 2 = ellipse, 2.1 = slightly squarer
band(cx, cy, rx, ry, t0, t1,   # an arc of a stroke: outer arc out, inner back
     wside=, wend=,            #   thickness at the horizontal / vertical ends
     rxi=, ryi=, cxi=, cyi=,   #   or state the inner ellipse outright
     sq=, sqi=)                #   offsetting cxi/cyi tapers the stroke
band_ends(... , t, ...)        # -> (outer_point, inner_point) at t
arc(cx, cy, rx, ry, t0, t1, sq)   # bare segments, to splice into a contour
bracket(cx, cy, dx, dy)        # concave fillet in the corner at (cx,cy)
stroke(line, w, y0, y1)        # slanted stroke, horizontal thickness w
Line(p0, p1); line.x(y); line.shift(dx); xsect(a, b)   # x = f(y)
hole(c) cw(c) ccw(c) rev(c)
move(c,dx,dy) moveall(cs,dx,dy) flipx(c,axis) flipy(c,axis) bbox(cs)
```

`t` is **degrees, counter-clockwise from +x**. `wside`/`wend` give vertical
stress for free: thick at the sides, thin at top and bottom.

## Recipes

| letter kind | build |
| --- | --- |
| I l i | `rect` stem + `foot()` top and bottom |
| O o 0 | `oval` + `hole(oval(smaller))` |
| B D P R b p | stem `rect` + `bowl_right()` |
| d q | stem `rect` + `bowl_left()` |
| n m h | two stem rects + `arch()` |
| u | same, `arch(..., up=False)` |
| C c e | `band` over an arc range + a wedge `poly` at each terminal |
| S s | two flattened bowls + a quad joining their ends (see `sshape`) |
| A V W X Y | `Line` + `xsect` for the edges, one `poly` for the silhouette |
| accents | draw the mark once as its own glyph; `F.accents` composes it |

`foot`, `bowl_right`, `arch` are in `draw_template.py` — copy them into your
face and tune the constants. They are a face's own brushes, not library code.

## Assembly

```python
from fontbuild import Font
F = Font("My Face", em=1000, ascent=800, descent=200)
F.cap_height, F.x_height = 700, 500        # accent placement uses these
glyph = F.glyph

@glyph('A', 722)          # width is a fallback; sidebearings override it
def _A(): return [...]

F.sidebearings.update({'A': (12, 12)})     # (left, right), measured to the ink
F.accents.update({'A': 'grave acute circumflex tilde dieresis ring'})
F.kern += [("A", "V W Y T", -60)]          # left, "right glyphs", units

if __name__ == "__main__":
    sys.exit(F.cli())
```

Glyph keys are either a single character or a name from `CHARMAP` /
`ACCENT_CP` in `fontbuild.py` (`period`, `ampersand`, `quoteright`, …).

**Sidebearings, not guessed widths.** Anything in `F.sidebearings` gets its
advance measured from the ink it actually drew. Flat-sided letters ~30 units,
round ~26, diagonals ~12 (their extreme is a serif tip that should interlock).

---

## Traps

These all cost real time. They are listed because the symptom never points at
the cause.

1. **Winding.** Author solids clockwise; `draw()` reverses on the way in
   because FontForge works in PostScript order. Hand `removeOverlap` a
   clockwise outer contour and it silently *subtracts* — you get missing
   serifs and filled counters, with no error.
2. **`flipx`/`flipy` preserve orientation** — they reverse internally. Do not
   add your own `rev()` after mirroring, or a mirrored bowl becomes a hole.
   (This is what turned `q`'s bowl into a void.)
3. **Never lay an edge flush.** Coincident or tangent edges break
   `removeOverlap` — the glyph comes out truncated, or as one open contour.
   Bury every join ~8 units inside the piece it lands on. Bowls attach *inside*
   the stem, arches die *inside* both stems.
4. **Polygon vertex order is around the perimeter**, not side by side. Listing
   `(topR, topL, botR, botL)` gives a silent bow-tie that surfaces much later
   as "self-intersecting". `7` and `TM` both had one.
5. **Arc sweep direction.** `180 → 330` goes round the bottom; `180 → -30` is
   the same end point the other way, over the top. Getting this backwards puts
   `t`'s tail above the baseline.
6. **Superellipse tangents.** For `sq > 2` the parametric speed is infinite
   where the curve crosses an axis. glyphlib solves control points from the
   arc midpoint instead; do not write your own tangent math.
7. **The cleanup order in `fontbuild.clean()` is load-bearing.** `round()`
   pushes nearly-touching edges across each other, so `removeOverlap` must run
   *after* the snap — and nothing may round after `correctDirection`.
8. **`removeOverlap` can leave a contour open.** An open contour is reported as
   "wrong direction". `tidy()` closes them and drops zero-area slivers.

Expected, not defects: composites overlap their references (the cedilla is
meant to touch its C), and accented capitals sit above the em ascent.

## Verify

A build that prints `183 glyphs` can still be visually wrong. Every time:

```bash
ffpython scripts/draw_myface.py --out output/MyFace.ttf
python scripts/proof.py --font output/MyFace.ttf --out output/proof.png --cols 13
ffpython scripts/inspect_font.py --font output/MyFace.ttf
```

**Then look at `proof.png`.** It is the only check that catches a font that is
valid but ugly. `--chars "abg" --size 260` zooms one problem glyph.
`compare.py --a yours.ttf --b times.ttf` is the honest test of weight and
colour at reading size.

`scripts/dbg_glyph.py` dumps a glyph's parts, their areas and bounding boxes,
and the contour count at each cleanup stage — reach for it when a glyph
vanishes or fills in.

## Working efficiently

- Draw a handful of glyphs, build, proof, *then* do the rest. Do not write 80
  glyphs against an unverified pipeline.
- Fix by category. If `b` is wrong, `d p q` are wrong the same way.
- The proof PNG is cheaper to read than the code. Look before you reason.

---

# Tracing (image path)

Uniform grid, one char per cell, grid fills the image **exactly**, every glyph
on a shared baseline at 80% of cell height. `--chars` lists cell contents in
reading order; `--cols` sets grid width.

```powershell
python scripts/make_font.py --sheet input/sheet.png --out output/MyFont.ttf --family "My Font"
```

- **Quoting `--chars`.** The default set contains `'` and `"`. PowerShell:
  single quotes, apostrophe doubled — `'ABC...!?''"-()'`. The bash form is a
  parse error there. Easiest: omit `--chars`.
- **`!! GRID LOOKS MISALIGNED` means fix the input**, usually by cropping the
  margin off. Never compensate with `--baseline`; that shifts all rows equally
  and this is per-row drift.
- Regression fixtures, all 73/73 with no serious defects: `input/sheet_clean.png`
  → SheetSerif, `input/sheet_rough.png` → WobbleHand,
  `input/samurai/brush_sheet.png` → RoninBrush. Rebuild all three if you touch
  `prepare_glyphs.py` or `build_font.py`.

---

# The specimen page (`web/`)

Standard library Python plus three static files. No npm, no framework, no
build step — keep it that way.

```bash
python web/server.py --port 8000
```

`GET /api/fonts` lists, `POST /api/fonts?name=X.ttf` takes raw bytes,
`GET /fonts/X.ttf` serves. Uploads are validated on sfnt magic, capped at 8 MB
and 250 files, and the filename must be a bare name. Static assets are matched
by shape (`^[A-Za-z0-9_-]+\.(html|js|css|svg|ico|png)$`) so nothing else beside
`server.py` is reachable.

Two pages, sharing `fontkit.js` — the font list, `FontFace` loading, the sfnt
parser, upload and drag-drop. The active font is remembered in `localStorage`,
so it follows you between them.

- `index.html` + `app.js` — the specimen tool. Dense panels, tiny functional
  labels, no hero, no descriptive copy, no decorative whitespace. Readouts come
  from parsing `head`/`hhea`/`OS/2`/`name`/`cmap`, not from CSS. **Keep
  additions in that register.**
- `showcase.html` + `showcase.css`/`showcase.js` — the same font in three
  realistic contexts (blog, neo-brutalist component sheet, dashboard). These
  *are* meant to look designed; each commits to its own palette. Demos are
  static markup toggled by `data-demo` on `#stage`, so there is no templating
  to reason about. Keep them to one screen each.

All four views appear in one nav on both pages. Which demo is showing lives in
the URL hash (`showcase.html#blog|#brutal|#dash`), so each is linkable and the
back button works; switching does not reload, so the font stays loaded.

## Deployment (this repo's own instance)

Live at **https://fontmaker.philippeho.dev** — Coolify app
`k8dsmh7rz92ggnus56ew69r5` on the Hetzner box, Dockerfile build pack, base
directory `/web`, port 8000, host directory
`/home/phil/app-data/fontmaker/fonts` mounted at `/data/fonts`.

**Releases are manual — there is no webhook, so a push does not deploy.**
After pushing:

```powershell
. C:\Users\phili\.config\coolify\env.ps1
$h = @{ Authorization = "Bearer $env:COOLIFY_TOKEN" }
Invoke-RestMethod -Uri "$env:COOLIFY_URL/api/v1/deploy?uuid=k8dsmh7rz92ggnus56ew69r5" -Headers $h -Method Post
```

Uploaded fonts live on the host, not in the image, so they survive a redeploy
and can be added or removed over SSH. The Coolify persistent-storage API wants
`type: "persistent"` — `volume`, `bind` and `directory` are all rejected, and
the endpoint is absent from the published OpenAPI spec.
