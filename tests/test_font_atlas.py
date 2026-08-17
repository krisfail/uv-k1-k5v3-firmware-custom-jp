"""Host-side checks for the K1/K5v3 font atlas parser and inventory."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]


def load_atlas_module():
    spec = importlib.util.spec_from_file_location("k1_render_bitmap_atlas", ROOT / "tools" / "render_bitmap_atlas.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load render_bitmap_atlas.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FontAtlasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.atlas = load_atlas_module()

    def parse_arrays(self):
        occurrences = {}
        arrays = []
        for source in (ROOT / "App" / "font.c", ROOT / "App" / "japanese_font.c", ROOT / "App" / "bitmaps.c"):
            arrays.extend(self.atlas.parse_source(source, occurrences))
        return arrays

    def parse_array(self, name: str):
        return next(array for array in self.parse_arrays() if array.name == name)

    def test_extended_fonts_keep_sparse_slots_and_long_vowel(self) -> None:
        big = self.parse_array("gFontBigJapanese")
        small = self.parse_array("gFontSmallJapanese")
        for array, width in ((big, 14), (small, 6)):
            self.assertIsNotNone(array.glyphs)
            glyphs = array.glyphs
            assert glyphs is not None
            self.assertEqual([glyph["code"] for glyph in glyphs], list(range(0x80, 0x100)))
            self.assertEqual(len(glyphs), len(array.values) // width)
            self.assertFalse(glyphs[0x9A - 0x80]["occupied"])
            self.assertEqual(glyphs[0xE0 - 0x80]["label"], "ー")

    def test_duplicate_designated_glyph_is_rejected(self) -> None:
        row = ",".join(["0"] * 14)
        initializer = f"[0x80 - 0x7F] = {{{row}}}, [0x80 - 0x7F] = {{{row}}}"
        with self.assertRaises(ValueError):
            self.atlas.parse_glyph_annotations("gFontBigJapanese", initializer, 14)

    def test_open_font_derived_large_glyphs_have_stable_readable_bitmaps(self) -> None:
        array = self.parse_array("gFontBigJapanese")
        glyphs = array.glyphs
        assert glyphs is not None
        expected = {
            0x98: bytes.fromhex("08 f8 58 fc 58 f8 08 04 05 05 0d 15 1d 04"),
            0x99: bytes.fromhex("00 fc 24 fc 24 24 fc 1e 01 01 07 01 11 1f"),
            0xBA: bytes.fromhex("00 10 10 10 10 f0 00 00 10 10 10 10 3f 00"),
            0xC6: bytes.fromhex("00 10 10 10 10 10 00 08 08 08 08 08 08 08"),
        }
        for code, bitmap in expected.items():
            glyph = glyphs[code - 0x80]
            self.assertEqual(bytes(glyph["bytes"]), bitmap)
            self.assertTrue(glyph["occupied"])
        self.assertEqual(array.source, "japanese_font.c")

    def test_extra_large_japanese_table_is_compact_and_editable(self) -> None:
        array = self.parse_array("gFontJapaneseExtraLarge")
        self.assertEqual(array.glyph_layout, (10, 2))
        self.assertEqual([glyph["code"] for glyph in array.glyphs or []], [0x80, 0x81, 0x98, 0x99])
        self.assertTrue(all(glyph["occupied"] for glyph in array.glyphs or []))
    def test_large_long_vowel_uses_the_ascii_hyphen_rows(self) -> None:
        ascii_font = self.parse_array("gFontBig")
        japanese_font = self.parse_array("gFontBigJapanese")
        ascii_glyph = next(g for g in ascii_font.glyphs or [] if g["code"] == 0x2D)
        japanese_glyph = next(g for g in japanese_font.glyphs or [] if g["code"] == 0xE0)
        self.assertEqual(bytes(ascii_glyph["bytes"]), bytes(japanese_glyph["bytes"]))

    def test_markdown_inventory_is_human_readable(self) -> None:
        report = self.atlas.make_markdown_inventory(self.parse_arrays())
        self.assertIn("# フォント一覧", report)
        self.assertIn("| `gFontBigJapanese` | font |", report)
        self.assertIn("| `0xE0` | ー | 使用中 |", report)

    def test_manifest_provides_canonical_codepoint_labels(self) -> None:
        manifest = self.atlas.load_font_manifest(ROOT / "tools" / "font_inventory.json", ROOT)
        arrays = self.atlas.apply_font_manifest(self.parse_arrays(), manifest)
        japanese = next(array for array in arrays if array.name == "gFontBigJapanese")
        glyphs = japanese.glyphs
        assert glyphs is not None
        self.assertEqual(glyphs[0xA1 - 0x80]["label"], "｡")
        self.assertEqual(glyphs[0xDF - 0x80]["label"], "ﾟ")
        self.assertEqual(glyphs[0xE0 - 0x80]["label"], "ー")

    def test_generated_inventory_exposes_bitmap_edit_chunks(self) -> None:
        inventory = json.loads(
            (ROOT / "docs" / "assets" / "font-atlas" / "bitmap_atlas_inventory.json").read_text(encoding="utf-8")
        )
        bitmap = next(array for array in inventory["arrays"] if array["name"] == "BITMAP_BatteryLevel")
        self.assertEqual(bitmap["category"], "bitmap")
        self.assertEqual(bitmap["editable_chunks"], [{"index": 0, "offset": 0, "length": 2, "label": "element 0"}])
        codes = next(array for array in inventory["arrays"] if array["name"] == "gFontJapaneseExtraLargeCodes")
        self.assertEqual(codes["element_width"], 1)
        self.assertEqual([chunk["length"] for chunk in codes["editable_chunks"]], [1, 1, 1, 1])
        small_bold = next(array for array in inventory["arrays"] if array["name"] == "gFontSmallBold")
        self.assertEqual(small_bold["element_count"], 94)
        self.assertEqual(small_bold["editable_chunks"][0]["label"], "0x21 !")
        self.assertEqual(small_bold["editable_chunks"][-1]["label"], "0x7E ~")

    def test_small_bold_font_is_rendered_element_by_element(self) -> None:
        svg = self.atlas.make_svg([self.parse_array("gFontSmallBold")], scale=2, wrap=64)
        self.assertIn("0x21 !", svg)
        self.assertIn("0x7E ~", svg)
        self.assertEqual(svg.count('fill="url(#cell-grid-2)"'), 94)

    def test_svg_escapes_ascii_glyph_labels(self) -> None:
        arrays = [self.parse_array("gFontBig"), self.parse_array("gFontBigJapanese")]
        svg = self.atlas.make_svg(arrays, scale=2, wrap=64)
        ET.fromstring(svg)
        self.assertIn("0x26 &amp;", svg)
        self.assertIn("0x3C &lt;", svg)
        self.assertIn("0x98 専", svg)
        self.assertIn("<pattern id=\"cell-grid-2\"", svg)
        self.assertIn("<path d=\"", svg)
        self.assertLess(svg.count("<rect "), 300)
        self.assertNotIn("project-authored", svg)
        self.assertNotIn("C:" + "/Users", svg)
        self.assertNotIn("C:" + "\\", svg)


if __name__ == "__main__":
    unittest.main()
