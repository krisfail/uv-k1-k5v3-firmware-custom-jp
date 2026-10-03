#!/usr/bin/env python3
"""Generate the fixed external Japanese bitmap-font image for K1/K5 V3.

The input is Izumi 16's JIS X 0213 Plane 1 BDF.  Only JIS rows 1--47
(non-kanji plus JIS X 0208 first-level kanji) are selected.  ASCII remains
the firmware's existing compatibility font and is therefore not duplicated
in this external image.

The binary format is deliberately fixed and small:

    [sorted Unicode index: uint16 codepoint, uint16 glyph index]
    [16x16 glyphs: 16 rows x uint16, little-endian per row]
    [14x14 glyphs: 14 rows x uint16, little-endian per row]
    [8x8 Japanese glyphs: 8 rows x uint8, MSB-left]

The firmware and host tool use the generated layout header/manifest.  There
is no runtime font negotiation or variable-width record format.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import struct
from pathlib import Path


FONT_BASE = 0x020000
NAME_BASE = 0x060000
NAME_RECORD_SIZE = 32
NAME_PAYLOAD_MAX = NAME_RECORD_SIZE - 1
SOURCE_SHA256 = "005345196615E692C54EF67286B44DD0EAA3A899D066CD407A4B3A810822C20C"
SOURCE_URL = "https://unifoundry.com/japanese/izmg16-2004-1.bdf.gz"
EXPECTED_FONT_BOUNDING_BOX = (16, 16, 0, -2)
SOURCE14_SHA256 = "926AE3E16560F1719C34217E5A9FFAFC81DF18ED1732A5302313DA8359294226"
SOURCE14_NAME = "WenQuanYi Bitmap Song 10.5pt"
SOURCE14_REPOSITORY = "https://github.com/EthanYan6/Dondji"
EXPECTED_FONT14_BOUNDING_BOX = (14, 15, 0, -3)
SOURCE8_SHA256 = "28A8745552C844F7C73F11BDF4470225F5E08645A98C5404B2E25BB326A5CABD"
SOURCE8_NAME = "Misaki Gothic 8dot"
SOURCE8_URL = "https://littlelimit.net/misaki.htm"
EXPECTED_FONT8_BOUNDING_BOX = (8, 8, 0, -2)
EXPECTED_FONT8_ASCENT = 6
RESAMPLE14_THRESHOLD = 21
RESAMPLE14 = (
    ((0, 7), (1, 1)), ((1, 6), (2, 2)), ((2, 5), (3, 3)),
    ((3, 4), (4, 4)), ((4, 3), (5, 5)), ((5, 2), (6, 6)),
    ((6, 1), (7, 7)), ((8, 7), (9, 1)), ((9, 6), (10, 2)),
    ((10, 5), (11, 3)), ((11, 4), (12, 4)), ((12, 3), (13, 5)),
    ((13, 2), (14, 6)), ((14, 1), (15, 7)),
)


def open_bdf(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="ascii")
    return path.open("r", encoding="ascii")


def verify_source(path: Path) -> None:
    actual = hashlib.sha256(path.read_bytes()).hexdigest().upper()
    if actual != SOURCE_SHA256:
        raise ValueError(
            "unexpected source SHA-256: {} (expected {})".format(
                actual, SOURCE_SHA256))


def verify_source14(path: Path) -> None:
    actual = hashlib.sha256(path.read_bytes()).hexdigest().upper()
    if actual != SOURCE14_SHA256:
        raise ValueError(
            "unexpected 14px source SHA-256: {} (expected {})".format(
                actual, SOURCE14_SHA256))


def verify_source8(path: Path) -> None:
    actual = hashlib.sha256(path.read_bytes()).hexdigest().upper()
    if actual != SOURCE8_SHA256:
        raise ValueError(
            "unexpected 8px source SHA-256: {} (expected {})".format(
                actual, SOURCE8_SHA256))


def jis_codepoint(character: str) -> int:
    encoded = character.encode("iso2022_jp")
    if not (encoded.startswith(b"\x1b$B") and encoded.endswith(b"\x1b(B")):
        raise ValueError(f"not a single JIS X 0208 character: {character!r}")
    return int.from_bytes(encoded[3:-3], "big")


def target_characters() -> list[str]:
    """Return JIS rows 0x21..0x4f in stable JIS order, without duplicates."""

    result: list[str] = []
    seen: set[str] = set()
    for row in range(0x21, 0x50):
        for cell in range(0x21, 0x7F):
            try:
                character = bytes((row + 0x80, cell + 0x80)).decode("euc_jp")
            except UnicodeDecodeError:
                continue
            if len(character) != 1 or character in seen:
                continue
            seen.add(character)
            result.append(character)
    return result


def parse_bdf(path: Path, wanted_codes: set[int]) -> dict[int, list[int]]:
    """Read 16x16 glyph rows keyed by JIS row-cell encoding."""

    with open_bdf(path) as source:
        lines = source.read().splitlines()
    bounding_box_line = next(
        (line for line in lines if line.startswith("FONTBOUNDINGBOX ")), None)
    if bounding_box_line is None:
        raise ValueError("BDF is missing FONTBOUNDINGBOX")
    bounding_box = tuple(int(value) for value in bounding_box_line.split()[1:])
    if bounding_box != EXPECTED_FONT_BOUNDING_BOX:
        raise ValueError(
            "unexpected BDF FONTBOUNDINGBOX: {} (expected {})".format(
                bounding_box, EXPECTED_FONT_BOUNDING_BOX))

    glyphs: dict[int, list[int]] = {}
    index = 0
    while index < len(lines):
        if not lines[index].startswith("STARTCHAR "):
            index += 1
            continue

        end = index + 1
        while end < len(lines) and lines[end] != "ENDCHAR":
            end += 1
        block = lines[index:end]
        encoding_line = next((line for line in block if line.startswith("ENCODING ")), None)
        if encoding_line is None:
            index = end + 1
            continue
        code = int(encoding_line.split()[1])
        if code not in wanted_codes:
            index = end + 1
            continue

        bbx_line = next((line for line in block if line.startswith("BBX ")), None)
        bitmap_index = next((i for i, line in enumerate(block) if line == "BITMAP"), None)
        if bbx_line is None or bitmap_index is None:
            raise ValueError(f"missing BBX/BITMAP for JIS code 0x{code:04X}")
        bbx = tuple(int(value) for value in bbx_line.split()[1:])
        rows = block[bitmap_index + 1 : bitmap_index + 17]
        if (bbx != EXPECTED_FONT_BOUNDING_BOX or len(rows) != 16 or
                any(len(row) != 4 for row in rows)):
            raise ValueError(
                f"JIS code 0x{code:04X} does not use the expected 16x16 baseline")
        glyphs[code] = [int(row, 16) for row in rows]
        index = end + 1
    return glyphs


def parse_bdf14(path: Path, wanted_codepoints: set[int]) -> dict[int, list[int]]:
    """Read a native 14px BDF into fixed 14-row, 14-column cells.

    BDF glyphs have individual bounding boxes and a shared baseline.  The
    WenQuanYi source uses a 14px advance and normally leaves one bottom row
    in the cell; the conversion preserves that baseline instead of scaling
    the resulting bitmap at run time.
    """

    with path.open("r", encoding="ascii") as source:
        lines = source.read().splitlines()
    bounding_box_line = next(
        (line for line in lines if line.startswith("FONTBOUNDINGBOX ")), None)
    if bounding_box_line is None:
        raise ValueError("14px BDF is missing FONTBOUNDINGBOX")
    bounding_box = tuple(int(value) for value in bounding_box_line.split()[1:])
    if bounding_box != EXPECTED_FONT14_BOUNDING_BOX:
        raise ValueError(
            "unexpected 14px BDF FONTBOUNDINGBOX: {} (expected {})".format(
                bounding_box, EXPECTED_FONT14_BOUNDING_BOX))

    glyphs: dict[int, list[int]] = {}
    index = 0
    while index < len(lines):
        if not lines[index].startswith("STARTCHAR "):
            index += 1
            continue

        end = index + 1
        while end < len(lines) and lines[end] != "ENDCHAR":
            end += 1
        block = lines[index:end]
        encoding_line = next(
            (line for line in block if line.startswith("ENCODING ")), None)
        if encoding_line is None:
            index = end + 1
            continue
        codepoint = int(encoding_line.split()[1])
        if codepoint not in wanted_codepoints:
            index = end + 1
            continue

        bbx_line = next((line for line in block if line.startswith("BBX ")), None)
        dwidth_line = next(
            (line for line in block if line.startswith("DWIDTH ")), None)
        bitmap_index = next(
            (i for i, line in enumerate(block) if line == "BITMAP"), None)
        if bbx_line is None or dwidth_line is None or bitmap_index is None:
            raise ValueError(
                "missing BBX/DWIDTH/BITMAP for U+{:04X}".format(codepoint))

        width, height, x_offset, y_offset = (
            int(value) for value in bbx_line.split()[1:])
        dwidth = int(dwidth_line.split()[1])
        if (width < 0 or height < 0 or width > 14 or height > 14 or
                x_offset < 0 or x_offset + width > 14 or dwidth > 14):
            index = end + 1
            continue

        rows = block[bitmap_index + 1:bitmap_index + 1 + height]
        if len(rows) != height or any(not row or len(row) > 4 for row in rows):
            raise ValueError("invalid bitmap rows for U+{:04X}".format(codepoint))

        # Align the common (13px, -1) glyph to rows 0..12.  Other glyphs
        # retain their BDF baseline relative to that common top edge.
        top = 12 - y_offset - height
        if top < 0 or top + height > 14:
            index = end + 1
            continue

        row_bytes = (width + 7) // 8
        bitmap = [0] * 14
        for source_row, text in enumerate(rows):
            value = int(text, 16)
            for source_column in range(width):
                if value & (1 << (row_bytes * 8 - 1 - source_column)):
                    destination_column = x_offset + source_column
                    bitmap[top + source_row] |= 0x8000 >> destination_column
        glyphs[codepoint] = bitmap
        index = end + 1
    return glyphs


def parse_bdf8(path: Path, wanted_codepoints: set[int]) -> dict[int, list[int]]:
    """Read native 8px BDF glyphs into row-packed 8-byte cells."""

    with path.open("r", encoding="ascii") as source:
        lines = source.read().splitlines()
    bounding_box_line = next(
        (line for line in lines if line.startswith("FONTBOUNDINGBOX ")), None)
    if bounding_box_line is None:
        raise ValueError("8px BDF is missing FONTBOUNDINGBOX")
    bounding_box = tuple(int(value) for value in bounding_box_line.split()[1:])
    if bounding_box != EXPECTED_FONT8_BOUNDING_BOX:
        raise ValueError(
            "unexpected 8px BDF FONTBOUNDINGBOX: {} (expected {})".format(
                bounding_box, EXPECTED_FONT8_BOUNDING_BOX))

    ascent_line = next(
        (line for line in lines if line.startswith("FONT_ASCENT ")), None)
    if ascent_line is None or int(ascent_line.split()[1]) != EXPECTED_FONT8_ASCENT:
        raise ValueError("unexpected 8px BDF FONT_ASCENT")

    glyphs: dict[int, list[int]] = {}
    index = 0
    while index < len(lines):
        if not lines[index].startswith("STARTCHAR "):
            index += 1
            continue

        end = index + 1
        while end < len(lines) and lines[end] != "ENDCHAR":
            end += 1
        block = lines[index:end]
        encoding_line = next(
            (line for line in block if line.startswith("ENCODING ")), None)
        if encoding_line is None:
            index = end + 1
            continue
        codepoint = int(encoding_line.split()[1])
        if codepoint not in wanted_codepoints:
            index = end + 1
            continue

        bbx_line = next((line for line in block if line.startswith("BBX ")), None)
        dwidth_line = next(
            (line for line in block if line.startswith("DWIDTH ")), None)
        bitmap_index = next(
            (i for i, line in enumerate(block) if line == "BITMAP"), None)
        if bbx_line is None or dwidth_line is None or bitmap_index is None:
            raise ValueError(
                "missing BBX/DWIDTH/BITMAP for U+{:04X}".format(codepoint))

        width, height, x_offset, y_offset = (
            int(value) for value in bbx_line.split()[1:])
        dwidth = int(dwidth_line.split()[1])
        if (width < 0 or height < 0 or width > 8 or height > 8 or
                x_offset < 0 or x_offset + width > 8 or
                dwidth < 0 or dwidth > 8):
            index = end + 1
            continue

        rows = block[bitmap_index + 1:bitmap_index + 1 + height]
        if len(rows) != height or any(not row or len(row) > 2 for row in rows):
            raise ValueError("invalid bitmap rows for U+{:04X}".format(codepoint))

        top = EXPECTED_FONT8_ASCENT - y_offset - height
        if top < 0 or top + height > 8:
            index = end + 1
            continue

        row_bytes = (width + 7) // 8
        cell_offset = max(0, (8 - dwidth) // 2)
        bitmap = [0] * 8
        for source_row, text in enumerate(rows):
            value = int(text, 16)
            for source_column in range(width):
                if value & (1 << (row_bytes * 8 - 1 - source_column)):
                    bitmap[top + source_row] |= 0x80 >> (
                        cell_offset + x_offset + source_column)
        glyphs[codepoint] = bitmap
        index = end + 1
    return glyphs


def resample_glyph14(glyph: list[int]) -> list[int]:
    """Create a build-time fallback for symbols absent from the 14px BDF."""

    result = [0] * 14
    for row, row_span in enumerate(RESAMPLE14):
        for column, column_span in enumerate(RESAMPLE14):
            coverage = 0
            for source_row, row_weight in row_span:
                for source_column, column_weight in column_span:
                    if glyph[source_row] & (0x8000 >> source_column):
                        coverage += row_weight * column_weight
            if coverage >= RESAMPLE14_THRESHOLD:
                result[row] |= 0x8000 >> column
    return result


def write_layout_header(path: Path, glyph_count: int) -> None:
    index_bytes = glyph_count * 4
    bitmap_bytes = glyph_count * 32
    bitmap14_offset = index_bytes + bitmap_bytes
    bitmap14_bytes = glyph_count * 28
    bitmap8_offset = bitmap14_offset + bitmap14_bytes
    bitmap8_bytes = glyph_count * 8
    total_bytes = bitmap8_offset + bitmap8_bytes
    text = f"""/* Generated by tools/generate_japanese_font.py. */
