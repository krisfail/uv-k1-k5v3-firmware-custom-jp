"""Host-side checks for the K1 RX-only UI and reverse CTCSS path."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class ReceiveUiAndToneTests(unittest.TestCase):
    def test_help_is_clipped_cleared_and_time_sliced(self) -> None:
        menu = read("App/ui/menu.c")
        app = read("App/app/app.c")
        self.assertIn("#define UI_MENU_HELP_WIDTH 15u", menu)
        self.assertIn("memset(gFrameBuffer[6] + 18, 0, LCD_WIDTH - 18)", menu)
        self.assertIn("UI_MENU_TimeSlice500ms();", app)
        self.assertIn('return "scan list membership";', menu)
        self.assertIn('return "normal/reverse tone";', menu)

    def test_welcome_all_and_logo_message_are_safe(self) -> None:
        welcome = read("App/ui/welcome.c")
        settings = read("App/settings.h")
        cmake = read("CMakePresets.json")
        font = read("App/japanese_font.c")
        self.assertIn("char WelcomeString0[17];", welcome)
        self.assertIn("UI_SanitizeWelcomeString", welcome)
        self.assertIn("POWER_ON_DISPLAY_MODE_LOGO_MESSAGE", settings)
        self.assertIn('"ENABLE_FEAT_F4HWN_LOGO": true', cmake)
        self.assertIn("[0x98 - 0x7F]", font)
        self.assertIn("[0x99 - 0x7F]", font)

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

    def test_txlock_is_not_compiled_into_rx_only_menu(self) -> None:
        header = read("App/ui/menu.h")
        menu = read("App/ui/menu.c")
        self.assertIn("!defined(ENABLE_RX_ONLY)", header)
        self.assertIn("#ifndef ENABLE_RX_ONLY\n        case MENU_TX_LOCK", menu)


if __name__ == "__main__":
    unittest.main()
