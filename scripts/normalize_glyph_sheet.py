"""Normalize an AI-generated glyph sheet into a strict uniform grid.

Image generators can draw the requested characters in the right order while
varying the horizontal pitch and baseline from row to row. This script detects
the white gaps between glyphs, assigns the expected number of glyphs per row,
recentres each one, and maps every source-row baseline to one target baseline.
"""

import argparse
import math
import os
import statistics

import numpy as np
from PIL import Image
from scipy import ndimage


DEFAULT_CHARS = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
    "0123456789"
    ".,:;!?'\"-()"
)

BASELINE_ANCHORS = set(".!?")
BASELINE_EXCLUSIONS = set("fgjpqy,;'\"-()")


def _projection_runs(row_image, threshold):
    mask = row_image.convert("L").point(lambda value: 255 if value < threshold else 0)
    occupied = [
        mask.crop((x, 0, x + 1, mask.height)).getbbox() is not None
        for x in range(mask.width)
    ]
    runs = []
    start = None
    for x, has_ink in enumerate(occupied):
        if has_ink and start is None:
            start = x
        elif not has_ink and start is not None:
            runs.append((start, x))
            start = None
    if start is not None:
        runs.append((start, row_image.width))
    return runs


def _merge_runs_to_count(runs, expected):
    runs = list(runs)
    if len(runs) < expected:
        raise ValueError(
            "found %d isolated ink groups, expected at least %d" % (len(runs), expected)
        )
    while len(runs) > expected:
        gap_index = min(
            range(len(runs) - 1),
            key=lambda index: runs[index + 1][0] - runs[index][1],
        )
        runs[gap_index : gap_index + 2] = [
            (runs[gap_index][0], runs[gap_index + 1][1])
        ]
    return runs


def _ink_bbox(image, threshold):
    mask = image.convert("L").point(lambda value: 255 if value < threshold else 0)
    return mask.getbbox()


def _extract_row_glyph(source, x0, x1, y0, y1, threshold):
    """Extract components belonging to one row while preserving descenders."""
    row_height = y1 - y0
    extension = row_height // 2
    crop_y0 = max(0, y0 - extension)
    crop_y1 = min(source.height, y1 + extension)
    origin_y = y0 - crop_y0

    gray = np.asarray(
        source.convert("L").crop((x0, crop_y0, x1, crop_y1))
    )
    labels, count = ndimage.label(
        gray < threshold, structure=np.ones((3, 3), dtype=np.uint8)
    )
    if count == 0:
        blank = Image.new("L", (x1 - x0, crop_y1 - crop_y0), 255)
        return blank, None, origin_y

    # A neighbouring row can leave a descender fragment inside the nominal
    # slice. Real glyph components reach into the middle 75% of their own row;
    # those short border fragments do not. Components selected here retain
    # their full shape, including any part extending beyond y1.
    core_start = origin_y + round(row_height * 0.25)
    core_end = min(labels.shape[0], origin_y + row_height)
    selected_labels = set(np.unique(labels[core_start:core_end]))
    selected_labels.discard(0)
    selected = np.isin(labels, list(selected_labels))
    cleaned = Image.fromarray(
        np.where(selected, 0, 255).astype(np.uint8), mode="L"
    )
    bbox = _ink_bbox(cleaned, threshold)
    if bbox is None:
        return cleaned, None, origin_y
    relative_bbox = (bbox[0], bbox[1] - origin_y, bbox[2], bbox[3] - origin_y)
    return cleaned, relative_bbox, origin_y


def _densest_bottom_cluster(values, tolerance):
    if not values:
        raise ValueError("cannot estimate a baseline from an empty row")
    ordered = sorted(values)
    candidates = []
    for start, low in enumerate(ordered):
        cluster = [value for value in ordered[start:] if value - low <= tolerance]
        candidates.append(cluster)
    best = min(
        candidates,
        key=lambda cluster: (-len(cluster), statistics.median(cluster)),
    )
    return statistics.median(best)


def _estimate_row_baseline(row_chars, bboxes, row_height):
    anchors = []
    for char, bbox in zip(row_chars, bboxes):
        if bbox is None:
            continue
        if (char.isalnum() and char not in BASELINE_EXCLUSIONS) or char in BASELINE_ANCHORS:
            anchors.append(bbox[3])
    if not anchors:
        anchors = [bbox[3] for bbox in bboxes if bbox is not None]
    return _densest_bottom_cluster(anchors, max(2, round(row_height * 0.04)))