#ifndef APP_JAPANESE_FONT_EXTERNAL_H
#define APP_JAPANESE_FONT_EXTERNAL_H

#define JAPANESE_FONT_FLASH_BASE       0x{FONT_BASE:06X}u
#define JAPANESE_FONT_INDEX_OFFSET     0u
#define JAPANESE_FONT_BITMAP_OFFSET    0x{index_bytes:06X}u
#define JAPANESE_FONT_GLYPH_COUNT      {glyph_count}u
#define JAPANESE_FONT_GLYPH_BYTES      32u
#define JAPANESE_FONT_GLYPH14_BYTES    28u
#define JAPANESE_FONT_GLYPH8_BYTES     8u
#define JAPANESE_FONT_INDEX_BYTES      {index_bytes}u
#define JAPANESE_FONT_BITMAP_BYTES     {bitmap_bytes}u
#define JAPANESE_FONT_BITMAP14_OFFSET  0x{bitmap14_offset:06X}u
#define JAPANESE_FONT_BITMAP14_BYTES   {bitmap14_bytes}u
#define JAPANESE_FONT_BITMAP8_OFFSET   0x{bitmap8_offset:06X}u
#define JAPANESE_FONT_BITMAP8_BYTES    {bitmap8_bytes}u
#define JAPANESE_FONT_TOTAL_BYTES      {total_bytes}u

