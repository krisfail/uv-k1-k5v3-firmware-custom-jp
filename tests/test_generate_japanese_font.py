import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load_generator():
    path = ROOT / "tools" / "generate_japanese_font.py"
    spec = importlib.util.spec_from_file_location("generate_japanese_font_test", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load generate_japanese_font.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def minimal_bdf(bounding_box="16 16 0 -2", glyph_bbx="16 16 0 -2"):
    rows = "\n".join(["0000"] * 16)
    return "\n".join((
        "STARTFONT 2.1",
        "FONTBOUNDINGBOX " + bounding_box,
        "STARTCHAR test",
        "ENCODING 9250",
        "BBX " + glyph_bbx,
        "BITMAP",
        rows,
        "ENDCHAR",
        "ENDFONT",
        ""))


class JapaneseFontGeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.generator = load_generator()

    def parse(self, text):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "font.bdf"
            path.write_text(text, encoding="ascii")
            return self.generator.parse_bdf(path, {9250})

    def test_accepts_expected_geometry_and_baseline(self):
        glyphs = self.parse(minimal_bdf())
        self.assertEqual(glyphs[9250], [0] * 16)

    def test_source_hash_contract_is_a_full_sha256(self):
        self.assertEqual(len(self.generator.SOURCE_SHA256), 64)
        with TemporaryDirectory() as directory:
            path = Path(directory) / "not-the-canonical-source.bdf.gz"
            path.write_bytes(b"not the canonical source")
            with self.assertRaises(ValueError):
                self.generator.verify_source(path)

    def test_rejects_font_baseline_change(self):
        with self.assertRaises(ValueError):
            self.parse(minimal_bdf(bounding_box="16 16 0 -1"))

    def test_rejects_glyph_offset_change(self):
        with self.assertRaises(ValueError):
            self.parse(minimal_bdf(glyph_bbx="16 16 1 -2"))


if __name__ == "__main__":
    unittest.main()
