"""RX-safe, named settings model for the K1/K5 V3 settings window.

The offsets mirror the existing K1 CHIRP profile.  Unknown bytes in the
0xA000-0xA16F block are preserved; this module only edits named fields that
are already exposed by the RX-only profile.
"""

from __future__ import annotations

from dataclasses import dataclass


SETTINGS_SIZE = 0x170
FM_MIN = 760
FM_MAX = 950
PRESERVE_DISABLED = "（既存の無効値を保持）"


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    group: str
    kind: str
    minimum: int = 0
    maximum: int = 0
    choices: tuple[str, ...] = ()


def _backlight_choices() -> tuple[str, ...]:
    result = ["OFF"]
    for seconds in range(5, 301, 5):
        if seconds < 60:
            result.append("{}秒".format(seconds))
        elif seconds % 60 == 0:
            result.append("{}分".format(seconds // 60))
        else:
            result.append("{}分{:02d}秒".format(seconds // 60, seconds % 60))
    result.append("常時点灯")
    return tuple(result)


def _auto_lock_choices() -> tuple[str, ...]:
    return tuple(["OFF"] + ["{}分{:02d}秒".format(value // 60, value % 60)
                            for value in range(15, 601, 15)])


def _scan_resume_choices() -> tuple[str, ...]:
    result = ["停止"]
    result.extend("キャリア解消後 {:.2f}秒".format(value * 0.25)
                  for value in range(1, 81))
    result.extend("タイムアウト後 {}秒".format((value - 80) * 5)
                  for value in range(81, 105))
    return tuple(result)


ACTION_CHOICES = (
    "なし", "ライト", "モニター", "スキャン", "FMラジオ", "キーロック",
    "A/B切替", "VFO/メモリ切替", "モード切替", "最低輝度解除", "受信モード",
    "受信専用", "W/N", "バックライト", "ミュート", "受信音声",
)
# Values are deliberately explicit because the firmware enum contains
# disabled TX/VOX/alarm values between these RX-safe options.
ACTION_RAW = {
    "なし": 0, "ライト": 1, "モニター": 3, "スキャン": 4,
    "FMラジオ": 7, "キーロック": 9, "A/B切替": 10,
    "VFO/メモリ切替": 11, "モード切替": 12, "最低輝度解除": 13,
    "受信モード": 14, "受信専用": 15, "W/N": 17,
    "バックライト": 18, "ミュート": 19, "受信音声": 20,
}


def _choice_field(key: str, label: str, group: str,
                  choices: tuple[str, ...]) -> Field:
    return Field(key, label, group, "choice", choices=choices)


def _int_field(key: str, label: str, group: str,
               minimum: int, maximum: int) -> Field:
    return Field(key, label, group, "int", minimum, maximum)


def _bool_field(key: str, label: str, group: str) -> Field:
    return Field(key, label, group, "bool")


def fields() -> tuple[Field, ...]:
    channel_display = ("周波数", "チャンネル番号", "名前", "名前＋周波数")
    battery_save = ("OFF", "1:1", "1:2", "1:3", "1:4", "1:5")
    dual_watch = ("OFF", "A", "B")
    power_on = ("全画面", "音声", "メッセージ", "電圧", "ロゴ",
                "ロゴ＋メッセージ", "ロゴ＋全画面", "なし")
    battery_type = ("1600mAh K5", "2200mAh K5", "3500mAh K5",
                    "1500mAh K1", "2500mAh K1")
    menu_lock = ("キー", "キー＋操作", "キー＋PTT", "キー＋操作＋PTT")
    scan_lists = tuple(["リスト {}".format(i) for i in range(1, 25)] +
                       ["全チャンネル"])
    action_choices = ACTION_CHOICES + (PRESERVE_DISABLED,)
    result = [
        _int_field("squelch", "スケルチ", "基本設定", 0, 9),
        _choice_field("channel_display_mode", "チャンネル表示", "基本設定", channel_display),
        _choice_field("battery_save", "バッテリーセーブ", "基本設定", battery_save),
        _choice_field("dual_watch", "デュアル受信", "基本設定", dual_watch),
        _choice_field("backlight_time", "バックライト時間", "基本設定", _backlight_choices()),
        _choice_field("scan_resume_mode", "スキャン再開", "基本設定", _scan_resume_choices()),
        _choice_field("power_on_display_mode", "起動画面", "基本設定", power_on),
        _choice_field("battery_type", "バッテリー種別", "基本設定", battery_type),
        _int_field("backlight_min", "バックライト最低輝度", "表示・操作", 0, 10),
        _int_field("backlight_max", "バックライト最高輝度", "表示・操作", 0, 10),
        _int_field("contrast", "コントラスト", "表示・操作", 1, 15),
        _bool_field("invert_display", "表示反転", "表示・操作"),
        _choice_field("meter_style", "Sメーター表示", "表示・操作", ("TINY", "CLASSIC")),
        _bool_field("gui_style", "GUI表示", "表示・操作"),
        _choice_field("menu_lock_mode", "メニューロック範囲", "表示・操作", menu_lock),
        _choice_field("sleep_timer", "スリープタイマー", "表示・操作",
                      tuple(["OFF"] + ["{}分".format(i) for i in range(1, 121)])),
        _bool_field("beep_control", "キービープ", "表示・操作"),
        _bool_field("key_lock", "キーロック", "表示・操作"),
        _choice_field("auto_keypad_lock", "自動キーロック", "表示・操作", _auto_lock_choices()),
    ]
    for key, label in (
            ("key1_shortpress_action", "サイドキー1 短押し"),
            ("key1_longpress_action", "サイドキー1 長押し"),
            ("key2_shortpress_action", "サイドキー2 短押し"),
            ("key2_longpress_action", "サイドキー2 長押し"),
            ("keyM_longpress_action", "［M］長押し")):
        result.append(_choice_field(key, label, "プログラマブルキー", action_choices))
    result.extend([
        _choice_field("scan_list_default", "標準スキャンリスト", "スキャン設定", scan_lists),
        _bool_field("scan_list_enabled", "標準スキャンリストを有効化", "スキャン設定"),
        _int_field("priority_channel_1", "優先チャンネル1（0=未設定）", "スキャン設定", 0, 1024),
        _int_field("priority_channel_2", "優先チャンネル2（0=未設定）", "スキャン設定", 0, 1024),
        _int_field("call_channel", "コールチャンネル（0=未設定）", "スキャン設定", 0, 1024),
        _choice_field("audio_fm", "FM受信音声プロファイル", "F4HWN受信設定",
                      ("FLAT", "CLEAN", "MID", "BOOST", "MAX")),
        _choice_field("audio_am", "AM受信音声プロファイル", "F4HWN受信設定",
                      ("SHARP", "STOCK", "OPEN")),
        _bool_field("nfm_narrower", "NFMナロー化", "F4HWN受信設定"),
        Field("logo_1", "ロゴ1（ASCII 16文字）", "起動画面ロゴ", "ascii",
              maximum=16),
        Field("logo_2", "ロゴ2（ASCII 16文字）", "起動画面ロゴ", "ascii",
              maximum=16),
        _int_field("fm_current", "現在周波数（0.1 MHz）", "FM放送受信", FM_MIN, FM_MAX),
    ])
    for index in range(1, 49):
        result.append(_int_field("fm_{:02d}".format(index),
                                 "FM {:02d}（0=空き, 0.1 MHz）".format(index),
                                 "FM放送受信", 0, FM_MAX))
    return tuple(result)


def _u16(data: bytearray, offset: int) -> int:
    return data[offset] | (data[offset + 1] << 8)


def _put_u16(data: bytearray, offset: int, value: int) -> None:
    data[offset] = value & 0xFF
    data[offset + 1] = (value >> 8) & 0xFF


def _safe_choice(choices: tuple[str, ...], raw: int, default: int = 0) -> str:
    return choices[raw] if 0 <= raw < len(choices) else choices[default]


def read_settings(data: bytes) -> dict[str, object]:
    if len(data) != SETTINGS_SIZE:
        raise ValueError("settings block must be exactly 0x170 bytes")
    raw = bytearray(data)
    main = raw[:16]
    actions = raw[0xA8:0xF8]
    scan = raw[0x130:0x138]
    f4 = raw[0x158:0x160]
    choices = {field.key: field.choices for field in fields()}
    result: dict[str, object] = {
        "squelch": main[1] if main[1] < 10 else 1,
        "channel_display_mode": _safe_choice(choices["channel_display_mode"], main[9]),
        "battery_save": _safe_choice(choices["battery_save"], main[11], 4),
        "dual_watch": _safe_choice(choices["dual_watch"], main[12], 1),
        "backlight_time": _safe_choice(choices["backlight_time"], main[13], 12),
        "scan_resume_mode": _safe_choice(choices["scan_resume_mode"], actions[5], 14),
        "power_on_display_mode": _safe_choice(choices["power_on_display_mode"], actions[7], 3),
        "battery_type": _safe_choice(choices["battery_type"], actions[0x1C]),
        "backlight_min": min(main[8] >> 4, 10),
        "backlight_max": min(main[8] & 0x0F, 10),
        "contrast": (f4[5] & 0x0F) if (f4[5] & 0x0F) else 10,
        "invert_display": bool(f4[5] & 0x10),
        "meter_style": "CLASSIC" if f4[5] & 0x40 else "TINY",
        "gui_style": bool(f4[5] & 0x80),
        "menu_lock_mode": _safe_choice(choices["menu_lock_mode"], f4[2]),
        "sleep_timer": _safe_choice(choices["sleep_timer"], f4[4] >> 1, 60),
        "beep_control": bool(actions[0] & 0x01),
        "key_lock": bool(main[4] & 0x01),
        "auto_keypad_lock": _safe_choice(choices["auto_keypad_lock"], actions[6]),
        "scan_list_default": _safe_choice(choices["scan_list_default"],
                                            max(0, (scan[0] & 0x7F) - 1)),
        "scan_list_enabled": bool(scan[0] & 0x80),
        "priority_channel_1": _channel_value(scan, 1),
        "priority_channel_2": _channel_value(scan, 3),
        "call_channel": _channel_value(scan, 5),
        "audio_fm": _safe_choice(choices["audio_fm"], main[0] & 0x0F),
        "audio_am": _safe_choice(choices["audio_am"], (main[0] >> 4) & 0x0F),
        "nfm_narrower": bool(main[14] & 0x02),
        "logo_1": _ascii_value(raw[0xC8:0xD8]),
        "logo_2": _ascii_value(raw[0xD8:0xE8]),
        "fm_current": min(max(_u16(raw, 0x20), FM_MIN), FM_MAX),
    }
    if result["backlight_min"] >= result["backlight_max"]:
        result["backlight_min"] = 0
    for index in range(1, 49):
        value = _u16(raw, 0x28 + (index - 1) * 2)
        result["fm_{:02d}".format(index)] = value if FM_MIN <= value <= FM_MAX else 0
    for key, offset in (
            ("key1_shortpress_action", 1), ("key1_longpress_action", 2),
            ("key2_shortpress_action", 3), ("key2_longpress_action", 4)):
        result[key] = _action_value(actions[offset])
    result["keyM_longpress_action"] = _action_value(actions[0] >> 1)
    return result


def _ascii_value(raw: bytes) -> str:
    result = bytearray()
    for value in raw:
        if value in (0, 0xFF) or not 0x20 <= value <= 0x7E:
            break
        result.append(value)
    return result.decode("ascii")


def _channel_value(scan: bytearray, offset: int) -> int:
    raw = _u16(scan, offset)
    return 0 if raw >= 1024 else raw + 1


def _action_value(raw: int) -> str:
    for label, value in ACTION_RAW.items():
        if raw == value:
            return label
    return PRESERVE_DISABLED


def apply_settings(data: bytes, values: dict[str, object]) -> bytes:
    if len(data) != SETTINGS_SIZE:
        raise ValueError("settings block must be exactly 0x170 bytes")
    raw = bytearray(data)
    main = raw[:16]
    actions = raw[0xA8:0xF8]
    scan = raw[0x130:0x138]
    f4 = raw[0x158:0x160]
    choices = {field.key: field.choices for field in fields()}

    def choice(key: str, fallback: int) -> int:
        value = values.get(key)
        if value is None:
            return fallback
        try:
            return choices[key].index(str(value))
        except ValueError as exc:
            raise ValueError("invalid value for {}".format(key)) from exc

    def integer(key: str, minimum: int, maximum: int, fallback: int) -> int:
        value = values.get(key, fallback)
        try:
            value = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid value for {}".format(key)) from exc
        if not minimum <= value <= maximum:
            raise ValueError("{} is outside its allowed range".format(key))
        return value

    main[0] = (choice("audio_fm", main[0] & 0x0F) & 0x0F) | \
              ((choice("audio_am", (main[0] >> 4) & 0x0F) & 0x0F) << 4)
    main[1] = integer("squelch", 0, 9, main[1])
    main[9] = choice("channel_display_mode", main[9])
    main[11] = choice("battery_save", main[11])
    main[12] = choice("dual_watch", main[12])
    main[13] = choice("backlight_time", main[13])
    main[14] = (main[14] & ~0x02) | (int(bool(values.get("nfm_narrower", bool(main[14] & 0x02)))) << 1)
    main[4] = (main[4] & ~0x01) | int(bool(values.get("key_lock", bool(main[4] & 0x01))))
    backlight_min = integer("backlight_min", 0, 10, main[8] >> 4)
    backlight_max = integer("backlight_max", 0, 10, main[8] & 0x0F)
    if backlight_min > backlight_max:
        raise ValueError("backlight_min must not exceed backlight_max")
    main[8] = (backlight_min << 4) | backlight_max

    actions[0] = (actions[0] & 0x01) | (_action_raw(values.get("keyM_longpress_action"), actions[0] >> 1) << 1)
    actions[0] = (actions[0] & ~0x01) | int(bool(values.get("beep_control", bool(actions[0] & 0x01))))
    for key, offset in (
            ("key1_shortpress_action", 1), ("key1_longpress_action", 2),
            ("key2_shortpress_action", 3), ("key2_longpress_action", 4)):
        actions[offset] = _action_raw(values.get(key), actions[offset])
    actions[5] = choice("scan_resume_mode", actions[5])
    actions[6] = choice("auto_keypad_lock", actions[6])
    actions[7] = choice("power_on_display_mode", actions[7])
    actions[0x1C] = choice("battery_type", actions[0x1C])

    scan[0] = (scan[0] & 0x80) | (choice("scan_list_default", max(0, (scan[0] & 0x7F) - 1)) + 1)
    scan[0] = (scan[0] & ~0x80) | (int(bool(values.get("scan_list_enabled", bool(scan[0] & 0x80)))) << 7)
    for key, offset in (("priority_channel_1", 1), ("priority_channel_2", 3), ("call_channel", 5)):
        channel = integer(key, 0, 1024, _channel_value(scan, offset))
        _put_u16(scan, offset, 1024 if channel == 0 else channel - 1)

    contrast = integer("contrast", 1, 15, max(1, f4[5] & 0x0F))
    f4[5] = (f4[5] & 0xF0) | contrast
    for key, mask in (("invert_display", 0x10), ("gui_style", 0x80)):
        if bool(values.get(key, bool(f4[5] & mask))):
            f4[5] |= mask
        else:
            f4[5] &= ~mask
    if str(values.get("meter_style", "CLASSIC" if f4[5] & 0x40 else "TINY")) == "CLASSIC":
        f4[5] |= 0x40
    else:
        f4[5] &= ~0x40
    f4[2] = choice("menu_lock_mode", f4[2])
    f4[4] = (f4[4] & 0x01) | (choice("sleep_timer", min(f4[4] >> 1, 120)) << 1)

    for index in range(2):
        key = "logo_{}".format(index + 1)
        try:
            logo = str(values.get(key, _ascii_value(raw[0xC8 + index * 16:0xD8 + index * 16]))).encode("ascii")
        except UnicodeEncodeError as exc:
            raise ValueError("{} must contain ASCII characters".format(key)) from exc
        if len(logo) > 16:
            raise ValueError("{} is limited to 16 ASCII characters".format(key))
        raw[0xC8 + index * 16:0xD8 + index * 16] = logo.ljust(16, b"\x00")

    current = integer("fm_current", FM_MIN, FM_MAX, _u16(raw, 0x20))
    _put_u16(raw, 0x20, current)
    raw[0x23] = (raw[0x23] & 0xF9) | 0x02
    for index in range(1, 49):
        value = integer("fm_{:02d}".format(index), 0, FM_MAX,
                        _u16(raw, 0x28 + (index - 1) * 2))
        if value and not FM_MIN <= value <= FM_MAX:
            raise ValueError("FM channel must be 76.0-95.0 MHz")
        _put_u16(raw, 0x28 + (index - 1) * 2, 0xFFFF if value == 0 else value)
    raw[:16] = main
    raw[0xA8:0xF8] = actions
    raw[0x130:0x138] = scan
    raw[0x158:0x160] = f4
    return bytes(raw)


def _action_raw(value: object, fallback: int) -> int:
    if value is None or str(value) == PRESERVE_DISABLED:
        return fallback
    try:
        return ACTION_RAW[str(value)]
    except KeyError as exc:
        raise ValueError("unsupported programmable-key action") from exc
