# fontmaker

Make a real, installable `.ttf` from a script — and look at it in a browser.

Two ways in:

| | input | good for |
| --- | --- | --- |
| **draw** | Python that describes the letterforms | text faces, anything that has to be *correct* |
| **trace** | an image of a glyph grid | hand-drawn, scanned or AI-generated display faces |

Both end at FontForge, which does the outline welding and writes the file.

`web/` is a specimen page: pick a font, or drop one on it, and see it in every
form that matters at once.

---

## Install

You need Python 3 and **FontForge with its Python module**.

- **Windows** — install FontForge and use its bundled interpreter,
  `fontforge\bin\ffpython.exe`. The repo expects it at `fontforge/` if you
  vendor it there (that directory is gitignored; it is ~120 MB).
- **Linux** — `apt install fontforge python3-fontforge`, then plain `python3`
  can `import fontforge`.
- **macOS** — `brew install fontforge`.

Anywhere `ffpython` appears below, substitute whichever interpreter can
`import fontforge`. Check with:

```bash
python -c "import fontforge; print(fontforge.version())"
```

The tracing path additionally needs Pillow (`pip install Pillow`), and the
proof/specimen renderers need it too. Those run on the *system* Python, not on
FontForge's — the two cannot share packages.

---

## Draw a font

```bash
fontforge/bin/ffpython.exe scripts/draw_gravitas.py --out output/Gravitas.ttf
```

That builds **Gravitas Text**, a 183-glyph transitional serif, from nothing but
coordinates. It is the worked example. To start a new face:

```bash
cp scripts/draw_template.py scripts/draw_myface.py
fontforge/bin/ffpython.exe scripts/draw_myface.py --out output/MyFace.ttf
```

The template builds as-is and demonstrates one of each construction pattern —
serifed stem, ring, bowl on a stem, diagonal pair, arch. Fill in the rest of
the alphabet the same way.

Then **look at it**, because a font that builds can still be wrong:

```bash
python scripts/proof.py --font output/MyFace.ttf --out output/proof.png --cols 13
python scripts/render_specimen.py --font output/MyFace.ttf --out output/spec.png
python scripts/compare.py --a output/MyFace.ttf --b C:/Windows/Fonts/times.ttf --out output/cmp.png
fontforge/bin/ffpython.exe scripts/inspect_font.py --font output/MyFace.ttf
```

`proof.py` is the microscope — one big glyph per cell with baseline, x-height
and cap guides. `inspect_font.py` catches structural faults. `compare.py`
stacks your face against a reference at reading sizes, which is the only
honest test of weight and colour.

### How it works

A glyph is a **pile of overlapping solid pieces** — stems, arcs, serif slabs,
bracket fillets — which FontForge's `removeOverlap` welds into one outline.
Counters are not drawn; they are whatever the union leaves empty. This is much
more forgiving than stating each outline exactly, and it is why a letter is
usually a dozen short lines rather than a hundred coordinates.

- `scripts/glyphlib.py` — geometry. Superellipse arcs fitted to cubics,
  slanted strokes, and `bracket()`, the concave fillet that makes a serif look
  drawn rather than glued on. No FontForge import; pure Python.
- `scripts/fontbuild.py` — assembly. Glyph naming, the cleanup sequence,
  measured sidebearings, accent composites, kerning, vertical metrics.
- `scripts/draw_*.py` — one file per face: metrics, its own brushes, and the
  glyphs.

`AGENTS.md` is the compact reference — the whole API and every trap worth
knowing, in a couple of pages. Read that rather than the 1,400-line example.

---

## Trace a font from an image

A single image holding a **uniform grid of cells**, one character per cell,
every glyph on a shared baseline. The grid must fill the image exactly.

```bash
python scripts/make_test_sheet.py --out input/sheet.png
python scripts/make_font.py --sheet input/sheet.png --out output/MyFont.ttf --family "My Font"
```

`make_font.py` runs the whole pipeline and dispatches each stage to the right
interpreter. `make_brush_sheet.py` paints a sumi-e style sheet procedurally if
you want a display face without an image model.

**Sheets from image models almost always need cropping first** — they render
with a margin, which makes every computed cell slightly too large and walks the
baseline down the page. The pipeline detects this and prints
`!! GRID LOOKS MISALIGNED`. Crop the image; do not compensate with
`--baseline`.

A photo of a sign is **not** a glyph sheet: it is not a grid, it is
perspective-skewed and unevenly lit, and it holds only the letters on the sign.
Turning one into a font needs a crop/deskew/normalise/assemble step that does
not exist here yet.

---

## The specimen page

```bash
python web/server.py
# http://127.0.0.1:8000
```

Standard library only — no npm, no build step, no framework. Pick a font from
the dropdown, or drop a `.ttf` anywhere on the page to upload it. The metrics
and glyph coverage shown are parsed out of the file itself, not guessed.

Opened straight off disk (`file://web/index.html`) it still works, minus the
server-side font list: dropped fonts preview from memory.

### Deploy

```bash
docker compose -f web/compose.yaml up -d --build
```

The image is `python:3.12-alpine` plus four files. Uploads go to `/data/fonts`,
which is the only writable path and the only thing worth putting on a volume;
fonts baked into the image stay visible underneath it.

Behind Coolify: point it at this repo, build pack **Dockerfile**, base
directory `/web`, Dockerfile `/Dockerfile`, expose port **8000**, and add a
persistent storage mapping to `/data/fonts`. Uploads then land on the host and
survive a redeploy, and you can drop `.ttf` files straight into that directory
over SSH to add them to the dropdown.

Add `--read-only` to the command to serve the page without accepting uploads.
Leave it off and **anyone who can reach the URL can write files to that
directory** — bounded by an 8 MB per-file cap and a 250-file ceiling, but
still worth deciding on deliberately.

---

## Layout

```
scripts/
  glyphlib.py        geometry primitives            (no fontforge)
  fontbuild.py       outline -> .ttf                (needs fontforge)
  draw_template.py   starter for a new face
  draw_gravitas.py   worked example, 183 glyphs
  proof.py           per-glyph proof grid           (needs Pillow)
  render_specimen.py sample-text sheet              (needs Pillow)
  compare.py         your face vs a reference       (needs Pillow)
  inspect_font.py    structural QA                  (needs fontforge)
  make_font.py       image -> .ttf pipeline entry point
  prepare_glyphs.py  slice + trace a sheet
  build_font.py      assemble traced outlines
  make_test_sheet.py, make_brush_sheet.py, normalize_glyph_sheet.py
web/
  server.py index.html app.js style.css fonts/ Dockerfile compose.yaml
input/    glyph sheets
output/   built fonts and proofs (gitignored)
```

## Known limits

- One weight per script. No italics, no variable axes.
- Latin only.
- Kerning is a hand-written pair list, not a class-based table.
- The tracing path gives uniform sidebearings and no kerning at all.
