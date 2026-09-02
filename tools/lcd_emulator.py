#!/usr/bin/env python3
"""K1の128×64 LCDフレームバッファを確認する簡易エミュレータ。"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

try:
    from PIL import Image, ImageDraw
except ImportError as exc:  # pragma: no cover - depends on the local tool setup
    raise SystemExit("このツールには Pillow が必要です。") from exc

ROOT = Path(__file__).resolve().parents[1]
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from render_bitmap_atlas import parse_source

LCD_WIDTH = 128
LCD_HEIGHT = 64
LCD_PAGES = LCD_HEIGHT // 8
LCD_BYTES = LCD_WIDTH * LCD_PAGES
EXTERNAL_GLYPH_BYTES = 32
EXTERNAL_INDEX_BYTES = 13_956
EXTERNAL_BITMAP_OFFSET = EXTERNAL_INDEX_BYTES


@dataclass
class LcdFrame:
    """ST7565互換のページ形式フレームバッファ。"""

    data: bytearray = field(default_factory=lambda: bytearray(LCD_BYTES))

    def __post_init__(self) -> None:
        if len(self.data) != LCD_BYTES:
            raise ValueError(f"フレームバッファは{LCD_BYTES} bytes必要です。")

    def clear(self) -> None:
        self.data[:] = b"\x00" * LCD_BYTES

    def pixel(self, x: int, y: int, on: bool = True) -> None:
        if not (0 <= x < LCD_WIDTH and 0 <= y < LCD_HEIGHT):
            return
        offset = (y // 8) * LCD_WIDTH + x
        mask = 1 << (y % 8)
        if on:
            self.data[offset] |= mask
        else:
            self.data[offset] &= ~mask

    def line(self, x1: int, y1: int, x2: int, y2: int, on: bool = True) -> None:
        """C側の整数Bresenham描画に合わせて線を引く。"""
        dx = abs(x2 - x1)
        sx = 1 if x1 < x2 else -1
        dy = -abs(y2 - y1)
        sy = 1 if y1 < y2 else -1
        error = dx + dy
        while True:
            self.pixel(x1, y1, on)
            if x1 == x2 and y1 == y2:
                break
            twice = 2 * error
            if twice >= dy:
                error += dy
                x1 += sx
            if twice <= dx:
                error += dx
                y1 += sy

    def rectangle(self, x1: int, y1: int, x2: int, y2: int, on: bool = True) -> None:
        self.line(x1, y1, x1, y2, on)
        self.line(x1, y1, x2, y1, on)
        self.line(x2, y1, x2, y2, on)
        self.line(x1, y2, x2, y2, on)

    def image(self, scale: int = 4):
        if scale < 1:
            raise ValueError("scaleは1以上にしてください。")
        image = Image.new("RGB", (LCD_WIDTH, LCD_HEIGHT), "white")
        pixels = image.load()
        for y in range(LCD_HEIGHT):
            for x in range(LCD_WIDTH):
                if self.data[(y // 8) * LCD_WIDTH + x] & (1 << (y % 8)):
                    pixels[x, y] = (20, 20, 20)
        return image.resize((LCD_WIDTH * scale, LCD_HEIGHT * scale), Image.Resampling.NEAREST)


@dataclass(frozen=True)
class FontTables:
    big: dict[int, bytes]
    big_digits: dict[int, bytes]
    small: dict[int, bytes]
    tiny: dict[int, bytes]
    vfo_default: bytes
    vfo_not_default: bytes


def _find_array(arrays, name: str):
    for array in arrays:
        if array.name == name:
            return array
    raise ValueError(f"フォント配列が見つかりません: {name}")


def _find_last_array(arrays, name: str):
    for array in reversed(arrays):
        if array.name == name:
            return array
    raise ValueError(f"ビットマップ配列が見つかりません: {name}")


def _glyph_map(array, first_code: int | None = None) -> dict[int, bytes]:
    if array.glyphs is not None:
        return {int(glyph["code"]): bytes(glyph["bytes"]) for glyph in array.glyphs}
    if first_code is None or array.element_width is None:
        raise ValueError(f"フォント配列にコードポイント情報がありません: {array.name}")
    width = array.element_width
    if len(array.values) % width:
        raise ValueError(f"フォント配列の要素長が不正です: {array.name}")
    return {
        first_code + index: array.values[index * width : (index + 1) * width]
        for index in range(len(array.values) // width)
    }


def load_font_tables(root: Path = ROOT) -> FontTables:
    occurrences: dict[str, int] = {}
    arrays = parse_source(root / "App" / "font.c", occurrences)
    bitmap_arrays = parse_source(root / "App" / "bitmaps.c", {})
    return FontTables(
        big=_glyph_map(_find_array(arrays, "gFontBig")),
        big_digits=_glyph_map(_find_array(arrays, "gFontBigDigits"), first_code=0),
        small=_glyph_map(_find_array(arrays, "gFontSmall"), first_code=0x21),
        tiny=_glyph_map(_find_array(arrays, "gFont3x5"), first_code=0x20),
        vfo_default=_find_last_array(bitmap_arrays, "BITMAP_VFO_Default").values,
        vfo_not_default=_find_last_array(bitmap_arrays, "BITMAP_VFO_NotDefault").values,
    )


def load_internal_codepoints(root: Path = ROOT) -> dict[int, int]:
    """helper.cの内部コード→Unicode対応表を読み取る。"""
    text = (root / "App" / "ui" / "helper.c").read_text(encoding="utf-8")
    return {
        int(code, 16): int(codepoint, 16)
        for code, codepoint in re.findall(
            r"case 0x([0-9A-Fa-f]{2}):\s*return 0x([0-9A-Fa-f]{4})", text
        )
    }


def _right_edge(start: int, end: int) -> int:
    return LCD_WIDTH - 1 if end == 0 else min(end, LCD_WIDTH - 1)


def _centered_start(start: int, end: int, length: int, advance: int) -> int:
    if end <= start or length == 0:
        return start
    available = end - start
    used = length * advance
    if used >= available:
        return start
    return start + (available - used + 1) // 2


def _internal_glyph(code: int, fonts: FontTables, small: bool) -> bytes | None:
    if 0x21 <= code <= 0x7E:
        return (fonts.small if small else fonts.big).get(code)
    return None


def draw_small_internal(
    frame: LcdFrame,
    codes: Iterable[int] | bytes,
    fonts: FontTables,
    start: int,
    end: int,
    line: int,
) -> None:
    values = list(codes)
    x_start = _centered_start(start, end, len(values), 7)
    if not (0 <= x_start < LCD_WIDTH and 0 <= line < LCD_PAGES):
        return
    right = _right_edge(start, end)
    for index, code in enumerate(values):
        x = x_start + index * 7 + 1
        glyph = _internal_glyph(code, fonts, small=True)
        if glyph is None or x > right:
            continue
        width = min(6, right + 1 - x, LCD_WIDTH - x)
        if width > 0:
            offset = line * LCD_WIDTH + x
            frame.data[offset : offset + width] = glyph[:width]


def draw_large_internal(
    frame: LcdFrame,
    codes: Iterable[int] | bytes,
    fonts: FontTables,
    start: int,
    end: int,
    line: int,
) -> None:
    values = list(codes)
    if not (0 <= line + 1 < LCD_PAGES):
        return
    right = _right_edge(start, end)
    for index, code in enumerate(values):
        x = start + index * 8
        glyph = _internal_glyph(code, fonts, small=False)
        if glyph is None or x > right:
            continue
        width = min(7, right + 1 - x, LCD_WIDTH - x)
        if width <= 0:
            continue
        frame.data[line * LCD_WIDTH + x : line * LCD_WIDTH + x + width] = glyph[:width]
        frame.data[(line + 1) * LCD_WIDTH + x : (line + 1) * LCD_WIDTH + x + width] = glyph[7 : 7 + width]


class ExternalFont:
    """japanese_font.binの4-byte indexと16×16 bitmapを読む。"""

    def __init__(self, path: Path):
        self.data = path.read_bytes()
        if len(self.data) < EXTERNAL_BITMAP_OFFSET:
            raise ValueError("外部フォントのindexが短すぎます。")
        self.glyph_indices: dict[int, int] = {}
        for offset in range(0, EXTERNAL_INDEX_BYTES, 4):
            codepoint = int.from_bytes(self.data[offset : offset + 2], "little")
            glyph_index = int.from_bytes(self.data[offset + 2 : offset + 4], "little")
            self.glyph_indices[codepoint] = glyph_index

    def glyph(self, codepoint: int) -> bytes | None:
        glyph_index = self.glyph_indices.get(codepoint)
        if glyph_index is None:
            return None
        offset = EXTERNAL_BITMAP_OFFSET + glyph_index * EXTERNAL_GLYPH_BYTES
        glyph = self.data[offset : offset + EXTERNAL_GLYPH_BYTES]
        return glyph if len(glyph) == EXTERNAL_GLYPH_BYTES else None


def draw_external_glyph(
    frame: LcdFrame, font: ExternalFont, codepoint: int, x: int, line: int, end: int
) -> bool:
    glyph = font.glyph(codepoint)
    if glyph is None or not (0 <= line + 1 < LCD_PAGES) or x >= LCD_WIDTH or x > end:
        return False
    width = min(16, LCD_WIDTH - x, end + 1 - x)
    for page in range(2):
        for column in range(width):
            value = 0
            for row in range(8):
                absolute_row = page * 8 + row
                bitmap_row = int.from_bytes(
                    glyph[absolute_row * 2 : absolute_row * 2 + 2], "little"
                )
                if bitmap_row & (0x8000 >> column):
                    value |= 1 << row
            frame.data[(line + page) * LCD_WIDTH + x + column] = value
    return True


def draw_external_text(
    frame: LcdFrame, text: str, fonts: FontTables, external: ExternalFont,
    start: int, end: int, line: int,
) -> bool:
    """Draw a UTF-8 channel name using the same 8/16-pixel advances as K1."""
    codepoints = list(map(ord, text))
    right = _right_edge(start, end)
    pixel_width = sum(8 if codepoint < 0x80 else 16 for codepoint in codepoints)
    if line + 1 >= LCD_PAGES or pixel_width > right + 1 - start:
        return False
    if any(codepoint >= 0x80 and external.glyph(codepoint) is None
           for codepoint in codepoints):
        return False

    x = start if end == 0 else start + (right + 1 - start - pixel_width) // 2
    for codepoint in codepoints:
        if codepoint < 0x80:
            if codepoint > 0x20:
                glyph = fonts.big.get(codepoint)
                if glyph is None:
                    return False
                width = min(7, right + 1 - x)
                frame.data[line * LCD_WIDTH + x : line * LCD_WIDTH + x + width] = glyph[:width]
                frame.data[(line + 1) * LCD_WIDTH + x : (line + 1) * LCD_WIDTH + x + width] = glyph[7 : 7 + width]
            x += 8
        else:
            if not draw_external_glyph(frame, external, codepoint, x, line, right):
                return False
            x += 16
    return True


def draw_external_text_compact(
    frame: LcdFrame, text: str, fonts: FontTables, external: ExternalFont,
    start: int, end: int, line: int,
) -> bool:
    """UI_PrintJapaneseChannelNameCompactの2×2間引きを再現する。"""
    codepoints = list(map(ord, text))
    right = _right_edge(start, end)
    pixel_width = sum(7 if codepoint < 0x80 else 8 for codepoint in codepoints)
    if not (0 <= line < LCD_PAGES) or pixel_width > right + 1 - start:
        return False
    if any(codepoint >= 0x80 and external.glyph(codepoint) is None
           for codepoint in codepoints):
        return False

    x = start + (right + 1 - start - pixel_width) // 2
    for codepoint in codepoints:
        if codepoint < 0x80:
            if codepoint > 0x20:
                glyph = fonts.small.get(codepoint)
                if glyph is None or x + 1 > right:
                    return False
                width = min(6, right + 1 - (x + 1))
                frame.data[line * LCD_WIDTH + x + 1 :
                           line * LCD_WIDTH + x + 1 + width] = glyph[:width]
            x += 7
            continue

        glyph = external.glyph(codepoint)
        if glyph is None:
            return False
        width = min(8, right + 1 - x, LCD_WIDTH - x)
        for column in range(width):
            value = 0
            source_column = column * 2
            for row in range(8):
                source_row = row * 2
                bitmap_row = int.from_bytes(
                    glyph[source_row * 2 : source_row * 2 + 2], "little"
                )
                if bitmap_row & (0x8000 >> source_column):
                    value |= 1 << row
            frame.data[line * LCD_WIDTH + x + column] = value
        x += 8
    return True


def draw_external_internal(
    frame: LcdFrame,
    codes: Iterable[int] | bytes,
    fonts: FontTables,
    external: ExternalFont,
    internal_codepoints: dict[int, int],
    start: int,
    end: int,
    line: int,
) -> bool:
    codepoints: list[int] = []
    for code in codes:
        if 0x20 <= code <= 0x7E:
            codepoints.append(code)
        elif code in internal_codepoints:
            codepoints.append(internal_codepoints[code])
        else:
            return False

    pixel_width = sum(8 if codepoint < 0x80 else 16 for codepoint in codepoints)
    right = _right_edge(start, end)
    if line + 1 >= LCD_PAGES or pixel_width > right + 1 - start:
        return False
    if any(codepoint >= 0x80 and external.glyph(codepoint) is None
           for codepoint in codepoints):
        return False

    x = start if end == 0 else start + (right + 1 - start - pixel_width) // 2
    for codepoint in codepoints:
        if codepoint < 0x80:
            if codepoint > 0x20:
                glyph = fonts.big.get(codepoint)
                if glyph is None:
                    return False
                width = min(7, right + 1 - x)
                frame.data[line * LCD_WIDTH + x : line * LCD_WIDTH + x + width] = glyph[:width]
                frame.data[(line + 1) * LCD_WIDTH + x : (line + 1) * LCD_WIDTH + x + width] = glyph[7 : 7 + width]
            x += 8
        else:
            if not draw_external_glyph(frame, external, codepoint, x, line, right):
                return False
            x += 16
    return True


def draw_ring(frame: LcdFrame, cx: int, cy: int, outer: int, inner: int) -> None:
    for y in range(-outer, outer + 1):
        for x in range(-outer, outer + 1):
            distance = x * x + y * y
            if inner * inner <= distance <= outer * outer:
                frame.pixel(cx + x, cy + y)


def draw_category_icon(frame: LcdFrame, category: int, x: int = 40, y: int = 3) -> None:
    if category == 0:  # チャンネル
        frame.rectangle(x + 8, y + 11, x + 38, y + 34)
        frame.line(x + 18, y + 11, x + 23, y + 2)
        frame.line(x + 23, y + 2, x + 28, y + 11)
        frame.line(x + 14, y + 17, x + 32, y + 17)
        frame.line(x + 14, y + 23, x + 26, y + 23)
    elif category == 1:  # スキャン
        draw_ring(frame, x + 22, y + 17, 12, 9)
        frame.line(x + 31, y + 26, x + 42, y + 36)
        frame.line(x + 39, y + 36, x + 42, y + 33)
    elif category == 2:  # キー
        for row in range(3):
            for column in range(3):
                left = x + 8 + column * 11
                top = y + 7 + row * 10
                frame.rectangle(left, top, left + 7, top + 6)
        frame.rectangle(x + 19, y + 37, x + 27, y + 39)
    elif category == 3:  # 電源
        frame.line(x + 23, y + 2, x + 23, y + 21)
        points = ((x + 15, y + 8, x + 10, y + 14), (x + 10, y + 14, x + 10, y + 24),
                  (x + 10, y + 24, x + 16, y + 33), (x + 16, y + 33, x + 23, y + 37),
                  (x + 23, y + 37, x + 30, y + 33), (x + 30, y + 33, x + 36, y + 24),
                  (x + 36, y + 24, x + 36, y + 14), (x + 36, y + 14, x + 31, y + 8))
        for point in points:
            frame.line(*point)
    elif category == 4:  # 表示
        frame.rectangle(x + 6, y + 9, x + 40, y + 31)
        frame.rectangle(x + 12, y + 14, x + 34, y + 26)
        frame.line(x + 18, y + 36, x + 29, y + 36)
        frame.line(x + 23, y + 31, x + 23, y + 36)
    elif category == 5:  # タイマー
        draw_ring(frame, x + 23, y + 20, 16, 13)
        frame.line(x + 23, y + 20, x + 23, y + 10)
        frame.line(x + 23, y + 20, x + 31, y + 25)
        frame.line(x + 18, y + 2, x + 28, y + 2)
        frame.line(x + 18, y + 2, x + 15, y + 6)
        frame.line(x + 28, y + 2, x + 31, y + 6)
    elif category == 6:  # 音声
        for point in ((x + 8, y + 17, x + 16, y + 17), (x + 16, y + 17, x + 27, y + 8),
                      (x + 27, y + 8, x + 27, y + 32), (x + 27, y + 32, x + 16, y + 23),
                      (x + 16, y + 23, x + 8, y + 23), (x + 35, y + 14, x + 40, y + 19),
                      (x + 40, y + 19, x + 35, y + 25)):
            frame.line(*point)
    elif category == 7:  # 受信
        frame.line(x + 23, y + 8, x + 23, y + 35)
        frame.line(x + 23, y + 8, x + 17, y + 2)
        frame.line(x + 23, y + 8, x + 29, y + 2)
        frame.line(x + 9, y + 37, x + 37, y + 37)
        frame.line(x + 14, y + 32, x + 32, y + 32)
        frame.line(x + 17, y + 27, x + 29, y + 27)
    elif category == 8:  # DTMF
        for row in range(4):
            for column in range(3):
                left = x + 8 + column * 11
                top = y + 3 + row * 9
                frame.rectangle(left, top, left + 7, top + 6)
    elif category == 9:  # 設定
        draw_ring(frame, x + 23, y + 20, 15, 7)
        for point in ((x + 3, y + 20, x + 8, y + 20), (x + 38, y + 20, x + 43, y + 20),
                      (x + 23, y + 0, x + 23, y + 5), (x + 23, y + 35, x + 23, y + 40),
                      (x + 9, y + 6, x + 13, y + 10), (x + 33, y + 30, x + 37, y + 34),
                      (x + 33, y + 10, x + 37, y + 6), (x + 9, y + 34, x + 13, y + 30)):
            frame.line(*point)
    else:  # ALL
        for row in range(4):
            top = y + 6 + row * 9
            frame.line(x + 8, top, x + 12, top)
            frame.line(x + 17, top, x + 40, top)


CATEGORY_NAMES = ("CHANNELS", "SCAN", "KEYS", "POWER", "DISPLAY", "TIMERS",
                  "AUDIO", "RADIO", "DTMF", "SERVICE", "ALL")
CATEGORY_LABELS = (
    b"CHANNELS", b"SCAN", b"KEYS", b"POWER", b"DISPLAY", b"TIMERS",
    b"AUDIO", b"RADIO", b"DTMF", b"SERVICE", b"ALL",
)
CATEGORY_ITEM_COUNTS = (14, 6, 8, 4, 11, 4, 5, 6, 5, 6, 50)


def _draw_category_chevrons(frame: LcdFrame) -> None:
    frame.line(15, 22, 7, 30)
    frame.line(15, 22, 7, 14)
    frame.line(113, 22, 121, 30)
    frame.line(113, 22, 121, 14)


def render_category(index: int, fonts: FontTables, total: int = len(CATEGORY_NAMES)) -> LcdFrame:
    if not 0 <= index < len(CATEGORY_NAMES):
        raise ValueError("カテゴリ番号が範囲外です。")
    frame = LcdFrame()
    frame.line(0, 0, LCD_WIDTH - 1, 0)
    _draw_category_chevrons(frame)
    draw_category_icon(frame, index)
    draw_small_internal(frame, CATEGORY_LABELS[index], fonts, 0, LCD_WIDTH - 1, 6)
    draw_small_internal(frame, f"{CATEGORY_ITEM_COUNTS[index]:02d}".encode(), fonts, 2, 0, 7)
    draw_small_internal(frame, b"ITEMS", fonts, 18, 0, 7)
    draw_small_internal(frame, f"{index + 1:02d}/{total:02d}".encode(), fonts, 92, 0, 7)
    return frame


def _draw_menu_separator(frame: LcdFrame) -> None:
    frame.line(48, 0, 48, 55)
    for x in range(0, 48, 2):
        frame.data[5 * LCD_WIDTH + x] = 0x40


def _draw_menu_badge(frame: LcdFrame, text: bytes, fonts: FontTables) -> None:
    # UI_MENU_DrawTopRightRoundedBadgeの小字反転を、視認確認用に再現する。
    width = len(text) * 7 + 1
    x = 50 + max(1, (78 - width) // 2)
    draw_small_internal(frame, text, fonts, x, 0, 1)
    for column in range(x - 1, min(128, x + width + 1)):
        frame.data[1 * LCD_WIDTH + column] ^= 0xFF
        frame.data[0 * LCD_WIDTH + column] ^= 0x80


def render_menu(submenu: bool, fonts: FontTables, external: ExternalFont,
                internal_codepoints: dict[int, int]) -> LcdFrame:
    frame = LcdFrame()
    _draw_menu_separator(frame)
    current = b"RXDCS"
    if submenu:
        draw_external_internal(frame, current, fonts, external, internal_codepoints,
                               0, 47, 0) or draw_large_internal(frame, current, fonts, 0, 47, 0)
        value = b"DCS"
        draw_external_internal(frame, value, fonts, external, internal_codepoints,
                               50, 127, 2) or draw_large_internal(frame, value, fonts, 50, 127, 2)
    else:
        draw_small_internal(frame, b"RxCTCS", fonts, 0, 47, 1)
        draw_external_internal(frame, current, fonts, external, internal_codepoints,
                               0, 47, 2) or draw_large_internal(frame, current, fonts, 0, 47, 2)
        draw_small_internal(frame, b"RXCTCS", fonts, 0, 47, 4)
        draw_small_internal(frame, b"01/03", fonts, 6, 0, 6)
        draw_external_internal(frame, b"DCS", fonts, external, internal_codepoints,
                               50, 127, 2) or draw_large_internal(frame, b"DCS", fonts, 50, 127, 2)
        _draw_menu_badge(frame, b"01/32", fonts)
    return frame


def render_popup(fonts: FontTables) -> LcdFrame:
    frame = LcdFrame()
    message = b"RX ONLY"
    start = _centered_start(9, 118, len(message), 8)
    draw_large_internal(frame, message, fonts, start, 118, 2)
    draw_small_internal(frame, b"EXIT", fonts, 9, 118, 6)
    return frame


def draw_small_inverse(
    frame: LcdFrame, text: bytes, fonts: FontTables, start: int, line: int,
) -> None:
    """UI_PrintStringSmallNormalInverseの受信ヘッダー部分を再現する。"""
    end = 0
    draw_small_internal(frame, text, fonts, start, end, line)
    if not text or line == 0 or line >= LCD_PAGES:
        return

    x_start = _centered_start(start, end, len(text), 7)
    x_end = min(LCD_WIDTH, x_start + len(text) * 7)
    if x_start > 0:
        frame.data[line * LCD_WIDTH + x_start - 1] ^= 0x7F
    for column in range(x_start, x_end):
        frame.data[line * LCD_WIDTH + column] ^= 0xFF
        frame.data[(line - 1) * LCD_WIDTH + column] ^= 0x80
    if x_end < LCD_WIDTH:
        frame.data[line * LCD_WIDTH + x_end] ^= 0x7F


def draw_tiny_internal(
    frame: LcdFrame, text: bytes, fonts: FontTables, x: int, y: int,
) -> None:
    """GUI_DisplaySmallestの3×5字形を物理座標へ描く。"""
    for code in text:
        glyph = fonts.tiny.get(code)
        if glyph is None:
            return
        for column, bits in enumerate(glyph):
            for row in range(6):
                if bits & (1 << row):
                    frame.pixel(x + column, y + row)
        x += 4


def draw_tiny_inverse(
    frame: LcdFrame, text: bytes, fonts: FontTables, x: int, page: int, end: int,
) -> None:
    """GUI_DisplaySmallestInverseのページ内反転を再現する。"""
    draw_tiny_internal(frame, text, fonts, x, page * 8 + 1)
    if not text or not (0 <= page < LCD_PAGES):
        return
    start = x - 2
    if not (0 <= start < LCD_WIDTH):
        return
    right = min(end, LCD_WIDTH - 1)
    frame.data[page * LCD_WIDTH + start] ^= 0x3E
    for column in range(start + 1, right):
        frame.data[page * LCD_WIDTH + column] ^= 0x7F
    frame.data[page * LCD_WIDTH + right] ^= 0x3E


def _draw_receive_marker(frame: LcdFrame, fonts: FontTables,
                         line: int, active: bool) -> None:
    """UI_DisplayMainが使うVFOマーカーbitmapをそのまま配置する。"""
    marker = fonts.vfo_default if active else fonts.vfo_not_default
    offset = line * LCD_WIDTH
    frame.data[offset : offset + len(marker)] = marker


def _draw_receive_frequency(frame: LcdFrame, fonts: FontTables,
                            frequency: bytes, line: int, x_start: int) -> None:
    """UI_DisplayFrequencyの13-column数字配置を再現する。"""
    x = x_start
    can_display = False
    for code in frequency:
        if can_display or code != ord(" "):
            can_display = True
            if ord("0") <= code <= ord("9"):
                glyph = fonts.big_digits[code - ord("0")]
                for column in range(10):
                    frame.data[line * LCD_WIDTH + x + 2 + column] = glyph[column]
                    frame.data[(line + 1) * LCD_WIDTH + x + 2 + column] = glyph[10 + column]
                x += 13
            elif code == ord("."):
                for _ in range(3):
                    frame.data[(line + 1) * LCD_WIDTH + x] = 0x60
                    x += 1
                continue
        else:
            continue

    # UI_DrawMain keeps the two fractional digits at the far right of the
    # following page when the large frequency font is active.
    draw_small_internal(frame, b"00", fonts, x_start + 81, 0, line + 1)


def _draw_receive_frequency_small(frame: LcdFrame, fonts: FontTables,
                                  line: int) -> None:
    """デュアルVFOの8×8名称経路で使う小字形周波数を再現する。"""
    draw_small_internal(frame, b"431.52000", fonts, 36, 0, line + 1)


def _draw_receive_metadata(frame: LcdFrame, fonts: FontTables, line: int,
                           main_only: bool, main_vfo: bool) -> None:
    """受信状態を一行の小字形へまとめて表示する。"""
    page = 4 if main_only else (2 if line == 0 else 6)
    status = b"FM DC 023N N SQL5" if main_vfo else b"FM DC 023N N"
    draw_small_internal(frame, status, fonts, 2, 0, page)


def _draw_receive_rssi(frame: LcdFrame, fonts: FontTables, dual: bool) -> None:
    """DisplayRSSIBarのページ消去と代表的なSメーターを再現する。"""
    line = 3 if dual else 5
    frame.data[line * LCD_WIDTH : (line + 1) * LCD_WIDTH] = b"\x00" * LCD_WIDTH
    # RX-only uses the 6×8 font for the dedicated meter row.  The bar begins
    # at the same x coordinate as the production code (2 + 7×8 + 4).
    draw_small_internal(frame, b"-117 dBm", fonts, 2, 0, line)
    # -117 dBm corresponds to S5 in the current six-dB S-unit mapping.
    _draw_level_bar(frame, line, level=5, bars=13)


def _draw_level_bar(frame: LcdFrame, line: int, level: int, bars: int) -> None:
    """F4HWNのDrawLevelBarをgSetting_set_met=0として再現する。"""
    level = min(level, bars)
    simple = (0x3E, 0x3E, 0x3E, 0x3E)
    hollow = (0x3E, 0x22, 0x22, 0x3E)
    for index in range(level):
        values = simple if index < bars - 4 else hollow
        offset = line * LCD_WIDTH + 62 + index * 5
        frame.data[offset : offset + 4] = bytes(values)


def render_receive(fonts: FontTables, external: ExternalFont, *,
                   dual: bool = False, external_name: bool = True,
                   compact_name: bool = False, ascii_name: bool = False,
                   name_freq: bool = True) -> LcdFrame:
    """Render the K1 receive layout used for the visual UI audit.

    The sample covers the default 16×16 external name path, the compact 8×8
    path, and the readable ASCII mode.  It does not emulate radio state timing.
    """
    frame = LcdFrame()
    vfo_lines = (0, 4) if dual else (0,)
    effective_compact_name = compact_name or dual
    for vfo, line in enumerate(vfo_lines):
        _draw_receive_marker(frame, fonts, line, vfo == 0)
        draw_small_inverse(frame, f"{vfo + 1:04d}".encode(), fonts, 1, line + 1)
        # F4HWN's receive/audio indicator is a 3×5 string at y=1/33, while
        # the channel number starts on the following LCD page.
        draw_tiny_internal(frame, b"FLAT", fonts, 10, line * 8 + 1)

        name_drawn = False
        if external_name and not ascii_name:
            if effective_compact_name:
                name_drawn = draw_external_text_compact(
                    frame, "東京", fonts, external, 33, 127, line,
                )
            else:
                name_drawn = draw_external_text(
                    frame, "東京", fonts, external, 33, 127, line,
                )
        if not name_drawn:
            if effective_compact_name:
                draw_small_internal(frame, b"TOKYO", fonts, 33, 127, line)
            else:
                draw_external_text(frame, "TOKYO", fonts, external, 33, 127, line)

        if name_freq:
            if dual and effective_compact_name:
                _draw_receive_frequency_small(frame, fonts, line)
            else:
                _draw_receive_frequency(
                    frame, fonts, b"431.520", line + 2,
                    x_start=32 if dual else 16,
                )

        _draw_receive_metadata(frame, fonts, line, main_only=not dual,
                               main_vfo=vfo == 0)

    if not dual:
        # UI_DisplayMain reserves page 6 for the active VFO selector in
        # main-only mode.  It is absent from dual-VFO screens.
        draw_tiny_inverse(frame, b"VFO A", fonts, 107, 6, 127)

    _draw_receive_rssi(frame, fonts, dual)
    return frame


def make_contact_sheet(frames: list[LcdFrame], labels: list[str], scale: int, title: str):
    margin = 12
    label_height = 26
    columns = 3
    rows = (len(frames) + columns - 1) // columns
    cell_width = LCD_WIDTH * scale + margin * 2
    cell_height = LCD_HEIGHT * scale + label_height + margin
    image = Image.new("RGB", (cell_width * columns, cell_height * rows + 28), "#eeeeee")
    draw = ImageDraw.Draw(image)
    draw.text((margin, 8), title, fill="#111111")
    for index, (frame, label) in enumerate(zip(frames, labels)):
        column = index % columns
        row = index // columns
        x = column * cell_width + margin
        y = row * cell_height + 28 + label_height
        draw.rectangle((x - 1, y - 1, x + LCD_WIDTH * scale, y + LCD_HEIGHT * scale), outline="#888888")
        image.paste(frame.image(scale), (x, y))
        draw.text((x, y - label_height + 4), label, fill="#111111")
    return image


def _save(image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    print(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--screen", choices=("categories", "category", "menu", "popup", "receive", "raw"),
                        default="categories")
    parser.add_argument("--category", type=int, default=0, help="category画面の番号（0始まり）")
    parser.add_argument("--raw", type=Path, help="1024-byteのST7565フレームバッファ")
    parser.add_argument("--out", type=Path, default=ROOT / "tmp" / "lcd-preview.png")
    parser.add_argument("--scale", type=int, default=4)
    args = parser.parse_args(argv)

    fonts = load_font_tables(ROOT)
    if args.screen == "categories":
        frames = [render_category(index, fonts) for index in range(len(CATEGORY_NAMES))]
        image = make_contact_sheet(frames, [f"{i + 1:02d} {name}" for i, name in enumerate(CATEGORY_NAMES)],
                                   args.scale, "K1 LCD category preview")
    elif args.screen == "category":
        image = render_category(args.category, fonts).image(args.scale)
    elif args.screen == "menu":
        external = ExternalFont(ROOT / "docs" / "fonts" / "japanese_font.bin")
        internal_codepoints = load_internal_codepoints(ROOT)
        frames = [render_menu(False, fonts, external, internal_codepoints),
                  render_menu(True, fonts, external, internal_codepoints)]
        image = make_contact_sheet(frames, ["menu list", "menu value"], args.scale,
                                   "K1 LCD menu preview")
    elif args.screen == "popup":
        image = render_popup(fonts).image(args.scale)
    elif args.screen == "receive":
        external = ExternalFont(ROOT / "docs" / "fonts" / "japanese_font.bin")
        frames = [
            render_receive(fonts, external, dual=False, external_name=True),
            render_receive(fonts, external, dual=False, external_name=False,
                           ascii_name=True),
            render_receive(fonts, external, dual=True, external_name=True),
            render_receive(fonts, external, dual=False, external_name=True,
                           compact_name=True),
            render_receive(fonts, external, dual=True, external_name=True,
                           compact_name=True),
        ]
        image = make_contact_sheet(
            frames,
            ["main-only / Izumi 16x16", "main-only / ASCII mode",
             "dual VFO / Izumi 8x8 (auto)", "main-only / Izumi 8x8",
             "dual VFO / Izumi 8x8"],
            args.scale,
            "K1 LCD receive preview",
        )
    else:
        if args.raw is None:
            parser.error("--screen raw では --raw が必要です。")
        frame = LcdFrame(bytearray(args.raw.read_bytes()))
        image = frame.image(args.scale)
    _save(image, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
