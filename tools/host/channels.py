"""1024-channel list model for the dedicated WRX-JP host tool.

The wire layout follows the K1/K5 V3 CHIRP profile.  This module only edits
the normal channel image (0x0000-0x886F) and the separately allowlisted
Japanese name table; it has no calibration or arbitrary-flash operation.
"""

from __future__ import annotations

import csv
import io
import struct
from dataclasses import dataclass

if __package__ in (None, ""):
    import resources  # type: ignore[no-redef]
else:
    from . import resources


CHANNEL_COUNT = 1024
CHANNEL_RECORD_SIZE = 16
CHANNEL_IMAGE_SIZE = 0x8870
CHANNEL_NAME_BASE = 0x4000
CHANNEL_ATTRIBUTE_BASE = 0x8000
CHANNEL_ATTRIBUTE_SIZE = 2

STEPS = (
    2.5, 5, 6.25, 10, 12.5, 25, 8.33, 0.01, 0.05, 0.1, 0.25, 0.5,
    1, 1.25, 9, 15, 20, 30, 50, 100, 125, 200, 250, 500,
)
CTCSS_TONES = (
    67.0, 69.3, 71.9, 74.4, 77.0, 79.7, 82.5, 85.4, 88.5, 91.5,
    94.8, 97.4, 100.0, 103.5, 107.2, 110.9, 114.8, 118.8, 123.0,
    127.3, 131.8, 136.5, 141.3, 146.2, 151.4, 156.7, 159.8, 162.2,
    165.5, 167.9, 171.3, 173.8, 177.3, 179.9, 183.5, 186.2, 189.9,
    192.8, 196.6, 199.5, 203.5, 206.5, 210.7, 218.1, 225.7, 229.1,
    233.6, 241.8, 250.3, 254.1,
)
DTCS_CODES = (
    23, 25, 26, 31, 32, 36, 43, 47, 51, 53, 54, 65, 71, 72, 73, 74,
    114, 115, 116, 122, 125, 131, 132, 134, 143, 145, 152, 155, 156,
    162, 165, 172, 174, 205, 212, 223, 225, 226, 243, 244, 245, 246,
    251, 252, 255, 261, 263, 265, 266, 271, 274, 306, 311, 315, 325,
    331, 332, 343, 346, 351, 356, 364, 365, 371, 411, 412, 413, 423,
    431, 432, 445, 446, 452, 454, 455, 462, 464, 465, 466, 503, 506,
    516, 523, 526, 532, 546, 565, 606, 612, 624, 627, 631, 632, 654,
    662, 664, 703, 712, 723, 731, 732, 734, 743, 754,
)
MODES = ("FM", "NFM", "AM", "NAM", "USB")
TONE_MODES = ("", "Tone", "TSQL", "DTCS")
FIELDNAMES = (
    "channel", "frequency_hz", "mode", "tone_mode", "tone", "dtcs",
    "dtcs_polarity", "tuning_step_khz", "scan_lists", "name",
)


@dataclass
class Channel:
    channel: int
    frequency_hz: int | None
    mode: str = "FM"
    tone_mode: str = ""
    tone: float | None = None
    dtcs: int | None = None
    dtcs_polarity: str = "N"
    tuning_step_khz: float = 12.5
    scan_lists: int = 0
    name: str = ""

    @property
    def empty(self) -> bool:
        return self.frequency_hz is None


def _decode_fixed_text(data: bytes, encoding: str) -> str:
    payload = data.split(b"\x00", 1)[0].split(b"\xFF", 1)[0]
    try:
        return payload.decode(encoding)
    except UnicodeDecodeError:
        return ""


def _decode_external_name(name_table: bytes, index: int) -> str:
    start = index * resources.JAPANESE_NAME_RECORD_SIZE
    end = start + resources.JAPANESE_NAME_RECORD_SIZE
    return _decode_fixed_text(name_table[start:end], "utf-8")


def _decode_mode(raw: bytes) -> str:
    mode_index = ((raw[11] >> 4) & 0x0F) * 2 + ((raw[12] >> 1) & 1)
    return MODES[mode_index] if mode_index < len(MODES) else "FM"


def _decode_tone(raw: bytes) -> tuple[str, float | None, int | None, str]:
    flag = raw[10] & 0x0F
    code = raw[8]
    if flag == 1 and code < len(CTCSS_TONES):
        return "Tone", CTCSS_TONES[code], None, "N"
    if flag in (2, 3) and code < len(DTCS_CODES):
        return "DTCS", None, DTCS_CODES[code], "R" if flag == 3 else "N"
    return "", None, None, "N"


