"""LCDエミュレータの描画契約を検査する。実機やGUIは使用しない。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import lcd_emulator  # noqa: E402


class LcdEmulatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fonts = lcd_emulator.load_font_tables(ROOT)

    def test_pixel_uses_st7565_page_and_bit_order(self):
        frame = lcd_emulator.LcdFrame()
        frame.pixel(7, 9)
        self.assertEqual(frame.data[lcd_emulator.LCD_WIDTH + 7], 0x02)
        self.assertEqual(frame.image(2).size, (256, 128))

    def test_all_category_previews_fit_the_lcd(self):
        for index in range(len(lcd_emulator.CATEGORY_NAMES)):
            frame = lcd_emulator.render_category(index, self.fonts)
            self.assertEqual(len(frame.data), lcd_emulator.LCD_BYTES)
            self.assertTrue(any(frame.data[6 * lcd_emulator.LCD_WIDTH : 7 * lcd_emulator.LCD_WIDTH]))
            self.assertTrue(any(frame.data[7 * lcd_emulator.LCD_WIDTH :]))

    def test_menu_preview_can_use_the_external_font(self):
        external = lcd_emulator.ExternalFont(ROOT / "docs" / "fonts" / "japanese_font.bin")
        internal_codepoints = lcd_emulator.load_internal_codepoints(ROOT)
        frame = lcd_emulator.LcdFrame()
        drawn = lcd_emulator.draw_external_internal(
            frame, b"\x80\x81DCS", self.fonts, external, internal_codepoints,
            50, 127, 0)
        self.assertTrue(drawn)
        self.assertTrue(any(frame.data))

    def test_receive_preview_covers_external_name_ascii_fallback_and_dual_vfo(self):
        external = lcd_emulator.ExternalFont(ROOT / "docs" / "fonts" / "japanese_font.bin")
        main = lcd_emulator.render_receive(self.fonts, external, dual=False, external_name=True)
        fallback = lcd_emulator.render_receive(self.fonts, external, dual=False, external_name=False)
        ascii_mode = lcd_emulator.render_receive(
            self.fonts, external, dual=False, external_name=True, ascii_name=True
        )
        dual = lcd_emulator.render_receive(self.fonts, external, dual=True, external_name=True)
        compact = lcd_emulator.render_receive(
            self.fonts, external, dual=False, external_name=True, compact_name=True
        )
        dual_compact = lcd_emulator.render_receive(
            self.fonts, external, dual=True, external_name=True, compact_name=True
        )

        self.assertEqual(len(main.data), lcd_emulator.LCD_BYTES)
        self.assertNotEqual(main.data, fallback.data)
        self.assertEqual(ascii_mode.data, fallback.data)
        self.assertNotEqual(main.data, compact.data)
        self.assertTrue(any(dual_compact.data[lcd_emulator.LCD_WIDTH + 36 :
                                             2 * lcd_emulator.LCD_WIDTH]))
        self.assertTrue(any(main.data[2 * lcd_emulator.LCD_WIDTH : 4 * lcd_emulator.LCD_WIDTH]))
        self.assertTrue(any(dual.data[6 * lcd_emulator.LCD_WIDTH :]))
        self.assertTrue(any(dual.data[3 * lcd_emulator.LCD_WIDTH : 4 * lcd_emulator.LCD_WIDTH]))

    def test_receive_header_keeps_tiny_status_above_channel_number(self):
        external = lcd_emulator.ExternalFont(ROOT / "docs" / "fonts" / "japanese_font.bin")
        frame = lcd_emulator.render_receive(self.fonts, external, dual=False)

        tiny_row = frame.data[0 : lcd_emulator.LCD_WIDTH]
        channel_row = frame.data[lcd_emulator.LCD_WIDTH : 2 * lcd_emulator.LCD_WIDTH]
        self.assertTrue(any(tiny_row[10:26]))
        self.assertTrue(any(channel_row[1:30]))

    def test_receive_preview_uses_neutral_channel_name_samples(self):
        source = (ROOT / "tools" / "lcd_emulator.py").read_text(encoding="utf-8")
        self.assertNotIn("受信DCS", source)
        self.assertIn('frame, "東京"', source)
        self.assertIn('draw_external_text(frame, "TOKYO"', source)

    def test_receive_preview_models_the_current_metadata_and_rssi_pages(self):
        external = lcd_emulator.ExternalFont(ROOT / "docs" / "fonts" / "japanese_font.bin")
        frame = lcd_emulator.render_receive(self.fonts, external, dual=True)

        # The compact dual-VFO layout keeps metadata on its own page;
        # dual-VFO RSSI owns page 3.
        first_metadata_page = frame.data[2 * lcd_emulator.LCD_WIDTH :
                                         3 * lcd_emulator.LCD_WIDTH]
        self.assertTrue(any(first_metadata_page[58:100]))

        # RSSI clears its dedicated page before drawing the 6×8 label and meter.
        rssi_page = frame.data[3 * lcd_emulator.LCD_WIDTH :
                               4 * lcd_emulator.LCD_WIDTH]
        self.assertTrue(any(rssi_page[2:34]))
        self.assertFalse(any(rssi_page[58:62]))

    def test_receive_preview_uses_separate_status_pages_after_layout_fix(self):
        external = lcd_emulator.ExternalFont(ROOT / "docs" / "fonts" / "japanese_font.bin")
        single = lcd_emulator.render_receive(self.fonts, external, dual=False)
        dual = lcd_emulator.render_receive(self.fonts, external, dual=True)

        single_frequency_page = single.data[2 * lcd_emulator.LCD_WIDTH :
                                            3 * lcd_emulator.LCD_WIDTH]
        single_status_page = single.data[4 * lcd_emulator.LCD_WIDTH :
                                          5 * lcd_emulator.LCD_WIDTH]
        self.assertTrue(any(single_frequency_page[34:112]))
        self.assertTrue(any(single_status_page[2:121]))
        single_footer_page = single.data[6 * lcd_emulator.LCD_WIDTH :
                                        7 * lcd_emulator.LCD_WIDTH]
        self.assertTrue(any(single_footer_page[105:128]))

        dual_frequency_page = dual.data[lcd_emulator.LCD_WIDTH :
                                        2 * lcd_emulator.LCD_WIDTH]
        dual_status_page = dual.data[2 * lcd_emulator.LCD_WIDTH :
                                     3 * lcd_emulator.LCD_WIDTH]
        self.assertTrue(any(dual_frequency_page[36:100]))
        self.assertTrue(any(dual_status_page[2:100]))


if __name__ == "__main__":
    unittest.main()
