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


def minimal_bdf14(bounding_box="14 15 0 -3", glyph_bbx="13 13 0 -1"):
    rows = "\n".join(["8000"] + ["0000"] * 12)
    return "\n".join((
        "STARTFONT 2.1",
        "FONTBOUNDINGBOX " + bounding_box,
        "STARTCHAR test",
        "ENCODING 26481",
        "DWIDTH 14 0",
        "BBX " + glyph_bbx,
        "BITMAP",
        rows,
        "ENDCHAR",
        "ENDFONT",
        ""))


def minimal_bdf8(bounding_box="8 8 0 -2", glyph_bbx="7 7 0 -1",
                 dwidth=8, encoding=26481, first_row="80"):
    rows = "\n".join([first_row] + ["00"] * 6)
    return "\n".join((
        "STARTFONT 2.1",
        "FONTBOUNDINGBOX " + bounding_box,
        "FONT_ASCENT 6",
        "STARTCHAR test",
        "ENCODING " + str(encoding),
        "DWIDTH " + str(dwidth) + " 0",
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

    def test_reads_native_14px_cell_and_preserves_baseline(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "font14.bdf"
            path.write_text(minimal_bdf14(), encoding="ascii")
            glyphs = self.generator.parse_bdf14(path, {26481})
        self.assertEqual(len(glyphs[26481]), 14)
        self.assertEqual(glyphs[26481][0], 0x8000)
        self.assertEqual(glyphs[26481][13], 0)

    def test_rejects_native_14px_geometry_change(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "font14.bdf"
            path.write_text(
                minimal_bdf14(bounding_box="16 16 0 -2"), encoding="ascii")
            with self.assertRaises(ValueError):
                self.generator.parse_bdf14(path, {26481})

    def test_reads_native_8px_cell_and_preserves_baseline(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "font8.bdf"
            path.write_text(minimal_bdf8(), encoding="ascii")
            glyphs = self.generator.parse_bdf8(path, {26481})
        self.assertEqual(glyphs[26481], [0x80] + [0] * 7)

    def test_centers_narrow_native_8px_symbol_in_its_cell(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "font8.bdf"
            path.write_text(
                minimal_bdf8(glyph_bbx="3 1 0 2", dwidth=4,
                             encoding=0x2212, first_row="E0"), encoding="ascii")
            glyphs = self.generator.parse_bdf8(path, {0x2212})
        self.assertEqual(glyphs[0x2212][3], 0x38)

    def test_rejects_native_8px_geometry_change(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "font8.bdf"
            path.write_text(
                minimal_bdf8(bounding_box="16 16 0 -2"), encoding="ascii")
            with self.assertRaises(ValueError):
                self.generator.parse_bdf8(path, {26481})


if __name__ == "__main__":
    unittest.main()