def decode_channel_list(image: bytes, name_table: bytes) -> list[Channel]:
    """Decode the normal K1 channel image and its 1024 external names."""
    if len(image) != CHANNEL_IMAGE_SIZE:
        raise ValueError("channel image must be exactly 0x8870 bytes")
    if len(name_table) != resources.JAPANESE_NAME_SIZE:
        raise ValueError("Japanese name table must contain 1024 records")

    result: list[Channel] = []
    for index in range(CHANNEL_COUNT):
        offset = index * CHANNEL_RECORD_SIZE
        raw = image[offset:offset + CHANNEL_RECORD_SIZE]
        stored_frequency = struct.unpack_from("<I", raw, 0)[0]
        frequency = (None if stored_frequency in (0, 0xFFFFFFFF)
                     else stored_frequency * 10)
        tone_mode, tone, dtcs, polarity = _decode_tone(raw)
        attr_offset = CHANNEL_ATTRIBUTE_BASE + index * CHANNEL_ATTRIBUTE_SIZE
        scan_lists = struct.unpack_from("<H", image, attr_offset)[0] >> 8
        name = _decode_external_name(name_table, index)
        if not name:
            name = _decode_fixed_text(
                image[CHANNEL_NAME_BASE + index * 16:
                      CHANNEL_NAME_BASE + (index + 1) * 16], "ascii")
        if frequency is None:
            name = ""
        step_index = raw[14]
        step = STEPS[step_index] if step_index < len(STEPS) else 12.5
        result.append(Channel(
            channel=index + 1,
            frequency_hz=frequency,
            mode=_decode_mode(raw),
            tone_mode=tone_mode,
            tone=tone,
            dtcs=dtcs,
            dtcs_polarity=polarity,
            tuning_step_khz=step,
            scan_lists=scan_lists,
            name=name,
        ))
    return result


def _parse_optional_int(value: str, label: str) -> int | None:
    value = value.strip()
    if not value:
        return None
    try:
        return int(value, 10)
    except ValueError as exc:
        raise ValueError("{} must be an integer".format(label)) from exc


def _parse_optional_float(value: str, label: str) -> float | None:
    value = value.strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError("{} must be a number".format(label)) from exc


def _parse_row(row: dict[str, str], expected_channel: int) -> Channel:
    try:
        channel = int(row["channel"], 10)
    except (KeyError, ValueError) as exc:
        raise ValueError("channel must be an integer") from exc
    if channel != expected_channel:
        raise ValueError("channel rows must be numbered 1..1024 in order")

    frequency = _parse_optional_int(row.get("frequency_hz", ""), "frequency_hz")
    mode = row.get("mode", "FM").strip().upper() or "FM"
    tone_mode = row.get("tone_mode", "").strip()
    if mode not in MODES:
        raise ValueError("channel {} has an unsupported mode".format(channel))
    if tone_mode not in TONE_MODES:
        raise ValueError("channel {} has an unsupported tone_mode".format(channel))

    tone = _parse_optional_float(row.get("tone", ""), "tone")
    dtcs = _parse_optional_int(row.get("dtcs", ""), "dtcs")
    polarity = row.get("dtcs_polarity", "N").strip().upper() or "N"
    if polarity not in ("N", "R"):
        raise ValueError("channel {} has an invalid dtcs_polarity".format(channel))
    step = _parse_optional_float(row.get("tuning_step_khz", "12.5"),
                                 "tuning_step_khz")
    if step is None:
        step = 12.5
    if not any(abs(step - candidate) < 1e-6 for candidate in STEPS):
        raise ValueError("channel {} has an unsupported tuning step".format(channel))
    scan_lists = int(row.get("scan_lists", "0") or "0", 10)
    if not 0 <= scan_lists <= 0xFF:
        raise ValueError("channel {} scan_lists must be 0..255".format(channel))
    name = row.get("name", "")
    if "\t" in name or "\r" in name or "\n" in name:
        raise ValueError("channel {} name contains a tab or newline".format(channel))
    return Channel(channel, frequency, mode, tone_mode, tone, dtcs, polarity,
                   step, scan_lists, name)


def parse_channel_list(text: str) -> list[Channel]:
    """Parse the editable UTF-8 TSV representation."""
    lines = [line for line in text.splitlines()
             if line.strip() and not line.lstrip().startswith("#")]
    if not lines:
        raise ValueError("channel list is empty")
    reader = csv.DictReader(lines, delimiter="\t")
    if tuple(reader.fieldnames or ()) != FIELDNAMES:
        raise ValueError("channel list header does not match WRX-JP v1")
    rows = list(reader)
    if len(rows) != CHANNEL_COUNT:
        raise ValueError("channel list must contain exactly 1024 rows")
    return [_parse_row(row, index) for index, row in enumerate(rows, 1)]


def format_channel_list(channels: list[Channel]) -> str:
    if len(channels) != CHANNEL_COUNT:
        raise ValueError("channel list must contain exactly 1024 rows")
    output = io.StringIO(newline="")
    output.write("# WRX-JP channel list v1\n")
    writer = csv.DictWriter(output, fieldnames=FIELDNAMES, delimiter="\t",
                            lineterminator="\n", extrasaction="raise")
    writer.writeheader()
    for channel in channels:
        writer.writerow({
            "channel": channel.channel,
            "frequency_hz": "" if channel.frequency_hz is None else channel.frequency_hz,
            "mode": channel.mode,
            "tone_mode": channel.tone_mode,
            "tone": "" if channel.tone is None else "{:.1f}".format(channel.tone),
            "dtcs": "" if channel.dtcs is None else channel.dtcs,
            "dtcs_polarity": channel.dtcs_polarity,
            "tuning_step_khz": "{:g}".format(channel.tuning_step_khz),
            "scan_lists": channel.scan_lists,
            "name": channel.name,
        })
    return output.getvalue()


