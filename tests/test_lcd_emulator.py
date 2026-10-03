"""実機LCDデバッグ経路のプロトコルと画像化を検査する。"""

from __future__ import annotations

import io
import json
import struct
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import lcd_emulator  # noqa: E402


class LcdEmulatorTests(unittest.TestCase):
    def test_frame_requires_the_complete_physical_lcd_buffer(self):
        with self.assertRaises(ValueError):
            lcd_emulator.LcdFrame.from_bytes(b"short")

        frame = lcd_emulator.LcdFrame.from_bytes(bytes(lcd_emulator.LCD_BYTES))
        self.assertEqual(len(frame.data), lcd_emulator.LCD_BYTES)

    def test_image_maps_st7565_page_bits_to_pixels(self):
        data = bytearray(lcd_emulator.LCD_BYTES)
        x, y = 7, 9
        data[(y // 8) * lcd_emulator.LCD_WIDTH + x] = 1 << (y % 8)
        image = lcd_emulator.LcdFrame(data).image(scale=1)

        self.assertNotEqual(image.getpixel((x, y)), image.getpixel((0, 0)))
        self.assertEqual(image.size, (lcd_emulator.LCD_WIDTH, lcd_emulator.LCD_HEIGHT))

    def test_xmodem_crc_known_vector(self):
        self.assertEqual(lcd_emulator.crc16_xmodem(b"123456789"), 0x31C3)

    def test_request_uses_the_existing_uart_command_framing(self):
        request = lcd_emulator.build_request("menu")
        self.assertEqual(request[:2], b"\xAB\xCD")
        self.assertEqual(request[-2:], b"\xDC\xBA")
        self.assertEqual(request[2], 6)

        packet = lcd_emulator._xorarr(request[4:-2])
        self.assertEqual(len(packet), 8)
        command, size, event, reserved, crc = struct.unpack("<HHBBH", packet)
        command_body = packet[:6]
        self.assertEqual(command, lcd_emulator.LCD_DEBUG_COMMAND_ID)
        self.assertEqual(size, 2)
        self.assertEqual(event, lcd_emulator.EVENTS["menu"])
        self.assertEqual(reserved, 0)
        self.assertEqual(crc, lcd_emulator.crc16_xmodem(command_body))

    def test_read_frame_syncs_after_uart_startup_text(self):
        data = bytes(range(256)) * 4
        header = lcd_emulator.LCD_DEBUG_FRAME_HEADER.pack(
            lcd_emulator.LCD_DEBUG_FRAME_MAGIC,
            lcd_emulator.LCD_DEBUG_PROTOCOL_VERSION,
            lcd_emulator.EVENTS["menu"],
            0,
            0,
            lcd_emulator.LCD_BYTES,
            lcd_emulator.crc16_xmodem(data),
        )
        captured = lcd_emulator.read_frame(io.BytesIO(b"WRX-JP\x00" + header + data))

        self.assertEqual(captured.event, lcd_emulator.EVENTS["menu"])
        self.assertEqual(captured.status, 0)
        self.assertEqual(captured.frame.data, bytearray(data))

    def test_read_frame_rejects_bad_crc_and_size(self):
        data = bytes(lcd_emulator.LCD_BYTES)
        valid_header = lcd_emulator.LCD_DEBUG_FRAME_HEADER.pack(
            lcd_emulator.LCD_DEBUG_FRAME_MAGIC,
            lcd_emulator.LCD_DEBUG_PROTOCOL_VERSION,
            lcd_emulator.EVENTS["menu"],
            0,
            0,
            lcd_emulator.LCD_BYTES,
            0x1234,
        )
        with self.assertRaises(lcd_emulator.CaptureError):
            lcd_emulator.read_frame(io.BytesIO(valid_header + data))

        short_header = lcd_emulator.LCD_DEBUG_FRAME_HEADER.pack(
            lcd_emulator.LCD_DEBUG_FRAME_MAGIC,
            lcd_emulator.LCD_DEBUG_PROTOCOL_VERSION,
            lcd_emulator.EVENTS["menu"],
            0,
            0,
            lcd_emulator.LCD_BYTES - 1,
            0,
        )
        with self.assertRaises(lcd_emulator.CaptureError):
            lcd_emulator.read_frame(io.BytesIO(short_header))

    def test_standard_event_ids_match_the_firmware_header(self):
        header = (ROOT / "App" / "app" / "lcd_debug.h").read_text(encoding="utf-8")
        expected = {
            "MENU": 1,
            "MENU_HELP": 2,
            "PRESET_BANK": 3,
            "SCAN_LIST_NAME": 4,
            "SCAN_MEMORY": 5,
            "SCAN_DUAL": 6,
            "SCAN_RANGE": 7,
            "RECEIVE_MAIN": 8,
            "RECEIVE_DUAL": 9,
            "MENU_CAT_CHANNELS": 10,
            "MENU_CAT_SCAN": 11,
            "MENU_CAT_KEYS": 12,
            "MENU_CAT_POWER": 13,
            "MENU_CAT_DISPLAY": 14,
            "MENU_CAT_TIMERS": 15,
            "MENU_CAT_AUDIO": 16,
            "MENU_CAT_RADIO": 17,
            "MENU_CAT_DTMF": 18,
            "MENU_CAT_SERVICE": 19,
            "MENU_CAT_ALL": 20,
            "MENU_ITEM_DCS_OFF": 21,
            "MENU_ITEM_DCS_FORWARD": 22,
            "MENU_ITEM_DCS_REVERSE": 23,
            "MENU_ITEM_CTCS_FORWARD": 24,
            "MENU_ITEM_CTCS_REVERSE": 25,
            "MENU_ITEM_W_N": 26,
            "MENU_ITEM_LONG": 27,
            "MENU_ITEM_CONFIRM": 28,
            "MENU_ITEM_CSS_SCAN": 29,
            "MENU_ITEM_FONT_16": 30,
            "MENU_ITEM_FONT_8": 31,
            "MENU_ITEM_FONT_ASCII": 32,
            "MENU_ITEM_FONT_14": 33,
            "MENU_ITEM_ACTION": 34,
            "WARNING_RX_ONLY": 35,
            "WARNING_FM_ONLY": 36,
            "WARNING_RX_EXT_OFF": 37,
            "WARNING_PRESET_FAIL": 38,
            "WARNING_SCAN_ACTIVE": 39,
            "WARNING_SCAN_COMPLETE": 40,
            "WARNING_SCAN_FAILED": 41,
            "RECEIVE_FREQUENCY": 42,
            "RECEIVE_CHANNEL": 43,
            "RECEIVE_NAME_16": 44,
            "RECEIVE_NAME_FREQ": 45,
            "RECEIVE_NAME_8": 46,
            "RECEIVE_NAME_14": 47,
            "RECEIVE_NAME_ASCII": 48,
            "RECEIVE_DUAL_NAME": 49,
            "RECEIVE_JP_NAME_16": 50,
            "RECEIVE_JP_NAME_14": 51,
            "RECEIVE_JP_NAME_8": 52,
            "RECEIVE_JP_NAME_FREQ": 53,
            "RECEIVE_JP_DUAL_NAME": 54,
            "RECEIVE_AUDIO_SILENCE": 55,
            "RECEIVE_AUDIO_LOW": 56,
            "RECEIVE_AUDIO_SPEECH": 57,
            "RECEIVE_AUDIO_STRONG": 58,
            "RECEIVE_AUDIO_ALTERNATING": 59,
            "RECEIVE_AUDIO_IMPULSE": 60,
            "RECEIVE_AUDIO_STAIRCASE": 61,
            "RECEIVE_AUDIO_CLIPPING": 62,
            "RECEIVE_AUDIO_MAIN": 63,
            "RECEIVE_AUDIO_DUAL": 64,
            "RECEIVE_AM": 65,
            "RECEIVE_USB": 66,
            "RECEIVE_CTCSS": 67,
            "RECEIVE_CTCSS_REVERSE": 68,
            "RECEIVE_DCS": 69,
            "RECEIVE_DCS_REVERSE": 70,
            "RECEIVE_BANDWIDTH_WIDE_PLUS": 71,
            "RECEIVE_BANDWIDTH_WIDE": 72,
            "RECEIVE_BANDWIDTH_NARROW": 73,
            "RECEIVE_BANDWIDTH_NARROWER": 74,
            "RECEIVE_MONITOR": 75,
            "RECEIVE_DUAL_B": 76,
            "MAIN_LOW_BATTERY": 77,
            "MAIN_KEYPAD_LOCK": 78,
            "STATUS_NORMAL": 79,
            "STATUS_SCAN": 80,
            "STATUS_DUAL": 81,
            "STATUS_KEY_LOCK": 82,
            "STATUS_BACKLIGHT": 83,
            "STATUS_MUTE": 84,
            "MAIN_DTMF": 85,
            "MAIN_SCAN_RANGE": 86,
            "RECEIVE_SCANLIST_PRESENT": 87,
        }
        for name, event_id in expected.items():
            self.assertRegex(
                header,
                rf"LCD_DEBUG_EVENT_{name}\s*=\s*{event_id}\b",
            )
        self.assertEqual(
            lcd_emulator.EVENTS,
            {
                "menu": 1,
                "menu-help": 2,
                "preset-bank": 3,
                "scan-list-name": 4,
                "scan-memory": 5,
                "scan-dual": 6,
                "scan-range": 7,
                "receive-main": 8,
                "receive-dual": 9,
                "menu-cat-channels": 10,
                "menu-cat-scan": 11,
                "menu-cat-keys": 12,
                "menu-cat-power": 13,
                "menu-cat-display": 14,
                "menu-cat-audio": 16,
                "menu-cat-radio": 17,
                "menu-cat-dtmf": 18,
                "menu-cat-service": 19,
                "menu-cat-all": 20,
                "menu-item-dcs-off": 21,
                "menu-item-dcs-forward": 22,
                "menu-item-dcs-reverse": 23,
                "menu-item-ctcs-forward": 24,
                "menu-item-ctcs-reverse": 25,
                "menu-item-w-n": 26,
                "menu-item-long": 27,
                "menu-item-confirm": 28,
                "menu-item-css-scan": 29,
                "menu-item-font-16": 30,
                "menu-item-font-8": 31,
                "menu-item-font-ascii": 32,
                "menu-item-font-14": 33,
                "menu-item-action": 34,
                "warning-rx-only": 35,
                "warning-fm-only": 36,
                "warning-rx-ext-off": 37,
                "warning-preset-fail": 38,
                "warning-scan-active": 39,
                "warning-scan-complete": 40,
                "warning-scan-failed": 41,
                "receive-frequency": 42,
                "receive-channel": 43,
                "receive-name-16": 44,
                "receive-name-freq": 45,
                "receive-name-8": 46,
                "receive-name-14": 47,
                "receive-name-ascii": 48,
                "receive-dual-name": 49,
                "receive-jp-name-16": 50,
                "receive-jp-name-14": 51,
                "receive-jp-name-8": 52,
                "receive-jp-name-freq": 53,
                "receive-jp-dual-name": 54,
                "receive-audio-silence": 55,
                "receive-audio-low": 56,
                "receive-audio-speech": 57,
                "receive-audio-strong": 58,
                "receive-audio-alternating": 59,
                "receive-audio-impulse": 60,
                "receive-audio-staircase": 61,
                "receive-audio-clipping": 62,
                "receive-audio-main": 63,
                "receive-audio-dual": 64,
                "receive-am": 65,
                "receive-usb": 66,
                "receive-ctcss": 67,
                "receive-ctcss-reverse": 68,
                "receive-dcs": 69,
                "receive-dcs-reverse": 70,
                "receive-bandwidth-wide-plus": 71,
                "receive-bandwidth-wide": 72,
                "receive-bandwidth-narrow": 73,
                "receive-bandwidth-narrower": 74,
                "receive-monitor": 75,
                "receive-dual-b": 76,
                "main-low-battery": 77,
                "main-keypad-lock": 78,
                "status-normal": 79,
                "status-scan": 80,
                "status-dual": 81,
                "status-key-lock": 82,
                "status-backlight": 83,
                "status-mute": 84,
                "main-dtmf": 85,
                "main-scan-range": 86,
                "receive-scanlist-present": 87,
            },
        )

    def test_tool_contains_no_python_layout_renderer(self):
        source = (ROOT / "tools" / "lcd_emulator.py").read_text(encoding="utf-8")
        self.assertNotIn("def render_menu", source)
        self.assertNotIn("def render_receive", source)
        self.assertIn("def read_frame", source)
        self.assertIn("LcdFrame.from_bytes", source)

    def test_firmware_captures_the_physical_buffers(self):
        source = (ROOT / "App" / "app" / "lcd_debug.c").read_text(encoding="utf-8")
        for required in (
            "LCD_DEBUG_FRAME_BYTES",
            "gStatusLine",
            "gFrameBuffer",
            "LCD_DEBUG_COMMAND_ID",
            "UART_Send(frame, sizeof(frame))",
        ):
            self.assertIn(required, source)

    def test_japanese_name_patterns_are_deterministic(self):
        source = (ROOT / "App" / "app" / "lcd_debug.c").read_text(encoding="utf-8")
        self.assertIn('JPFONT_DebugSetChannelName(MR_CHANNEL_FIRST, "東京空港")', source)
        self.assertIn(
            'JPFONT_DebugSetChannelName(MR_CHANNEL_FIRST + 1u, "羽田AIR")',
            source,
        )

    def test_scope_patterns_use_the_firmware_renderer(self):
        debug_source = (ROOT / "App" / "app" / "lcd_debug.c").read_text(encoding="utf-8")
        main_source = (ROOT / "App" / "ui" / "main.c").read_text(encoding="utf-8")
        for name in (
            "RECEIVE_AUDIO_SILENCE",
            "RECEIVE_AUDIO_LOW",
            "RECEIVE_AUDIO_SPEECH",
            "RECEIVE_AUDIO_STRONG",
            "RECEIVE_AUDIO_ALTERNATING",
            "RECEIVE_AUDIO_IMPULSE",
            "RECEIVE_AUDIO_STAIRCASE",
            "RECEIVE_AUDIO_CLIPPING",
            "RECEIVE_AUDIO_MAIN",
            "RECEIVE_AUDIO_DUAL",
        ):
            self.assertIn(f"LCD_DEBUG_EVENT_{name}", debug_source)
        self.assertIn("UI_DisplayAudioScope();", debug_source)
        self.assertIn("g_scope_debug_input ? g_scope_debug_amplitude", main_source)
        self.assertIn("void UI_MAIN_DebugResetAudioScope(void)", main_source)
        self.assertIn(
            "#ifndef ENABLE_LCD_DEBUG\n    BK4819_ToggleGpioOut",
            main_source,
        )

    def test_real_rf_scope_limit_is_documented(self):
        docs = (ROOT / "docs" / "LCD_EMULATOR.ja.md").read_text(encoding="utf-8")
        hardware = (ROOT / "docs" / "HARDWARE_TEST_PLAN.ja.md").read_text(encoding="utf-8")
        self.assertIn("音声内容そのもの、スケルチ開閉、受信音、実際のRFスキャンは再現しない", docs)
        self.assertIn("| RF-01 |", hardware)
        self.assertIn("| AUDIO-04 |", hardware)

    def test_scan_range_pattern_does_not_share_the_status_page(self):
        source = (ROOT / "App" / "ui" / "main.c").read_text(encoding="utf-8")
        start = source.index("if(gScanRangeStart)")
        end = source.index("if (gDTMF_InputMode", start)
        self.assertIn("範囲表示は2行を使うため", source[start:end])
        self.assertIn("continue;", source[start:end])

    def test_debug_path_does_not_initialize_rf_or_write_settings(self):
        board = (ROOT / "App" / "board.c").read_text(encoding="utf-8")
        settings = (ROOT / "App" / "settings.c").read_text(encoding="utf-8")
        self.assertIn(
            "#ifndef ENABLE_LCD_DEBUG\n    BK1080_Init0();",
            board,
        )
        self.assertIn(
            "#ifndef ENABLE_LCD_DEBUG\n        if (strncmp(storedVersion",
            settings,
        )

    def test_debug_preset_is_available(self):
        presets = json.loads((ROOT / "CMakePresets.json").read_text(encoding="utf-8"))
        configure = {preset["name"]: preset for preset in presets["configurePresets"]}
        build = {preset["name"]: preset for preset in presets["buildPresets"]}
        self.assertTrue(configure["JpLcdDebug"]["cacheVariables"]["ENABLE_LCD_DEBUG"])
        self.assertEqual(build["JpLcdDebug"]["configurePreset"], "JpLcdDebug")


if __name__ == "__main__":
    unittest.main()