def normalize_sheet(
    source,
    chars=DEFAULT_CHARS,
    cols=13,
    cell_size=300,
    baseline_frac=0.8,
    ink_threshold=160,
    glyph_scale=0.9,
):
    """Return a strict-grid copy of ``source`` with recentered, aligned glyphs."""
    rows = math.ceil(len(chars) / cols)
    if source.width < cols or source.height < rows:
        raise ValueError("source image is too small for the requested grid")

    source_row_height = source.height // rows
    target = Image.new("L", (cols * cell_size, rows * cell_size), 255)
    scale = (cell_size / float(source_row_height)) * glyph_scale
    target_baseline = cell_size * baseline_frac

    for row in range(rows):
        row_chars = chars[row * cols : min((row + 1) * cols, len(chars))]
        y0 = row * source_row_height
        y1 = (row + 1) * source_row_height
        row_image = source.crop((0, y0, source.width, y1)).convert("L")
        runs = _merge_runs_to_count(
            _projection_runs(row_image, ink_threshold), len(row_chars)
        )

        glyph_images = []
        glyph_bboxes = []
        row_origins = []
        for x0, x1 in runs:
            glyph_image, glyph_bbox, origin_y = _extract_row_glyph(
                source.convert("L"), x0, x1, y0, y1, ink_threshold
            )
            glyph_images.append(glyph_image)
            glyph_bboxes.append(glyph_bbox)
            row_origins.append(origin_y)

        source_baseline = _estimate_row_baseline(
            row_chars, glyph_bboxes, source_row_height
        )

        target_baseline_y = round(target_baseline)
        for col, (glyph_image, glyph_bbox, origin_y) in enumerate(
            zip(glyph_images, glyph_bboxes, row_origins)
        ):
            width = max(1, round(glyph_image.width * scale))
            paste_x = (cell_size - width) // 2
            cell = Image.new("L", (cell_size, cell_size), 255)

            split_y = max(
                1, min(glyph_image.height - 1, round(source_baseline + origin_y))
            )
            upper = glyph_image.crop((0, 0, glyph_image.width, split_y))
            upper_height = max(1, round(upper.height * scale))
            upper = upper.resize((width, upper_height), Image.Resampling.LANCZOS)
            upper_mask = Image.eval(upper, lambda value: 255 - value)
            cell.paste(
                Image.new("L", upper.size, 0),
                (paste_x, target_baseline_y - upper_height),
                upper_mask,
            )

            descender_depth = max(
                0.0, (glyph_bbox[3] if glyph_bbox else source_baseline) - source_baseline
            )
            available_descender = max(1.0, cell_size - 1 - target_baseline_y)
            lower_scale = scale
            if descender_depth:
                lower_scale = min(scale, available_descender / descender_depth)
            lower = glyph_image.crop(
                (0, split_y, glyph_image.width, glyph_image.height)
            )
            lower_height = max(1, round(lower.height * lower_scale))
            lower = lower.resize((width, lower_height), Image.Resampling.LANCZOS)
            lower_mask = Image.eval(lower, lambda value: 255 - value)
            cell.paste(
                Image.new("L", lower.size, 0),
                (paste_x, target_baseline_y),
                lower_mask,
            )
            target.paste(cell, (col * cell_size, row * cell_size))

    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sheet", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--chars", default=DEFAULT_CHARS)
    parser.add_argument("--cols", type=int, default=13)
    parser.add_argument("--cell-size", type=int, default=300)
    parser.add_argument("--baseline", type=float, default=0.8)
    parser.add_argument("--threshold", type=int, default=160)
    parser.add_argument("--glyph-scale", type=float, default=0.9)
    args = parser.parse_args()

    source = Image.open(args.sheet)
    normalized = normalize_sheet(
        source,
        chars=args.chars,
        cols=args.cols,
        cell_size=args.cell_size,
        baseline_frac=args.baseline,
        ink_threshold=args.threshold,
        glyph_scale=args.glyph_scale,
    )
    out = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    normalized.save(out)
    print("source  : %s (%dx%d)" % (args.sheet, source.width, source.height))
    print("grid    : %d cols, %dpx cells, baseline %.2f" % (
        args.cols, args.cell_size, args.baseline
    ))
    print("output  : %s (%dx%d)" % (out, normalized.width, normalized.height))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
