"""Host-tool contract tests; no radio hardware is required."""

from __future__ import annotations

import struct
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from host import channels, protocol, resources, settings  # noqa: E402


class HostProtocolTests(unittest.TestCase):
    def test_frame_contains_xmodem_crc_and_expected_header(self):
        body = struct.pack("<HHI", 0x0514, 4, protocol.SESSION_TIMESTAMP)
        frame = protocol.frame_command(body)
        self.assertEqual(frame[:4], b"\xAB\xCD\x08\x00")
        packet = protocol._xorarr(frame[4:-2])
        self.assertEqual(packet[:-2], body)
        self.assertEqual(struct.unpack("<H", packet[-2:])[0],
                         protocol.crc16_xmodem(body))
        self.assertEqual(frame[-2:], b"\xDC\xBA")

    def test_calibration_is_readable_but_not_writable(self):
        protocol.validate_logical_read(0xB000, 0x200)
        with self.assertRaises(protocol.SafetyError):
            protocol.validate_logical_write(0xB000, 8)
        with self.assertRaises(protocol.SafetyError):
            protocol.validate_logical_write(0xAFF8, 16)
        with self.assertRaises(protocol.SafetyError):
            protocol.validate_logical_write(0xB1F8, 8)

    def test_only_normal_logical_ranges_are_writable(self):
        protocol.validate_logical_write(0x0000, 8)
        protocol.validate_logical_write(0xA000, 0x170)
        with self.assertRaises(protocol.SafetyError):
            protocol.validate_logical_write(0x8870, 8)
        with self.assertRaises(protocol.SafetyError):
            protocol.validate_logical_write(0x8FF8, 16)

    def test_external_ranges_are_disjoint_from_calibration(self):
        protocol.validate_external_resource_range(
            protocol.JAPANESE_FONT_BASE, protocol.JAPANESE_FONT_SIZE)
        protocol.validate_external_resource_range(
            protocol.JAPANESE_NAME_BASE, protocol.JAPANESE_NAME_SIZE)
        with self.assertRaises(protocol.SafetyError):
            protocol.validate_external_resource_range(
                protocol.CALIBRATION_FLASH_SECTOR_BASE, 1)
        with self.assertRaises(protocol.SafetyError):
            protocol.validate_external_resource_range(
                protocol.JAPANESE_FONT_BASE - 1, 2)


class JapaneseResourceTests(unittest.TestCase):
    def test_manifest_and_font_match_the_fixed_contract(self):
        manifest = resources.load_manifest()
        self.assertEqual(int(manifest["total_bytes"]), protocol.JAPANESE_FONT_SIZE)
        self.assertEqual(len(resources.load_font()), protocol.JAPANESE_FONT_SIZE)

    def test_name_table_is_exactly_1024_fixed_records(self):
        table = resources.pack_name_table(["日本語"] + [""] * 1023)
        self.assertEqual(len(table), protocol.JAPANESE_NAME_SIZE)
        self.assertEqual(table[:32], "日本語".encode("utf-8") + b"\x00" * 23)
        self.assertEqual(resources.unpack_name_table(table)[0], "日本語")
        self.assertEqual(len(resources.unpack_name_table(table)), 1024)

    def test_name_validation_rejects_unknown_long_and_wide_values(self):
        with self.assertRaises(ValueError):
            resources.pack_name_table(["😀"] + [""] * 1023)
        with self.assertRaises(ValueError):
            resources.pack_name_table(["a" * 32] + [""] * 1023)
        with self.assertRaises(ValueError):
            resources.pack_name_table(["日本語日本語"] + [""] * 1023)


class ChannelListTests(unittest.TestCase):
    def test_channel_tsv_round_trip_and_rx_only_encoding(self):
        image = bytearray(channels.CHANNEL_IMAGE_SIZE)
        struct.pack_into("<I", image, 0, 14500000)
        image[4:8] = b"\x11\x22\x33\x44"
        image[14] = channels.STEPS.index(12.5)
        struct.pack_into("<H", image, channels.CHANNEL_ATTRIBUTE_BASE, 0x0301)
        names = resources.pack_name_table(["日本語"] + [""] * 1023)

        rows = channels.decode_channel_list(bytes(image), names)
        self.assertEqual(rows[0].frequency_hz, 145000000)
        self.assertEqual(rows[0].name, "日本語")
        self.assertEqual(rows[0].scan_lists, 3)

        parsed = channels.parse_channel_list(channels.format_channel_list(rows))
        parsed[0].frequency_hz = 433920000
        parsed[0].mode = "NFM"
        parsed[0].tone_mode = "Tone"
        parsed[0].tone = 88.5
        parsed[0].name = "東京"
        updated, updated_names = channels.encode_channel_list(
            parsed, bytes(image), names)
        self.assertEqual(struct.unpack_from("<I", updated, 0)[0], 43392000)
        self.assertEqual(updated[4:8], b"\x00" * 4)
        self.assertTrue(updated[12] & 0x40)
        self.assertEqual(channels.decode_channel_list(updated, updated_names)[0].name,
                         "東京")

    def test_channel_tsv_requires_exactly_1024_ordered_rows(self):
        rows = [channels.Channel(index + 1, None) for index in range(1024)]
        text = channels.format_channel_list(rows)
        self.assertEqual(len(channels.parse_channel_list(text)), 1024)
        broken = text.splitlines()
        broken[2] = broken[2].replace("1\t", "2\t", 1)
        with self.assertRaises(ValueError):
            channels.parse_channel_list("\n".join(broken))


class SettingsModelTests(unittest.TestCase):
    def test_named_settings_round_trip_preserves_unknown_bytes(self):
        raw = bytearray(0x170)
        raw[0x167] = 0xA5  # outside every named field
        values = settings.read_settings(bytes(raw))
        values["squelch"] = "7"
        values["nfm_narrower"] = True
        updated = settings.apply_settings(bytes(raw), values)
        self.assertEqual(len(settings.fields()), 83)
        self.assertEqual(updated[0x167], 0xA5)
        self.assertEqual(updated[1], 7)
        self.assertEqual(updated[0x0E] & 0x02, 0x02)

    def test_settings_model_does_not_expose_tx_actions(self):
        action_fields = [field for field in settings.fields()
                         if field.group == "プログラマブルキー"]
        for field in action_fields:
            for label in ("電源（RX-only無効）", "VOX（無効）", "PTT（RX-only無効）"):
                self.assertNotIn(label, field.choices)


if __name__ == "__main__":
    unittest.main()
