import importlib.util
import struct
import sys
import tempfile
import types
import unittest
from pathlib import Path


def _install_chirp_stub():
    """Allow the pure driver mapping tests to run without CHIRP installed."""
    if "chirp" in sys.modules:
        return

    chirp = types.ModuleType("chirp")
    common = types.ModuleType("chirp.chirp_common")
    directory = types.ModuleType("chirp.directory")
    errors = types.ModuleType("chirp.errors")
    memmap = types.ModuleType("chirp.memmap")
    settings = types.ModuleType("chirp.settings")

    class RadioError(Exception):
        pass

    class CloneModeRadio:
        def __init__(self, _pipe=None):
            self.pipe = _pipe

        def status_fn(self, _status):
            pass

        def get_mmap(self):
            return self._mmap

    class RadioFeatures:
        pass

    class RadioPrompts:
        pass

    class Status:
        pass

    class Memory:
        def __init__(self):
            self.extra = []

    class RadioSettingValueInteger:
        def __init__(self, minimum, maximum, value):
            self.minimum = minimum
            self.maximum = maximum
            self.value = value

        def __int__(self):
            return int(self.value)

    class RadioSettingValueBoolean:
        def __init__(self, value):
            self.value = bool(value)

        def __int__(self):
            return int(self.value)

        def __bool__(self):
            return self.value

    class RadioSettingValueList:
        def __init__(self, values, current=None, fallback=None):
            self.values = tuple(values)
            self.value = current if current is not None else fallback
            if self.value is None:
                self.value = self.values[0]

        def __str__(self):
            return str(self.value)

    class RadioSettingValueString:
        def __init__(self, minimum, maximum, value):
            self.minimum = minimum
            self.maximum = maximum
            self.value = value

        def __str__(self):
            return self.value

    class RadioSetting:
        def __init__(self, name, _label, value):
            self._name = name
            self.value = value

        def get_name(self):
            return self._name

        def set_doc(self, _doc):
            pass

    class RadioSettingGroup(list):
        def __init__(self, _name, _label):
            super().__init__()
            self.name = _name
            self.label = _label

    class RadioSettings(list):
        def __init__(self, *groups):
            super().__init__(groups)

    class MemoryMapBytes:
        """Small model of CHIRP's non-buffer-backed MemoryMapBytes."""

        def __init__(self, data):
            if not isinstance(data, bytes):
                raise TypeError("MemoryMapBytes requires bytes")
            self._data = bytearray(data)

        def get(self, start, length=1):
            return bytes(self._data[start:start + length])

        def set(self, start, value):
            if isinstance(value, int):
                self._data[start] = value & 0xFF
            else:
                self._data[start:start + len(value)] = value

        def __getitem__(self, position):
            if isinstance(position, slice):
                return self.get(position.start or 0,
                                (position.stop or len(self._data)) -
                                (position.start or 0))
            return self.get(position)

        def __len__(self):
            return len(self._data)

    common.CloneModeRadio = CloneModeRadio
    common.RadioFeatures = RadioFeatures
    common.RadioPrompts = RadioPrompts
    common.Status = Status
    common.Memory = Memory
    common.CHARSET_ASCII = "ASCII"
    common.split_tone_decode = lambda *_args: None
    directory.register = lambda cls: cls
    errors.RadioError = RadioError
    memmap.MemoryMapBytes = MemoryMapBytes
    settings.InvalidValueError = ValueError
    settings.RadioSetting = RadioSetting
    settings.RadioSettingGroup = RadioSettingGroup
    settings.RadioSettings = RadioSettings
    settings.RadioSettingValueBoolean = RadioSettingValueBoolean
    settings.RadioSettingValueInteger = RadioSettingValueInteger
    settings.RadioSettingValueList = RadioSettingValueList
    settings.RadioSettingValueString = RadioSettingValueString

    chirp.chirp_common = common
    chirp.directory = directory
    chirp.errors = errors
    chirp.memmap = memmap
    sys.modules.update({
        "chirp": chirp,
        "chirp.chirp_common": common,
        "chirp.directory": directory,
        "chirp.errors": errors,
        "chirp.memmap": memmap,
        "chirp.settings": settings,
    })


_install_chirp_stub()
DRIVER_PATH = Path(__file__).parents[1] / "tools" / "chirp" / "wrx_jp.py"
SPEC = importlib.util.spec_from_file_location("wrx_jp", DRIVER_PATH)
DRIVER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DRIVER)
STANDALONE_PATH = DRIVER_PATH.with_name("wrx_jp_standalone.py")


