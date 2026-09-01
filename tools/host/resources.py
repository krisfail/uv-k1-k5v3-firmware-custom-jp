"""Fixed Japanese font and 1024-name resource validation."""

from __future__ import annotations

import json
from pathlib import Path

try:
    from .protocol import (
        JAPANESE_FONT_BASE,
        JAPANESE_FONT_SIZE,
        JAPANESE_NAME_BASE,
        JAPANESE_NAME_COUNT,
        JAPANESE_NAME_RECORD_SIZE,
        JAPANESE_NAME_SIZE,
    )
except ImportError:  # Running wrx_jp_host.py directly from this directory.
    from protocol import (  # type: ignore[no-redef]
        JAPANESE_FONT_BASE,
        JAPANESE_FONT_SIZE,
        JAPANESE_NAME_BASE,
        JAPANESE_NAME_COUNT,
        JAPANESE_NAME_RECORD_SIZE,
        JAPANESE_NAME_SIZE,
    )


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "tools" / "japanese_font_manifest.json"
FONT_PATH = ROOT / "docs" / "fonts" / "japanese_font.bin"


def load_manifest() -> dict:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    expected = {
        "flash_base": JAPANESE_FONT_BASE,
        "total_bytes": JAPANESE_FONT_SIZE,
        "name_table_base": JAPANESE_NAME_BASE,
        "name_record_size": JAPANESE_NAME_RECORD_SIZE,
        "name_payload_max": JAPANESE_NAME_RECORD_SIZE - 1,
    }
    for key, value in expected.items():
        if int(manifest.get(key, -1)) != value:
            raise ValueError("font manifest does not match the fixed firmware contract")
    return manifest


def load_font() -> bytes:
    load_manifest()
    data = FONT_PATH.read_bytes()
    if len(data) != JAPANESE_FONT_SIZE:
        raise ValueError("bundled Japanese font has an unexpected size")
    return data


def japanese_codepoints() -> frozenset[int]:
    return frozenset(int(value) for value in load_manifest().get("codepoints", []))


def validate_name(name: str, codepoints: frozenset[int] | None = None) -> bytes:
    if codepoints is None:
        codepoints = japanese_codepoints()
    try:
        encoded = name.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("channel name is not valid UTF-8") from exc
    if len(encoded) > JAPANESE_NAME_RECORD_SIZE - 1:
        raise ValueError("channel name exceeds 31 UTF-8 bytes")

    pixel_width = 0
    for character in name:
        codepoint = ord(character)
        if codepoint < 0x20 or codepoint > 0x7E:
            if codepoint not in codepoints:
                raise ValueError(
                    "channel name character U+{:04X} is not in the font".format(
                        codepoint))
            pixel_width += 16
        else:
            pixel_width += 8
    if pixel_width > 95:
        raise ValueError("channel name exceeds the LCD display width")
    return encoded


def pack_name_table(lines: list[str]) -> bytes:
    if len(lines) != JAPANESE_NAME_COUNT:
        raise ValueError("the Japanese resource requires exactly 1024 lines")
    codepoints = japanese_codepoints()
    table = bytearray()
    for number, line in enumerate(lines, 1):
        if "\r" in line or "\n" in line:
            raise ValueError("channel {} contains a newline".format(number))
        encoded = validate_name(line, codepoints)
        table.extend(encoded)
        table.extend(b"\x00" * (JAPANESE_NAME_RECORD_SIZE - len(encoded)))
    return bytes(table)


def read_name_file(path: Path) -> bytes:
    # newline="" preserves the contract and lets pack_name_table reject
    # embedded line endings instead of silently changing names.
    with path.open("r", encoding="utf-8", newline="") as stream:
        text = stream.read()
    return pack_name_table(text.splitlines())


def unpack_name_table(data: bytes) -> list[str]:
    if len(data) != JAPANESE_NAME_SIZE:
        raise ValueError("Japanese name table has an unexpected size")
    names: list[str] = []
    for index in range(JAPANESE_NAME_COUNT):
        record = data[index * JAPANESE_NAME_RECORD_SIZE:
                      (index + 1) * JAPANESE_NAME_RECORD_SIZE]
        payload = record.split(b"\x00", 1)[0].split(b"\xFF", 1)[0]
        try:
            names.append(payload.decode("utf-8"))
        except UnicodeDecodeError as exc:
            raise ValueError("name record {} is not valid UTF-8".format(index + 1)) from exc
    return names
