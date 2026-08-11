"""Static checks for the dependency-free interactive font editor."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class FontEditorTests(unittest.TestCase):
    def test_editor_contains_editing_and_export_controls(self) -> None:
        html = (ROOT / "tools" / "font_editor.html").read_text(encoding="utf-8")
        for marker in ("inventoryFile", "arraySelect", "glyphSelect", "grid", "copyC", "downloadPatch",
                       "layoutGuide", "visibleRowBounds", "guideTop",
                       "guideGlyph", "guideBottom", "通常大字形", "実データ上余白", "../assets/font-atlas",
                       "targetEntries", "editable_chunks", "target_kind", "Bitmap", "元データとの差分",
                       "diff-added", "diff-removed", "renderDiffSummary", "bitCount", "previewText",
                       "stringPreview", "renderStringPreview", "previewSample", "previewJapanese", "JIS_X0201_SAMPLE", "未登録", "annotationInput",
                       "pendingChanges", "stageCurrentTarget", "state.edits", "wrx-jp-font-patch-v1", "copyPatch", "patchFile", "loadPatch", "applyPatchData",
                       "LABEL_ALIASES", '"｡", "。"', '"｢", "「"', '"｣", "」"'):
            self.assertIn(marker, html)
        self.assertIn("bitmap_atlas_inventory.json", html)
        self.assertNotIn("C:" + "/Users", html)
        self.assertNotIn("C:" + "\\" + "Users", html)

    def test_pointer_drawing_is_delegated_and_transactional(self) -> None:
        html = (ROOT / "tools" / "font_editor.html").read_text(encoding="utf-8")
        for marker in (
            "touch-action: none",
            "toolMode",
            "activePointerId",
            "activeEditBefore",
            "handlePointerDown",
            "handlePointerMove",
            "getCoalescedEvents",
            "applyLine",
            "pointercancel",
            "lostpointercapture",
            "contextmenu",
            "event.detail !== 0",
            '$("grid").setPointerCapture',
        ):
            self.assertIn(marker, html)
        self.assertNotIn('cell.addEventListener("pointerenter"', html)
        self.assertNotIn('cell.addEventListener("pointerdown"', html)
        self.assertNotIn("state.drawing", html)

    def test_editor_accepts_bitmap_arrays_without_glyph_metadata(self) -> None:
        html = (ROOT / "tools" / "font_editor.html").read_text(encoding="utf-8")
        self.assertIn('typeof array.bytes_hex === "string"', html)
        self.assertIn('target_kind: "bitmap"', html)
        self.assertNotIn('Array.isArray(array.glyphs) && array.glyph_width && array.glyph_pages', html)

    def test_string_preview_marks_missing_and_uses_live_glyph(self) -> None:
        html = (ROOT / "tools" / "font_editor.html").read_text(encoding="utf-8")
        self.assertIn('workingBytes(target)', html)
        self.assertIn('context.strokeRect(originX + 1', html)
        self.assertIn('context.fillText(character', html)
        self.assertIn('未登録:', html)
        self.assertIn('canonicalizeLabel(glyph.label', html)
        self.assertIn('JIS_X0201_SAMPLE', html)
        self.assertIn('JAPANESE_ARRAY_NAMES', html)
        self.assertIn('EDITABLE_CONTROL_IDS', html)
        self.assertIn('function setPreviewText', html)
        self.assertIn('const lineGap = 8', html)
        self.assertIn('const columns = Math.max(1', html)
        self.assertIn('originY + y * scale', html)
        self.assertNotIn('max-width: 100%', html)

    def test_big_font_guide_uses_actual_vertical_bounds(self) -> None:
        html = (ROOT / "tools" / "font_editor.html").read_text(encoding="utf-8")
        self.assertIn('const bounds = visibleRowBounds()', html)
        self.assertIn('固定の上下余白なし', html)
        self.assertNotIn('表示行2–11: 参考字形領域', html)

    def test_batch_edits_keep_annotation_and_emit_one_patch(self) -> None:
        html = (ROOT / "tools" / "font_editor.html").read_text(encoding="utf-8")
        for marker in (
            "function targetKey",
            "function workingLabel",
            "function handleAnnotationInput",
            'label: state.currentLabel || null',
            'changes,',
            'anchor.download = "wrx-jp-font-patch.json"',
            '全変更のJSONパッチをクリップボードへコピーしました．',
        ):
            self.assertIn(marker, html)


if __name__ == "__main__":
    unittest.main()
