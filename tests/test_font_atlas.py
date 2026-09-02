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
    spec = importlib.util.spec_from_file_location(
        "k1_render_bitmap_atlas", ROOT / "tools" / "render_bitmap_atlas.py"
    )
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
        for source in (ROOT / "App" / "font.c", ROOT / "App" / "bitmaps.c"):
            arrays.extend(self.atlas.parse_source(source, occurrences))
        return arrays

    def parse_array(self, name: str):
        return next(array for array in self.parse_arrays() if array.name == name)

    def test_ascii_fonts_are_present_and_legacy_japanese_source_is_removed(self) -> None:
        self.assertTrue((ROOT / "App" / "font.c").exists())
        self.assertFalse((ROOT / "App" / "japanese_font.c").exists())
        self.assertIsNotNone(self.parse_array("gFontBig").glyphs)
        self.assertEqual(self.parse_array("gFontSmall").element_width, 6)

    def test_large_ascii_glyphs_have_stable_codepoints(self) -> None:
        glyphs = self.parse_array("gFontBig").glyphs
        assert glyphs is not None
        self.assertEqual(glyphs[0]["code"], 0x21)
        self.assertEqual(glyphs[-1]["code"], 0x7E)
        self.assertEqual(glyphs[0]["label"], "!")

    def test_manifest_selects_only_current_sources(self) -> None:
        manifest = self.atlas.load_font_manifest(ROOT / "tools" / "font_inventory.json", ROOT)
        paths = [source["path"] for source in manifest["sources"]]
        self.assertEqual(paths, ["App/font.c", "App/bitmaps.c"])
        self.assertNotIn("App/japanese_font.c", paths)
        arrays = self.atlas.apply_font_manifest(self.parse_arrays(), manifest)
        self.assertTrue(any(array.name == "gFontBig" for array in arrays))

    def test_generated_inventory_contains_no_removed_arrays(self) -> None:
        inventory = json.loads(
            (ROOT / "docs" / "assets" / "font-atlas" / "bitmap_atlas_inventory.json")
            .read_text(encoding="utf-8")
        )
        names = {array["name"] for array in inventory["arrays"]}
        self.assertNotIn("gFontBigJapanese", names)
        self.assertNotIn("gFontSmallJapanese", names)
        self.assertNotIn("gFontJapaneseExtraLarge", names)
        self.assertNotIn("App/japanese_font.c", inventory["sources"])

    def test_small_bold_font_is_rendered_element_by_element(self) -> None:
        svg = self.atlas.make_svg([self.parse_array("gFontSmallBold")], scale=2, wrap=64)
        self.assertIn("0x21 !", svg)
        self.assertIn("0x7E ~", svg)
        self.assertEqual(svg.count('fill="url(#cell-grid-2)"'), 94)

    def test_svg_escapes_ascii_glyph_labels(self) -> None:
        svg = self.atlas.make_svg([self.parse_array("gFontBig")], scale=2, wrap=64)
        ET.fromstring(svg)
        self.assertIn("0x26 &amp;", svg)
        self.assertIn("0x3C &lt;", svg)
        self.assertIn('<pattern id="cell-grid-2"', svg)
        self.assertIn("<path d=", svg)
        self.assertNotIn("project-authored", svg)
        self.assertNotIn("C:" + "/Users", svg)
        self.assertNotIn("C:" + "\\", svg)


if __name__ == "__main__":
    unittest.main()
