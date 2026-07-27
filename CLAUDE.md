# CLAUDE.md

Read [AGENTS.md](AGENTS.md) — it is the operating manual, and it is short on
purpose. Human docs in [README.md](README.md).

## The job

Make an installable `.ttf`, either by **drawing** it in Python or by **tracing**
an image of a glyph grid. Run from the repo root.

```powershell
# draw (copy scripts/draw_template.py first)
fontforge\bin\ffpython.exe scripts/draw_myface.py --out output/MyFace.ttf
python scripts/proof.py --font output/MyFace.ttf --out output/proof.png --cols 13

# trace
python scripts/make_font.py --sheet input/<sheet>.png --out output/<Name>.ttf --family "<Name>"
```

**Then look at `proof.png`.** A build that reports every glyph can still be
visually wrong; the proof is the only check that catches it. `inspect_font.py`
catches the structural faults.

## Rules

- **Two interpreters.** Pillow/numpy/scipy → system `python`. The `fontforge`
  module → `fontforge\bin\ffpython.exe`. Different builds, cannot share
  packages, don't pip into ffpython. `make_font.py` already dispatches.
- **Don't read `scripts/draw_gravitas.py` end to end** — 1,400 lines of a
  finished face. Grep the letter you need:
  `grep -n "@glyph('S'" -A 12 scripts/draw_gravitas.py`.
- **Don't reorder the cleanup in `fontbuild.clean()` or `build_font.py`.** The
  double `removeOverlap()` and the `addExtrema("all")` guard look redundant and
  are not — AGENTS.md, Traps.
- **Quoting `--chars`.** Default set has `'` and `"`. PowerShell: single quotes,
  doubled apostrophe → `'ABC...!?''"-()'`. The bash form is a parse error here.
  Easiest: omit `--chars`.
- **`!! GRID LOOKS MISALIGNED` means stop and fix the input**, usually by
  cropping the margin off. Never compensate with `--baseline` (that shifts all
  rows equally; this is per-row drift).
- **The specimen page is a tool, not a landing page.** Dense panels, tiny
  functional labels, no hero, no descriptive copy, no decorative whitespace.

## Working from a photo or a pasted image — READ THIS

**A photo does not work as input and there is no tool yet that makes it work.**
A photo of e.g. a street sign is not a grid, is perspective-skewed and unevenly
lit, and contains only the handful of letters on that sign.

Turning one into a font needs a step that doesn't exist: crop each letter,
deskew, normalise onto a shared baseline, assemble into a grid sheet, then fill
the missing characters. **Say this plainly and offer to build the assembler
rather than pretending the current pipeline handles it.** Either that, or draw
the face instead — that path is fully supported and gives a better result.

## State

- **Drawn:** `draw_gravitas.py` → Gravitas Text, 183 glyphs, no structural
  defects. `draw_template.py` builds a 7-glyph demo and is the starting point.
- **Traced:** three fixtures in `input/`, all 73/73 — `sheet_clean.png` →
  SheetSerif, `sheet_rough.png` → WobbleHand, `samurai/brush_sheet.png` →
  RoninBrush. Rebuild all three after touching `prepare_glyphs.py` or
  `build_font.py`. Specks on RoninBrush are dry-brush holes, not defects.

Known limits: one weight per script, Latin only, hand-written kern pairs. The
tracing path gives uniform sidebearings and no kerning.
