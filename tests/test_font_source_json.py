"""Safety tests for the C-font/JSON round-trip tool."""

from __future__ import annotations

import copy
import importlib.util
import tempfile
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load_module():
    spec = importlib.util.spec_from_file_location("k1_font_source_json", ROOT / "tools" / "font_source_json.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load font_source_json.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FontSourceJsonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tool = load_module()
        cls.source = ROOT / "App" / "japanese_font.c"

    def test_extract_is_complete_and_anchored(self) -> None:
        document = self.tool.extract_document(self.source, "gFontBigJapanese", 1)
        self.assertEqual(document["format"], "wrx-jp-font-source-v1")
        self.assertEqual(document["element_width"], 14)
        codes = [item["code"] for item in document["elements"]]
        self.assertIn("0x80", codes)
        self.assertIn("0x98", codes)
        self.assertIn("0xDF", codes)
        self.assertIn("0xFF", codes)

    def test_unannotated_contiguous_font_can_be_explicitly_anchored(self) -> None:
        document = self.tool.extract_document(ROOT / "App" / "font.c", "gFontSmall", 1, 0x21)
        self.assertEqual(len(document["elements"]), 0x7E - 0x21 + 1)
        self.assertEqual(document["elements"][0]["code"], "0x21")
        self.assertEqual(document["index_base"], "0x21")

    def test_noop_round_trip_is_byte_identical(self) -> None:
        document = self.tool.extract_document(self.source, "gFontBigJapanese", 1)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "japanese_font.c"
            self.tool.apply_document(self.source, document, output)
            self.assertEqual(output.read_bytes(), self.source.read_bytes())

    def test_only_edited_codepoint_is_spliced(self) -> None:
        document = self.tool.extract_document(self.source, "gFontBigJapanese", 1)
        edited = copy.deepcopy(document)
        target = next(item for item in edited["elements"] if item["code"] == "0xA1")
        values = target["bytes_hex"].split()
        values[0] = "01" if values[0] != "01" else "00"
        target["bytes_hex"] = " ".join(values)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "japanese_font.c"
            self.assertEqual(self.tool.apply_document(self.source, edited, output), 1)
            old_array = self.tool.parse_array(self.source.read_text(encoding="utf-8"), "gFontBigJapanese")
            new_array = self.tool.parse_array(output.read_text(encoding="utf-8"), "gFontBigJapanese")
            old = {entry.code: entry.values for entry in old_array.entries}
            new = {entry.code: entry.values for entry in new_array.entries}
            self.assertNotEqual(old[0xA1], new[0xA1])
            self.assertEqual(old[0x98], new[0x98])
            self.assertEqual(old[0xBA], new[0xBA])
            self.assertEqual(old[0xC6], new[0xC6])
            for code in old:
                if code != 0xA1:
                    self.assertEqual(old[code], new[code], f"unexpected change at 0x{code:02X}")

    def test_stale_base_bytes_are_rejected(self) -> None:
        document = self.tool.extract_document(self.source, "gFontBigJapanese", 1)
        target = next(item for item in document["elements"] if item["code"] == "0xA1")
        target["base_bytes_hex"] = "00 " * 13 + "00"
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                self.tool.apply_document(self.source, document, Path(directory) / "japanese_font.c")


if __name__ == "__main__":
    unittest.main()
