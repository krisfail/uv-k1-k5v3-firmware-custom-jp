"""Tests for deterministic font-inventory quality checks."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load_quality_module():
    spec = importlib.util.spec_from_file_location("k1_font_quality", ROOT / "tools" / "font_quality.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load font_quality.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FontQualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.quality = load_quality_module()

    def test_generated_inventory_has_no_unexpected_breakage(self) -> None:
        inventory = json.loads((ROOT / "docs" / "assets" / "font-atlas" / "bitmap_atlas_inventory.json").read_text(encoding="utf-8"))
        manifest = json.loads((ROOT / "tools" / "font_inventory.json").read_text(encoding="utf-8"))
        findings = self.quality.analyze_inventory(inventory, manifest)
        self.assertFalse([finding for finding in findings if finding.severity == "error"], findings)
        self.assertTrue(any(finding.message == "意図した空きスロット" for finding in findings))

    def test_unlisted_blank_glyph_is_an_error(self) -> None:
        document = {
            "arrays": [{
                "name": "gFontExample",
                "size": 2,
                "element_width": 2,
                "bytes_hex": "00 00",
                "glyphs": [{"code": "0x80", "label": "受", "occupied": False, "bytes_hex": "00 00"}],
            }],
        }
        findings = self.quality.analyze_inventory(document)
        self.assertTrue(any(finding.severity == "error" and "字形が空です" in finding.message for finding in findings))

    def test_expected_empty_slot_is_reported_but_not_rejected(self) -> None:
        document = {
            "arrays": [{
                "name": "gFontExample",
                "size": 2,
                "element_width": 2,
                "bytes_hex": "00 00",
                "quality": {"expected_empty": ["0x80"]},
                "glyphs": [{"code": "0x80", "label": None, "occupied": False, "bytes_hex": "00 00"}],
            }],
        }
        findings = self.quality.analyze_inventory(document)
        self.assertFalse([finding for finding in findings if finding.severity == "error"], findings)
        self.assertEqual([finding.message for finding in findings], ["意図した空きスロット"])

    def test_stale_occupied_metadata_is_an_error(self) -> None:
        document = {
            "arrays": [{
                "name": "gFontExample",
                "size": 1,
                "element_width": 1,
                "bytes_hex": "01",
                "glyphs": [{"code": "0x80", "label": "受", "occupied": False, "bytes_hex": "01"}],
            }],
        }
        findings = self.quality.analyze_inventory(document)
        self.assertTrue(any("occupiedフラグ" in finding.message for finding in findings))

    def test_malformed_quality_metadata_is_an_error(self) -> None:
        document = {
            "arrays": [{
                "name": "gFontExample",
                "size": 1,
                "element_width": 1,
                "bytes_hex": "00",
                "quality": [],
                "glyphs": [{"code": "0x80", "label": "受", "occupied": False, "bytes_hex": "00"}],
            }],
        }
        findings = self.quality.analyze_inventory(document)
        self.assertTrue(any("quality must be an object" in finding.message for finding in findings))


if __name__ == "__main__":
    unittest.main()