class _ReplyPipe:
    def __init__(self, replies):
        self.replies = list(replies)
        self.writes = []
        self.timeout = None

    def write(self, data):
        self.writes.append(bytes(data))
        return len(data)

    def read(self, length):
        if not self.replies:
            return b""
        data = self.replies[0][:length]
        self.replies[0] = self.replies[0][length:]
        if not self.replies[0]:
            self.replies.pop(0)
        return data


def _wire_reply(body):
    obfuscated = DRIVER.xorarr(body)
    header = struct.pack("<HH", 0xCDAB, len(body))
    footer = b"\x00\x00\xDC\xBA"
    return header + obfuscated + footer


class TestWRXJPDriver(unittest.TestCase):
    def test_standalone_module_embeds_font_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            isolated_path = Path(directory) / STANDALONE_PATH.name
            isolated_path.write_text(
                STANDALONE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
            standalone_spec = importlib.util.spec_from_file_location(
                "wrx_jp_standalone", isolated_path)
            standalone = importlib.util.module_from_spec(standalone_spec)
            standalone_spec.loader.exec_module(standalone)

            self.assertIsNotNone(
                standalone._EMBEDDED_FONT_MANIFEST_ZLIB_BASE64)
            self.assertIsNotNone(
                standalone._EMBEDDED_FONT_BINARY_ZLIB_BASE64)
            self.assertEqual(standalone.JAPANESE_FONT_SIZE,
                             DRIVER.JAPANESE_FONT_SIZE)
            self.assertEqual(standalone._load_japanese_font_data(),
                             DRIVER._load_japanese_font_data())
            self.assertFalse(hasattr(standalone, "WRXJPUVK5"))

            writes = []
            standalone._read_external = lambda _pipe, _address, length: (
                b"\x00" * length)
            standalone._write_external_verified = (
                lambda _pipe, address, data: writes.append((address, data)))
            standalone._ensure_external_font(object())

            self.assertEqual(writes[0][0], standalone.JAPANESE_FONT_BASE)
            self.assertEqual(writes[0][1], DRIVER._load_japanese_font_data())

    def test_external_font_write_retries_protocol_errors_per_block(self):
        attempts = []

        def write_once(_pipe, address, data):
            attempts.append((address, data))
            if len(attempts) < DRIVER.EXTERNAL_WRITE_RETRIES:
                raise DRIVER.errors.RadioError("temporary write failure")

        original_write = DRIVER._write_external_once
        original_read = DRIVER._read_external
        try:
            DRIVER._write_external_once = write_once
            DRIVER._read_external = lambda _pipe, _address, length: (
                b"x" * length)
            DRIVER._write_external_verified(object(), 0x020000, b"x" * 128)
        finally:
            DRIVER._write_external_once = original_write
            DRIVER._read_external = original_read

        self.assertEqual(len(attempts), DRIVER.EXTERNAL_WRITE_RETRIES)

    def test_upload_checks_external_font_support_before_memory_writes(self):
        events = []

        class Pipe:
            timeout = None

        radio = DRIVER.WRXJPUVK1K5V3(Pipe())
        radio._mmap = bytearray(radio.PROFILE.image_size)
        original_hello = DRIVER._say_hello
        original_font = DRIVER._ensure_external_font
        original_memory = DRIVER._write_memory
        original_reset = DRIVER._reset_radio
        try:
            DRIVER._say_hello = lambda _pipe: "wrx-jp"
            DRIVER._ensure_external_font = lambda _pipe: events.append("font")
            DRIVER._write_memory = lambda *_args: events.append("memory")
            DRIVER._reset_radio = lambda _pipe: events.append("reset")
            DRIVER._upload(radio)
        finally:
            DRIVER._say_hello = original_hello
            DRIVER._ensure_external_font = original_font
            DRIVER._write_memory = original_memory
            DRIVER._reset_radio = original_reset

        self.assertEqual(events[0], "font")
        self.assertIn("memory", events)

    def test_external_read_uses_32bit_address_and_128_byte_chunks(self):
        address = 0x040000
        payload = bytes(range(130))
        replies = []
        for offset, chunk in ((0, payload[:128]), (128, payload[128:])):
            replies.append(_wire_reply(
                struct.pack("<HHIB3x", 0x0532, 8 + len(chunk),
                            address + offset, len(chunk)) + chunk))
        pipe = _ReplyPipe(replies)

        self.assertEqual(DRIVER._read_external(pipe, address, len(payload)),
                         payload)
        self.assertEqual(len(pipe.writes), 2)
        for frame, offset, length in zip(pipe.writes, (0, 128), (128, 2)):
            command = DRIVER.xorarr(frame[4:-2])
            self.assertEqual(
                struct.unpack_from("<HHIB3xI", command),
                (0x0531, 12, address + offset, length,
                 DRIVER.EXTERNAL_SESSION_TIMESTAMP))
            self.assertEqual(
                struct.unpack_from("<H", command, len(command) - 2)[0],
                DRIVER._crc16_xmodem(command[:-2]))

    def test_external_write_checks_32bit_address_and_status(self):
        address = 0x020000
        payload = b"font-block"
        response = struct.pack("<HHIBBH", 0x0534, 8, address,
                               len(payload), 0, 0)
        pipe = _ReplyPipe([_wire_reply(response)])

        DRIVER._write_external_once(pipe, address, payload)
        self.assertEqual(len(pipe.writes), 1)
        command = DRIVER.xorarr(pipe.writes[0][4:-2])
        self.assertEqual(
            struct.unpack_from("<HHIBBHI", command),
            (0x0533, 12 + len(payload), address, len(payload), 1, 0,
             DRIVER.EXTERNAL_SESSION_TIMESTAMP))
        self.assertEqual(command[16:-2], payload)
        self.assertEqual(
            struct.unpack_from("<H", command, len(command) - 2)[0],
            DRIVER._crc16_xmodem(command[:-2]))

    def test_driver_accepts_chirp_pipe_argument(self):
        pipe = object()
        radio = DRIVER.WRXJPUVK1K5V3(pipe)
        self.assertIs(radio.pipe, pipe)

    def test_k1_k5v3_profile_uses_1024_channels(self):
        radio = DRIVER.WRXJPUVK1K5V3()

        self.assertEqual(radio.PROFILE.memory_channels, 1024)
        self.assertEqual(radio.PROFILE.name_base, 0x4000)
        self.assertEqual(radio.PROFILE.attr_width, 2)
        self.assertEqual(radio._channel_offset(False, 1023), 0x3FF0)
        self.assertEqual(radio._name_offset(1023), 0x7FF0)
        self.assertEqual(radio._channel_offset(True, 0), 0x9000)

    def test_rx_only_tone_and_mode_encoding(self):
        radio = DRIVER.WRXJPUVK1K5V3()
        raw = bytearray(16)
        memory = types.SimpleNamespace(
            tmode="TSQL", ctone=88.5, rtone=88.5, dtcs=None,
            rx_dtcs_polarity="N")

        radio._encode_tone(memory, raw)
        self.assertEqual(raw[8], DRIVER.CTCSS_TONES.index(88.5))
        self.assertEqual(raw[9], 0)
        self.assertEqual(raw[10] & 0x0F, 1)
        self.assertEqual(raw[10] & 0xF0, 0)

        radio._set_mode(raw, "AM")
        self.assertEqual(radio._get_mode(raw), "AM")
        self.assertEqual(raw[11] & 0x0F, 0)

    def test_set_memory_forces_rx_lock_and_uses_profile_map(self):
        radio = DRIVER.WRXJPUVK1K5V3()
        radio._mmap = bytearray(radio.PROFILE.image_size)
        memory = types.SimpleNamespace(
            number=1, extd_number=None, empty=False, freq=145500000,
            offset=0, duplex="+", mode="NFM", tmode="", tuning_step=12.5,
            name="呼出", extra=[])

        radio.set_memory(memory)
        raw = radio._mmap[:16]
        self.assertEqual(int.from_bytes(raw[0:4], "little"), 14550000)
        self.assertEqual(int.from_bytes(raw[4:8], "little"), 0)
        self.assertEqual(raw[12] & 0x40, 0x40)
        self.assertEqual(raw[12] & 0x02, 0x02)
        self.assertEqual(radio._mmap[0x4000:0x4006], b"\x00\x00\x00\x00\x00\x00")
        self.assertEqual(radio._mmap[0x8000] & 0x07, 2)

    def test_k1_exposes_japanese_name_contract(self):
        k1 = DRIVER.WRXJPUVK1K5V3()

        k1_features = k1.get_features()
        self.assertEqual(k1_features.valid_name_length, 10)
        for character in "日本語":
            self.assertIn(character, k1_features.valid_characters)

    def test_japanese_name_is_stored_in_external_table_and_round_trips(self):
        radio = DRIVER.WRXJPUVK1K5V3()
        radio._mmap = bytearray(radio.PROFILE.image_size)
        memory = types.SimpleNamespace(
            number=1, extd_number=None, empty=False, freq=145500000,
            offset=0, duplex="", mode="FM", tmode="", tuning_step=12.5,
            name="日本語", extra=[])

        radio.set_memory(memory)
        record = "日本語".encode("utf-8")
        self.assertEqual(
            bytes(radio._japanese_names[:DRIVER.JAPANESE_NAME_RECORD_SIZE]),
            record.ljust(DRIVER.JAPANESE_NAME_RECORD_SIZE, b"\x00"))
        self.assertEqual(bytes(radio._mmap[0x4000:0x4010]), b"\x00" * 16)
        self.assertTrue(radio._japanese_names_dirty)
        self.assertEqual(radio.get_memory(1).name, "日本語")

    def test_replacing_japanese_name_with_ascii_clears_external_record(self):
        radio = DRIVER.WRXJPUVK1K5V3()
        radio._mmap = bytearray(radio.PROFILE.image_size)
        japanese = types.SimpleNamespace(
            number=1, extd_number=None, empty=False, freq=145500000,
            offset=0, duplex="", mode="FM", tmode="", tuning_step=12.5,
            name="日本語", extra=[])
        ascii_name = types.SimpleNamespace(
            number=1, extd_number=None, empty=False, freq=145500000,
            offset=0, duplex="", mode="FM", tmode="", tuning_step=12.5,
            name="CALL", extra=[])

        radio.set_memory(japanese)
        radio.set_memory(ascii_name)
        self.assertEqual(bytes(radio._japanese_names[:32]), b"\x00" * 32)
        self.assertEqual(bytes(radio._mmap[0x4000:0x4004]), b"CALL")
        self.assertEqual(radio.get_memory(1).name, "CALL")

    def test_japanese_name_validation_rejects_unsupported_or_too_wide_names(self):
        self.assertEqual(DRIVER._validate_japanese_name("日本語"),
                         "日本語".encode("utf-8"))
        with self.assertRaises(DRIVER.errors.RadioError):
            DRIVER._validate_japanese_name("日本語日本語")
        with self.assertRaises(DRIVER.errors.RadioError):
            DRIVER._validate_japanese_name("😀")
        with self.assertRaises(DRIVER.errors.RadioError):
            DRIVER._validate_japanese_name("\ud800")

    def test_fm_settings_use_japanese_76_to_95_range(self):
        radio = DRIVER.WRXJPUVK1K5V3()
        radio._mmap = bytearray(radio.PROFILE.image_size)
        DRIVER._put_u16(radio._mmap, radio.PROFILE.fm_cfg, 800)
        DRIVER._put_u16(radio._mmap, radio.PROFILE.fm_channels, 950)
        settings = radio.get_settings()
        fm = settings[-1]
        self.assertEqual(len(fm), 49)
        self.assertEqual(fm[0].value.value, 800)
        self.assertEqual(fm[1].value.value, 950)
        self.assertEqual(fm[48].get_name(), "fm_48")
        self.assertEqual(DRIVER._rounded_upload_end(0x886E), 0x8870)

    def test_fm_settings_support_chirp_memory_map_bytes(self):
        radio = DRIVER.WRXJPUVK1K5V3()
        radio._mmap = DRIVER.memmap.MemoryMapBytes(
            bytes(radio.PROFILE.image_size))
        radio._set_mmap_u16(radio.PROFILE.fm_cfg, 800)
        radio._set_mmap_u16(radio.PROFILE.fm_channels, 950)

        settings = radio.get_settings()
        fm = settings[-1]
        self.assertEqual(fm[0].value.value, 800)
        self.assertEqual(fm[1].value.value, 950)

        fm[0].value.value = 810
        radio.set_settings(settings)
        self.assertEqual(
            radio._mmap.get(radio.PROFILE.fm_cfg, 2),
            (810).to_bytes(2, "little"))
        self.assertEqual(DRIVER._rounded_upload_end(0x90E7), 0x90E8)

    @staticmethod
    def _settings_by_name(settings):
        result = {}
        for group in settings:
            for setting in group:
                result[setting.get_name()] = setting
        return result

    def test_settings_expose_f4hwn_receive_controls(self):
        radio = DRIVER.WRXJPUVK1K5V3()
        radio._mmap = bytearray(radio.PROFILE.image_size)
        radio._mmap[radio.PROFILE.settings_base + 1] = 7
        radio._mmap[radio.PROFILE.settings_base + 9] = 2
        radio._mmap[radio.PROFILE.settings_base + 11] = 5
        radio._mmap[radio.PROFILE.action_settings_base + 5] = 0
        radio._mmap[radio.PROFILE.f4hwn_base + 5] = 0x50 | 12

        settings = radio.get_settings()
        values = self._settings_by_name(settings)
        for name in (
                "squelch", "channel_display_mode", "battery_save",
                "dual_watch", "backlight_time", "scan_resume_mode",
                "power_on_display_mode", "key1_shortpress_action",
                "keyM_longpress_action", "contrast", "invert_display",
                "audio_fm", "audio_am", "nfm_narrower", "logo_1", "fm_48"):
            self.assertIn(name, values)
        self.assertEqual(values["squelch"].value.value, 7)
        self.assertEqual(str(values["channel_display_mode"].value), "名前")
        self.assertEqual(values["contrast"].value.value, 12)
        self.assertEqual(values["battery_type"].value.values[3], "1500mAh K1")
        self.assertIn("受信専用", values["key1_shortpress_action"].value.values)
        self.assertIn("ロゴ＋メッセージ", values["power_on_display_mode"].value.values)
        self.assertEqual(values["menu_lock_mode"].value.values[1], "キー＋操作")

        for name in ("tx_power", "tot", "tx_tone", "calibration", "dtmf"):
            self.assertNotIn(name, values)

    def test_settings_return_all_f4hwn_style_groups(self):
        radio = DRIVER.WRXJPUVK1K5V3()
        radio._mmap = bytearray(radio.PROFILE.image_size)

        settings = radio.get_settings()

        self.assertEqual(
            [group.name for group in settings],
            ["basic", "display", "keys", "scan", "f4hwn", "logo", "fm"])
        self.assertEqual(
            [group.label for group in settings],
            ["基本設定", "表示・操作", "プログラマブルキー", "スキャン設定",
             "F4HWN受信設定", "起動画面ロゴ", "FM放送受信"])

    def test_settings_write_to_k1_external_flash_map_without_tx_fields(self):
        radio = DRIVER.WRXJPUVK1K5V3()
        radio._mmap = bytearray(radio.PROFILE.image_size)
        settings = radio.get_settings()
        values = self._settings_by_name(settings)

        values["squelch"].value.value = 4
        values["channel_display_mode"].value.value = "名前＋周波数"
        values["battery_save"].value.value = "1:5"
        values["dual_watch"].value.value = "B"
        values["backlight_min"].value.value = 2
        values["backlight_max"].value.value = 8
        values["beep_control"].value.value = True
        values["key1_shortpress_action"].value.value = "スキャン"
        values["scan_list_default"].value.value = "全チャンネル"
        values["scan_list_enabled"].value.value = True
        values["priority_channel_1"].value.value = 3
        values["nfm_narrower"].value.value = True
        values["contrast"].value.value = 13
        values["invert_display"].value.value = True
        values["logo_1"].value.value = "WRX-JP"

        radio.set_settings(settings)
        main = radio.PROFILE.settings_base
        action = radio.PROFILE.action_settings_base
        scan = radio.PROFILE.scan_settings_base
        f4hwn = radio.PROFILE.f4hwn_base
        self.assertEqual(radio._mmap[main + 1], 4)
        self.assertEqual(radio._mmap[main + 8], 0x28)
        self.assertEqual(radio._mmap[main + 9], 3)
        self.assertEqual(radio._mmap[main + 11], 5)
        self.assertEqual(radio._mmap[main + 12], 2)
        self.assertEqual(radio._mmap[main + 14] & 0x02, 0x02)
        self.assertEqual(radio._mmap[action + 1], 4)
        self.assertEqual(radio._mmap[scan], 0x99)
        self.assertEqual(int.from_bytes(radio._mmap[scan + 1:scan + 3], "little"), 2)
        self.assertEqual(radio._mmap[f4hwn + 5], 0x1D)
        self.assertEqual(
            bytes(radio._mmap[radio.PROFILE.logo_base:radio.PROFILE.logo_base + 7]),
            b"WRX-JP\x00")

    def test_all_settings_support_chirp_memory_map_bytes(self):
        radio = DRIVER.WRXJPUVK1K5V3()
        radio._mmap = DRIVER.memmap.MemoryMapBytes(
            bytes(radio.PROFILE.image_size))
        settings = radio.get_settings()
        values = self._settings_by_name(settings)
        values["squelch"].value.value = 6
        values["backlight_min"].value.value = 1
        values["backlight_max"].value.value = 5
        radio.set_settings(settings)
        self.assertEqual(
            radio._mmap.get(radio.PROFILE.settings_base + 1), b"\x06")
        self.assertEqual(
            radio._mmap.get(radio.PROFILE.settings_base + 8), b"\x15")


if __name__ == "__main__":
    unittest.main()
