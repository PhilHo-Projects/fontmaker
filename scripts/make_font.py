"""One-shot: glyph sheet image -> TTF.

Runs on the SYSTEM python. Handles the two-interpreter split itself - tracing
needs Pillow (system python), font assembly needs the fontforge module
(FontForge's bundled ffpython.exe).

    python scripts/make_font.py --sheet input/sheet.png --out output/MyFont.ttf \
        --chars "ABC...xyz" --cols 13
"""

import argparse
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUNDLED_FFPYTHON = os.path.join(ROOT, "fontforge", "bin", "ffpython.exe")

DEFAULT_CHARS = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
    "0123456789"
    ".,:;!?'\"-()"
)


def find_ffpython(explicit=None):
    for cand in (explicit, os.environ.get("FFPYTHON"), BUNDLED_FFPYTHON,
                 shutil.which("ffpython")):
        if cand and os.path.isfile(cand):
            return cand
    raise SystemExit(
        "ffpython not found. Install FontForge into %s or set FFPYTHON."
        % os.path.join(ROOT, "fontforge"))


def run(label, cmd):
    print("\n== %s ==" % label)
    print("  $ " + " ".join(('"%s"' % c if " " in c else c) for c in cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    for line in (result.stdout or "").splitlines():
        print("  " + line)
    if result.returncode != 0:
        sys.stderr.write(result.stderr or "")
        raise SystemExit("%s failed (exit %d)" % (label, result.returncode))
    if result.stderr.strip():
        for line in result.stderr.splitlines():
            print("  ! " + line)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sheet", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--chars", default=DEFAULT_CHARS)
    ap.add_argument("--cols", type=int, default=13)
    ap.add_argument("--baseline", type=float, default=0.8)
    ap.add_argument("--work", default=None, help="scratch dir (default: build/<fontname>)")
    ap.add_argument("--family", default=None)
    ap.add_argument("--style", default="Regular")
    ap.add_argument("--threshold", type=int, default=128)
    ap.add_argument("--polarity", choices=["auto", "dark-on-light", "light-on-dark"],
                    default="auto")
    ap.add_argument("--despeckle", type=int, default=4)
    ap.add_argument("--alphamax", type=float, default=1.0)
    ap.add_argument("--bleed-ratio", type=float, default=0.15)
    ap.add_argument("--sidebearing", type=int, default=45)
    ap.add_argument("--hint", action="store_true")
    ap.add_argument("--ffpython", default=None)
    args = ap.parse_args()

    stem = os.path.splitext(os.path.basename(args.out))[0]
    family = args.family or stem
    work = args.work or os.path.join(ROOT, "build", stem)
    ffpython = find_ffpython(args.ffpython)

    run("trace", [
        sys.executable, os.path.join(HERE, "prepare_glyphs.py"),
        "--sheet", args.sheet,
        "--work", work,
        "--chars", args.chars,
        "--cols", str(args.cols),
        "--baseline", str(args.baseline),
        "--threshold", str(args.threshold),
        "--polarity", args.polarity,
        "--despeckle", str(args.despeckle),
        "--alphamax", str(args.alphamax),
        "--bleed-ratio", str(args.bleed_ratio),
    ])

    build_cmd = [
        ffpython, os.path.join(HERE, "build_font.py"),
        "--spec", os.path.join(work, "glyphs.json"),
        "--out", args.out,
        "--family", family,
        "--style", args.style,
        "--sidebearing", str(args.sidebearing),
    ]
    if args.hint:
        build_cmd.append("--hint")
    run("build", build_cmd)

    print("\ndone: %s" % os.path.abspath(args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
