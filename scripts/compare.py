"""Stack the same text in two fonts so differences in weight, colour and
serif presence are obvious rather than remembered."""
import argparse
from PIL import Image, ImageDraw, ImageFont

TEXT = [
    ("Handgloves Quartz 38", 72),
    ("The quick brown fox jumps over", 34),
    ("the lazy dog. Reading a page of", 34),
    ("continuous text at 22 pixels is the", 22),
    ("only test that matters for a text face.", 22),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--labels", default="mine,reference")
    args = ap.parse_args()

    la, lb = args.labels.split(",")
    W = 1000
    block = sum(int(s * 1.42) for _t, s in TEXT) + 40
    img = Image.new("L", (W, block * 2 + 40), 255)
    d = ImageDraw.Draw(img)
    small = ImageFont.load_default()

    y = 10
    for path, label in ((args.a, la), (args.b, lb)):
        d.text((20, y), label, font=small, fill=128)
        y += 24
        for text, size in TEXT:
            f = ImageFont.truetype(path, size)
            d.text((24, y), text, font=f, fill=0)
            y += int(size * 1.42)
        y += 16
    img.save(args.out)
    print("compare : %s" % args.out)


if __name__ == "__main__":
    main()
