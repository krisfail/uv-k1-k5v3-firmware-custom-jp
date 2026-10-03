"""Static and contract checks for the dependency-free WebSerial host tool."""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
WEBUI = ROOT / "tools" / "webui"
SPEC = spec_from_file_location("prepare_github_pages", ROOT / "tools" / "prepare_github_pages.py")
MODULE = module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class WebUiTests(unittest.TestCase):
    def test_webui_is_static_and_separate_from_python_host(self) -> None:
        index = (WEBUI / "index.html").read_text(encoding="utf-8")
        protocol = (WEBUI / "protocol.mjs").read_text(encoding="utf-8")
        app = (WEBUI / "app.mjs").read_text(encoding="utf-8")
        self.assertIn('<script type="module" src="./app.mjs"></script>', index)
        self.assertIn("navigator.serial", app)
        self.assertIn("WebSerialTransport", app)
        self.assertIn("validateLogicalWrite", protocol)
        self.assertIn("CALIBRATION_LOGICAL_BASE", protocol)
        self.assertNotIn("pyserial", index + app)

    def test_memory_editor_exposes_safe_read_write_and_diff_flow(self) -> None:
        index = (WEBUI / "index.html").read_text(encoding="utf-8")
        memory = (WEBUI / "memory.mjs").read_text(encoding="utf-8")
        app = (WEBUI / "app.mjs").read_text(encoding="utf-8")
        for marker in (
            "memory-offset", "memory-length", "memory-read", "memory-write",
            "memory-import", "memory-export", "memory-diff-bytes", "memory-diff-blocks",
        ):
            self.assertIn(marker, index)
        self.assertIn("changedBlocks", memory)
        self.assertIn("writeMemoryChanged", app)
        self.assertIn("validateLogicalWrite(offset, after.length)", app)

    def test_pages_builder_copies_webui_and_manifest(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "docs"
            source.mkdir()
            (source / "index.md").write_text("# Index\n", encoding="utf-8")
            webui = root / "tools" / "webui"
            webui.mkdir(parents=True)
            (webui / "index.html").write_text("<!doctype html>", encoding="utf-8")
            manifest = root / "tools" / "japanese_font_manifest.json"
            manifest.write_text("{}", encoding="utf-8")
            (root / "README.ja.md").write_text(
                "# README\n\n[WebUI](tools/webui/index.html)\n",
                encoding="utf-8",
            )
            destination = root / ".pages-source"
            MODULE.prepare_pages_source(root, source, destination)
            self.assertTrue((destination / "host" / "index.html").exists())
            self.assertTrue((destination / "host" / "japanese_font_manifest.json").exists())
            self.assertIn("host/index.html", (destination / "README.ja.md").read_text(encoding="utf-8"))

    def test_ui_documents_the_real_browser_constraints(self) -> None:
        development = (ROOT / "DEVELOPMENT.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.ja.md").read_text(encoding="utf-8")
        webserial_doc = (ROOT / "docs/WEB_SERIAL_HOST.ja.md").read_text(encoding="utf-8")
        self.assertIn("WebSerial", development)
        self.assertIn("tools/webui/", development)
        self.assertIn("WebSerial host tool", readme)
        self.assertIn("校正", webserial_doc)
        self.assertIn("GitHub Pages", webserial_doc)


if __name__ == "__main__":
    unittest.main()
