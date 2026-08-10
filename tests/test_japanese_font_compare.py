"""Tests for the source-level Japanese glyph comparison tool."""

import importlib.util
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load_module():
    path = ROOT / "tools" / "compare_japanese_font.py"
    spec = importlib.util.spec_from_file_location("compare_japanese_font_k1", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load compare_japanese_font.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class JapaneseFontCompareTests(unittest.TestCase):
    def test_parser_accepts_comments_and_skips_non_large_glyphs(self) -> None:
        module = load_module()
        source = """
        {0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, //0x80 //受
        [0x81 - 0x7F] = {0x02,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00}, // 信
        [0x82 - 0x7F] = {0x01,0x02,0x03,0x04,0x05,0x06}, // 小字形
        """
        with TemporaryDirectory() as directory:
            path = Path(directory) / "font.c"
            path.write_text(source, encoding="utf-8")
            entries = module.parse_source(path, 0x80, 0x81)
        self.assertEqual(set(entries), {0x80, 0x81})
        self.assertEqual(entries[0x80].label, "受")
        self.assertEqual(entries[0x81].label, "信")

    def test_compare_reports_directional_bit_changes(self) -> None:
        module = load_module()
        reference = {0x80: module.FontEntry(0x80, (0x01, 0x00), "受", "ref.c", 1)}
        current = {0x80: module.FontEntry(0x80, (0x03, 0x00), "受", "cur.c", 1)}
        result = module.compare(reference, current)
        self.assertEqual(result["summary"]["different"], 1)
        self.assertEqual(result["summary"]["reference_only_bits"], 0)
        self.assertEqual(result["summary"]["current_only_bits"], 1)
        self.assertEqual(result["rows"][0]["label"], "受")
        self.assertEqual(result["rows"][0]["changed_bytes"], [0])


if __name__ == "__main__":
    unittest.main()
