"""Host-side checks for the K1 RX-only UI and reverse CTCSS path."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class ReceiveUiAndToneTests(unittest.TestCase):
    def test_help_is_clipped_cleared_and_time_sliced(self) -> None:
        menu = read("App/ui/menu.c")
        menu_text = read("App/ui/menu_text.h")
        app = read("App/app/app.c")
        self.assertIn("#define UI_MENU_HELP_WIDTH 15u", menu)
        self.assertIn("memset(gFrameBuffer[6] + 18, 0, LCD_WIDTH - 18)", menu)
        self.assertIn("UI_MENU_TimeSlice500ms();", app)
        self.assertIn('#define WRX_MENU_HELP_CHANNEL_LIST', menu_text)
        self.assertIn('#define WRX_MENU_HELP_CTCS', menu_text)

    def test_welcome_all_and_logo_followups_are_safe(self) -> None:
        welcome = read("App/ui/welcome.c")
        main = read("App/main.c")
        settings = read("App/settings.h")
        cmake = read("CMakePresets.json")
        font = read("App/japanese_font.c")
        self.assertIn("char WelcomeString0[17];", welcome)
        self.assertIn("UI_SanitizeWelcomeString", welcome)
        self.assertIn("POWER_ON_DISPLAY_MODE_MESSAGE", welcome)
        self.assertIn("POWER_ON_DISPLAY_MODE_ALL", welcome)
        self.assertIn("POWER_ON_DISPLAY_MODE_LOGO_MESSAGE", settings)
        self.assertIn("POWER_ON_DISPLAY_MODE_LOGO_ALL", settings)
        self.assertIn('"ENABLE_FEAT_F4HWN_LOGO": true', cmake)
        self.assertIn('UI_PrintString("JP RX-ONLY", 0, 127, 2, 10);', welcome)
        self.assertIn("UI_DisplayWelcomeRxOnlyMessage", welcome)
        self.assertIn("UI_DisplayWelcomeRxOnlyAll", welcome)
        self.assertIn("split_logo_followup", main)
        self.assertIn("boot_counter_10ms = 125", main)
        self.assertIn("UI_PrintStringJapaneseExtraLarge(WelcomeString0, 0, 127, 0, 11);", welcome)
        self.assertIn("[0x98 - 0x7F]", font)
        self.assertIn("[0x99 - 0x7F]", font)
        self.assertIn("0x08,0xf8,0x58,0xfc,0x58,0xf8,0x08", font)
        self.assertIn("0x00,0x10,0x10,0x10,0x10,0xF0,0x00", font)

    def test_reverse_ctcss_is_stored_displayed_and_inverted_at_runtime(self) -> None:
        dcs = read("App/dcs.h")
        radio = read("App/radio.c")
        menu = read("App/app/menu.c")
        ui = read("App/ui/menu.c")
        app = read("App/app/app.c")
        self.assertIn("CODE_TYPE_REVERSE_CONTINUOUS_TONE", dcs)
        self.assertIn("*pMax = ARRAY_SIZE(CTCSS_Options) * 2", menu)
        self.assertIn("pConfig->CodeType = CODE_TYPE_REVERSE_CONTINUOUS_TONE", menu)
        self.assertIn('sprintf(String, "R%u.%uHz"', ui)
        self.assertIn("static bool APP_CtcssMatch(void)", app)
        self.assertIn("CODE_TYPE_REVERSE_CONTINUOUS_TONE", radio)

    def test_txlock_menu_is_removed(self) -> None:
        header = read("App/ui/menu.h")
        menu = read("App/ui/menu.c")
        menu_text = read("App/ui/menu_text.h")
        self.assertNotIn("MENU_TX_LOCK", header)
        self.assertNotIn("TXLock", menu)

    def test_rejected_receive_actions_are_visible_and_audible(self) -> None:
        presets = read("App/app/rx_band_presets.c")
        radio = read("App/radio.c")
        helper = read("App/ui/helper.c")
        jp_text = read("App/ui/jp_text.h")
        self.assertIn("UI_DisplayUnavailable", presets)
        self.assertIn("return WRX_UI_TEXT_RX_EXT_OFF;", presets)
        self.assertIn("return WRX_UI_TEXT_SCAN_ACTIVE;", presets)
        self.assertIn('#define WRX_UI_TEXT_RX_EXT_OFF', jp_text)
        self.assertIn('#define WRX_UI_TEXT_SCAN_ACTIVE', jp_text)
        self.assertIn("UI_DisplayUnavailable", helper)
        self.assertIn("VFO_STATE_TX_DISABLE", radio)
        self.assertIn("AUDIO_PlayBeep(BEEP_500HZ_60MS_DOUBLE_BEEP_OPTIONAL);", radio)

    def test_large_font_uses_one_source_coordinate_system(self) -> None:
        header = read("App/font.h")
        helper = read("App/ui/helper.c")
        self.assertIn("#define FONT_BIG_PAGE_ROWS 8u", header)
        self.assertIn("UI_CenteredStart", helper)
        self.assertIn("UI_CopyLargeGlyph", helper)
        self.assertIn("UI_PrintStringBufferClipped", helper)
        self.assertIn("capacity - offset", helper)
        self.assertIn("glyph data itself decides which rows are lit", helper)
        self.assertNotIn("FONT_BIG_JAPANESE_RENDER_SHIFT", helper)

    def test_inverse_small_text_reuses_centering_and_clips_edges(self) -> None:
        helper = read("App/ui/helper.c")
        self.assertIn("const uint8_t x_start = UI_CenteredStart", helper)
        self.assertIn("if (length == 0u || Line == 0u || Line >= line_count || x_start >= LCD_WIDTH)", helper)
        self.assertIn("if (x_start > 0u)", helper)
        self.assertIn("if (x_end < LCD_WIDTH)", helper)

    def test_external_channel_names_cover_read_only_menu_and_center_by_pixels(self) -> None:
        helper = read("App/ui/helper.c")
        menu = read("App/ui/menu.c")
        self.assertIn("pixel_width > (uint16_t)(right + 1u - start)", helper)
        self.assertIn("center_full_width || end != 0u", helper)
        self.assertIn("UI_DrawExternalJapaneseCodepoints(codepoints, count", helper)
        self.assertIn("UI_DrawExternalJapaneseCodepoints(codepoints, codepoint_count", helper)
        self.assertGreaterEqual(menu.count("UI_PrintJapaneseChannelName"), 2)
        self.assertIn("if (edit_index < 0)", menu)

    def test_custom_menu_layout_uses_terminated_and_clipped_labels(self) -> None:
        header = read("App/ui/menu.h")
        menu = read("App/ui/menu.c")
        menu_text = read("App/ui/menu_text.h")
        jp_vocab = read("App/ui/jp_vocab.h")
        helper = read("App/ui/helper.c")
        self.assertIn("const char  name[7]", header)
        self.assertIn("WRX_MENU_LABEL_SCAN_REVERSE", menu)
        self.assertIn('"ScnRev"', menu_text)
        self.assertNotIn('"ScanRev"', menu_text)
        self.assertIn('#define WRX_JP_SCAN        "\\xBD\\xB7\\xAC\\xDD"', jp_vocab)
        self.assertIn('#define WRX_MENU_CATEGORY_SCAN         WRX_JP_SCAN', menu_text)
        self.assertIn('#define WRX_MENU_LABEL_SET_SCAN         WRX_JP_HIGH_SPEED', menu_text)
        self.assertIn("case 0xF0: return 0x9AD8; // 高", helper)
        self.assertIn("case 0xF1: return 0x901F; // 速", helper)
        self.assertNotIn("case 0xF0: return 0x8D70", helper)
        self.assertIn("UI_PrintStringSmallNormalClipped", helper)
        self.assertIn("UI_PrintStringClipped", helper)
        self.assertIn("UI_PrintStringSmallNormalClipped(MenuList[gMenuIndices[prev_index]].name, 0, 47, 1);", menu)
        self.assertIn("UI_PrintStringJapaneseExternal", menu)
        self.assertIn("UI_PrintStringClipped(", menu)


if __name__ == "__main__":
    unittest.main()