#define JAPANESE_NAME_TABLE_BASE       0x{NAME_BASE:06X}u
#define JAPANESE_NAME_RECORD_SIZE      {NAME_RECORD_SIZE}u
#define JAPANESE_NAME_PAYLOAD_MAX      {NAME_PAYLOAD_MAX}u
#define JAPANESE_NAME_TABLE_SIZE       (1024u * JAPANESE_NAME_RECORD_SIZE)

#endif /* APP_JAPANESE_FONT_EXTERNAL_H */
"""
    path.write_text(text, encoding="utf-8", newline="\n")


def generate(args: argparse.Namespace) -> None:
    verify_source(args.bdf)
    characters = target_characters()
    code_by_character = {character: jis_codepoint(character) for character in characters}
    wanted_codes = set(code_by_character.values())
    glyphs = parse_bdf(args.bdf, wanted_codes)
    missing = [character for character in characters if code_by_character[character] not in glyphs]
    if missing:
        preview = " ".join(f"U+{ord(character):04X}" for character in missing[:20])
        raise ValueError(f"missing {len(missing)} target glyphs: {preview}")

    glyphs14_native: dict[int, list[int]] = {}
    if args.bdf14 is not None:
        verify_source14(args.bdf14)
        glyphs14_native = parse_bdf14(args.bdf14, set(ord(c) for c in characters))

    if args.bdf8 is None:
        raise ValueError("a canonical native 8px BDF is required")
    verify_source8(args.bdf8)
    glyphs8_native = parse_bdf8(args.bdf8, set(ord(c) for c in characters))
    missing8 = [character for character in characters
                if ord(character) not in glyphs8_native]
    if missing8:
        preview = " ".join(f"U+{ord(character):04X}" for character in missing8[:20])
        raise ValueError(f"missing {len(missing8)} native 8px glyphs: {preview}")

    entries = sorted((ord(character), code_by_character[character]) for character in characters)
    # Keep glyph order stable in JIS order while the index is Unicode-sorted.
    glyph_index = {code: index for index, (_character, code) in enumerate(
        (character, code_by_character[character]) for character in characters
    )}

    index_bytes = bytearray()
    bitmap_bytes = bytearray()
    bitmap14_bytes = bytearray()
    bitmap8_bytes = bytearray()
    native14_count = 0
    for unicode_codepoint, jis_code in entries:
        index_bytes.extend(struct.pack("<HH", unicode_codepoint, glyph_index[jis_code]))
    for character in characters:
        for row in glyphs[code_by_character[character]]:
            bitmap_bytes.extend(struct.pack("<H", row))
        codepoint = ord(character)
        glyph14 = glyphs14_native.get(codepoint)
        if glyph14 is not None:
            native14_count += 1
        else:
            glyph14 = resample_glyph14(glyphs[code_by_character[character]])
        for row in glyph14:
            bitmap14_bytes.extend(struct.pack("<H", row))
        for row in glyphs8_native[codepoint]:
            bitmap8_bytes.append(row)

    args.out_bin.parent.mkdir(parents=True, exist_ok=True)
    args.out_bin.write_bytes(index_bytes + bitmap_bytes + bitmap14_bytes + bitmap8_bytes)
    args.out_header.parent.mkdir(parents=True, exist_ok=True)
    write_layout_header(args.out_header, len(characters))

    manifest = {
        "format": "wrx-jp-external-font-v2",
        "source": {
            "name": "Izumi Gothic-Medium 16dot",
            "url": SOURCE_URL,
            "sha256": SOURCE_SHA256,
            "license": "Public Domain (as stated in the source BDF)",
        },
        "geometry": {"width": 16, "height": 16, "row_bytes": 2},
        "geometry14": {"width": 14, "height": 14, "row_bytes": 2},
        "geometry8": {"width": 8, "height": 8, "row_bytes": 1},
        "glyph_count": len(characters),
        "index_bytes": len(index_bytes),
        "bitmap_bytes": len(bitmap_bytes),
        "bitmap14_offset": len(index_bytes) + len(bitmap_bytes),
        "bitmap14_bytes": len(bitmap14_bytes),
        "glyph14_bytes": 28,
        "bitmap8_offset": len(index_bytes) + len(bitmap_bytes) + len(bitmap14_bytes),
        "bitmap8_bytes": len(bitmap8_bytes),
        "glyph8_bytes": 8,
        "native8_glyph_count": len(glyphs8_native),
        "native14_glyph_count": native14_count,
        "fallback14_glyph_count": len(characters) - native14_count,
        "total_bytes": (len(index_bytes) + len(bitmap_bytes) +
                        len(bitmap14_bytes) + len(bitmap8_bytes)),
        "flash_base": FONT_BASE,
        "name_table_base": NAME_BASE,
        "name_record_size": NAME_RECORD_SIZE,
        "name_payload_max": NAME_PAYLOAD_MAX,
        "ascii_fallback": "firmware-legacy-gFontBig",
        "small_source": {
            "name": SOURCE14_NAME,
            "repository": SOURCE14_REPOSITORY,
            "sha256": SOURCE14_SHA256,
            "license": "GPL v2 with font embedding exception (as stated in the source BDF)",
            "native_glyphs": native14_count,
            "fallback": "Izumi 16 build-time area-average for source gaps",
        },
        "compact_source": {
            "name": SOURCE8_NAME,
            "copyright": "Copyright (C) 2002-2021 Num Kadoma",
            "url": SOURCE8_URL,
            "sha256": SOURCE8_SHA256,
            "license": "Free software; unlimited permission as stated by the source",
            "native_glyphs": len(glyphs8_native),
        },
        "codepoints": [unicode_codepoint for unicode_codepoint, _ in entries],
    }
    args.out_manifest.parent.mkdir(parents=True, exist_ok=True)
    args.out_manifest.write_text(
        json.dumps(manifest, ensure_ascii=True, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"glyphs: {len(characters)}")
    print(f"index: {len(index_bytes)} bytes")
    print(f"bitmap: {len(bitmap_bytes)} bytes")
    print(f"bitmap14: {len(bitmap14_bytes)} bytes ({native14_count} native)")
    print(f"bitmap8: {len(bitmap8_bytes)} bytes ({len(glyphs8_native)} native)")
    print(f"total: {len(index_bytes) + len(bitmap_bytes) + len(bitmap14_bytes) + len(bitmap8_bytes)} bytes")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bdf", type=Path)
    parser.add_argument(
        "--bdf14", type=Path,
        help="native 14px BDF; missing symbols use a build-time Izumi fallback")
    parser.add_argument(
        "--bdf8", type=Path,
        required=True,
        help="canonical native 8px BDF; all target symbols must be present")
    parser.add_argument("--out-bin", type=Path, default=Path("docs/fonts/japanese_font.bin"))
    parser.add_argument("--out-header", type=Path, default=Path("App/japanese_font_external.h"))
    parser.add_argument("--out-manifest", type=Path, default=Path("tools/japanese_font_manifest.json"))
    generate(parser.parse_args())


if __name__ == "__main__":
    main()