def _encode_tone(channel: Channel, raw: bytearray) -> None:
    flag = 0
    code = 0
    if channel.tone_mode in ("Tone", "TSQL"):
        if channel.tone is None:
            raise ValueError("channel {} tone is required".format(channel.channel))
        matches = [index for index, value in enumerate(CTCSS_TONES)
                   if abs(value - channel.tone) < 1e-6]
        if not matches:
            raise ValueError("channel {} has an unsupported CTCSS tone".format(channel.channel))
        code, flag = matches[0], 1
    elif channel.tone_mode == "DTCS":
        if channel.dtcs not in DTCS_CODES:
            raise ValueError("channel {} has an unsupported DTCS code".format(channel.channel))
        code = DTCS_CODES.index(channel.dtcs)
        flag = 3 if channel.dtcs_polarity == "R" else 2
    raw[8] = code
    raw[9] = 0
    raw[10] = (raw[10] & 0xF0) | flag


def encode_channel_list(channels: list[Channel], image: bytes,
                        name_table: bytes) -> tuple[bytes, bytes]:
    """Apply edited rows while preserving unknown bytes in the image."""
    if len(channels) != CHANNEL_COUNT:
        raise ValueError("channel list must contain exactly 1024 rows")
    if len(image) != CHANNEL_IMAGE_SIZE:
        raise ValueError("channel image must be exactly 0x8870 bytes")
    if len(name_table) != resources.JAPANESE_NAME_SIZE:
        raise ValueError("Japanese name table must contain 1024 records")

    updated = bytearray(image)
    updated_names = bytearray(name_table)
    codepoints = resources.japanese_codepoints()
    for index, channel in enumerate(channels):
        if channel.channel != index + 1:
            raise ValueError("channel rows must be numbered 1..1024 in order")
        record_offset = index * CHANNEL_RECORD_SIZE
        name_offset = CHANNEL_NAME_BASE + index * 16
        external_offset = index * resources.JAPANESE_NAME_RECORD_SIZE
        if channel.empty:
            updated[record_offset:record_offset + 16] = b"\xFF" * 16
            updated[name_offset:name_offset + 16] = b"\x00" * 16
            updated_names[external_offset:external_offset + 32] = b"\x00" * 32
            continue

        if channel.frequency_hz is None or channel.frequency_hz <= 0:
            raise ValueError("channel {} frequency must be positive".format(channel.channel))
        if channel.frequency_hz % 10:
            raise ValueError("channel {} frequency must be a 10 Hz multiple".format(channel.channel))
        stored_frequency = channel.frequency_hz // 10
        if stored_frequency > 0xFFFFFFFF:
            raise ValueError("channel {} frequency is too large".format(channel.channel))
        raw = bytearray(updated[record_offset:record_offset + 16])
        struct.pack_into("<I", raw, 0, stored_frequency)
        # RX-only invariant: never retain a transmit frequency or tone.
        raw[4:8] = b"\x00" * 4
        mode_index = {"FM": 0, "NFM": 1, "AM": 2, "NAM": 3, "USB": 5}[channel.mode]
        raw[11] = (raw[11] & 0x0F) | ((mode_index // 2) << 4)
        raw[12] = (raw[12] & 0xFD) | ((mode_index & 1) << 1) | 0x40
        _encode_tone(channel, raw)
        raw[14] = min(range(len(STEPS)),
                      key=lambda step_index: abs(STEPS[step_index] - channel.tuning_step_khz))
        updated[record_offset:record_offset + 16] = raw

        encoded_name = resources.validate_name(channel.name, codepoints)
        if any(ord(character) > 0x7E for character in channel.name):
            updated[name_offset:name_offset + 16] = b"\x00" * 16
            updated_names[external_offset:external_offset + 32] = \
                encoded_name.ljust(32, b"\x00")
        else:
            if len(encoded_name) > 10:
                raise ValueError("channel {} ASCII name exceeds 10 bytes".format(channel.channel))
            updated[name_offset:name_offset + 16] = encoded_name.ljust(16, b"\x00")
            updated_names[external_offset:external_offset + 32] = b"\x00" * 32

        attr_offset = CHANNEL_ATTRIBUTE_BASE + index * CHANNEL_ATTRIBUTE_SIZE
        attr = struct.unpack_from("<H", updated, attr_offset)[0]
        struct.pack_into("<H", updated, attr_offset,
                         (attr & 0x00FF) | (channel.scan_lists << 8))
    return bytes(updated), bytes(updated_names)
