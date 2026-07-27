import unittest

from PIL import Image, ImageDraw

from scripts.normalize_glyph_sheet import normalize_sheet


class NormalizeGlyphSheetTests(unittest.TestCase):
    def test_recenters_variable_pitch_glyphs_and_aligns_row_baselines(self):
        source = Image.new("L", (180, 80), 255)
        draw = ImageDraw.Draw(source)

        # Two deliberately uneven rows. Their glyphs have different horizontal
        # spacing and their source baselines sit at y=30 and y=70.
        for box in ((5, 10, 14, 29), (45, 10, 59, 29), (120, 10, 134, 29)):
            draw.rectangle(box, fill=0)
        for box in ((15, 50, 24, 69), (80, 50, 89, 69), (140, 50, 154, 69)):
            draw.rectangle(box, fill=0)

        normalized = normalize_sheet(
            source,
            chars="ABCDEF",
            cols=3,
            cell_size=100,
            baseline_frac=0.8,
            ink_threshold=128,
            glyph_scale=1.0,
        )

        self.assertEqual((300, 200), normalized.size)
        for index in range(6):
            row, col = divmod(index, 3)
            cell = normalized.crop(
                (col * 100, row * 100, (col + 1) * 100, (row + 1) * 100)
            )
            bbox = cell.point(lambda value: 255 if value < 128 else 0).getbbox()
            self.assertIsNotNone(bbox)
            self.assertEqual(80, bbox[3])
            self.assertLessEqual(abs(((bbox[0] + bbox[2]) / 2) - 50), 1)

    def test_merges_nearby_disconnected_parts_into_one_expected_glyph(self):
        source = Image.new("L", (120, 50), 255)
        draw = ImageDraw.Draw(source)
        draw.rectangle((10, 10, 14, 29), fill=0)
        draw.rectangle((18, 10, 22, 29), fill=0)
        draw.rectangle((80, 10, 94, 29), fill=0)

        normalized = normalize_sheet(
            source,
            chars='"A',
            cols=2,
            cell_size=100,
            baseline_frac=0.8,
            ink_threshold=128,
            glyph_scale=1.0,
        )

        first = normalized.crop((0, 0, 100, 100))
        projection = [
            any(first.getpixel((x, y)) < 128 for y in range(first.height))
            for x in range(first.width)
        ]
        runs = 0
        inside = False
        for occupied in projection:
            if occupied and not inside:
                runs += 1
                inside = True
            elif not occupied:
                inside = False
        self.assertEqual(2, runs)

    def test_preserves_a_descender_without_copying_it_into_the_next_row(self):
        source = Image.new("L", (120, 80), 255)
        draw = ImageDraw.Draw(source)

        # The first glyph is connected across the nominal y=40 row boundary.
        # The next row begins later, leaving a short piece of that descender in
        # its fixed row slice.
        draw.rectangle((10, 10, 19, 46), fill=0)
        draw.rectangle((75, 10, 84, 29), fill=0)
        draw.rectangle((10, 60, 19, 74), fill=0)
        draw.rectangle((75, 60, 84, 74), fill=0)

        normalized = normalize_sheet(
            source,
            chars="pABC",
            cols=2,
            cell_size=100,
            baseline_frac=0.8,
            ink_threshold=128,
            glyph_scale=0.5,
        )

        descender = normalized.crop((0, 0, 100, 100))
        descender_bbox = descender.point(
            lambda value: 255 if value < 128 else 0
        ).getbbox()
        self.assertEqual(99, descender_bbox[3])

        next_row = normalized.crop((0, 100, 100, 200))
        next_bbox = next_row.point(lambda value: 255 if value < 128 else 0).getbbox()
        self.assertGreaterEqual(next_bbox[1], 60)


if __name__ == "__main__":
    unittest.main()
