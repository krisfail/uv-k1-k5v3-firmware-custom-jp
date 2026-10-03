"""実機LCDデバッグファームのフレームを画像化するツール。

このツールは画面レイアウトを再実装しない。デバッグ専用ファームへ
イベントを要求し、ファームウェアのC描画処理が生成したST7565の物理
フレームバッファを受信して、確認用PNGへ変換する。
"""

from __future__ import annotations

import argparse
import io
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from PIL import Image, ImageColor, ImageDraw


LCD_WIDTH = 128
LCD_HEIGHT = 64
LCD_PAGES = 8
LCD_BYTES = LCD_WIDTH * LCD_PAGES
LCD_DEBUG_COMMAND_ID = 0x06F0
LCD_DEBUG_PROTOCOL_VERSION = 1
LCD_DEBUG_FRAME_MAGIC = b"LCDF"
LCD_DEBUG_FRAME_HEADER = struct.Struct("<4sBBBBHH")

BAUD_RATE = 38400

EVENTS = {
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
}
STANDARD_EVENTS = tuple(EVENTS)

LCD_PALETTES = {
    "classic": ("#f7f7f0", "#172126"),
    "orange": ("#f8d9a7", "#3a1f08"),
}


@dataclass
class LcdFrame:
    """ST7565の物理ページ順に並んだ1024バイトのフレーム。"""

    data: bytearray

    def __post_init__(self) -> None:
        if len(self.data) != LCD_BYTES:
            raise ValueError(f"フレームは{LCD_BYTES} bytes必要です")

    @classmethod
    def from_bytes(cls, data: bytes) -> "LcdFrame":
        return cls(bytearray(data))

    def image(self, scale: int = 4, lcd: str = "classic") -> Image.Image:
        if scale < 1:
            raise ValueError("scaleは1以上にしてください")
        try:
            background_hex, foreground_hex = LCD_PALETTES[lcd]
        except KeyError as exc:
            raise ValueError(f"未対応のLCD配色です: {lcd}") from exc
        background = ImageColor.getrgb(background_hex)
        foreground = ImageColor.getrgb(foreground_hex)

        image = Image.new("RGB", (LCD_WIDTH, LCD_HEIGHT), background)
        pixels = image.load()
        for y in range(LCD_HEIGHT):
            page = y // 8
            mask = 1 << (y % 8)
            for x in range(LCD_WIDTH):
                if self.data[page * LCD_WIDTH + x] & mask:
                    pixels[x, y] = foreground
        return image.resize(
            (LCD_WIDTH * scale, LCD_HEIGHT * scale), Image.Resampling.NEAREST
        )


@dataclass(frozen=True)
class CapturedFrame:
    event: int
    status: int
    flags: int
    frame: LcdFrame


class CaptureError(RuntimeError):
    """デバッグファームとのフレーム交換に失敗した。"""


def crc16_xmodem(data: bytes) -> int:
    crc = 0
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc <<= 1
            if crc & 0x10000:
                crc = (crc ^ 0x1021) & 0xFFFF
    return crc & 0xFFFF


def _xorarr(data: bytes) -> bytes:
    table = (22, 108, 20, 230, 46, 145, 13, 64,
             33, 53, 213, 64, 19, 3, 233, 128)
    return bytes(byte ^ table[index % len(table)]
                 for index, byte in enumerate(data))


def build_request(event: str | int) -> bytes:
    """既存UARTコマンド形式でLCDイベント要求を作る。"""
    event_id = EVENTS[event] if isinstance(event, str) else event
    if not 1 <= event_id <= 0xFF:
        raise ValueError("LCDイベント番号が範囲外です")
    body = struct.pack("<HHBB", LCD_DEBUG_COMMAND_ID, 2, event_id, 0)
    packet = body + struct.pack("<H", crc16_xmodem(body))
    return struct.pack(">HBB", 0xABCD, len(body), 0) + _xorarr(packet) + b"\xDC\xBA"


def _read_exact(stream: BinaryIO, size: int) -> bytes:
    result = bytearray()
    while len(result) < size:
        chunk = stream.read(size - len(result))
        if not chunk:
            raise CaptureError("LCDデバッグフレームが途中で終わりました")
        result.extend(chunk)
    return bytes(result)


def _read_header(stream: BinaryIO) -> bytes:
    """UART起動メッセージ等を読み飛ばしてLCDF境界へ同期する。"""
    window = bytearray()
    while True:
        byte = _read_exact(stream, 1)
        window.extend(byte)
        if len(window) > len(LCD_DEBUG_FRAME_MAGIC):
            del window[0]
        if bytes(window) == LCD_DEBUG_FRAME_MAGIC:
            return bytes(window) + _read_exact(
                stream, LCD_DEBUG_FRAME_HEADER.size - len(LCD_DEBUG_FRAME_MAGIC)
            )


def read_frame(stream: BinaryIO) -> CapturedFrame:
    header = _read_header(stream)
    magic, version, event, status, flags, size, expected_crc = (
        LCD_DEBUG_FRAME_HEADER.unpack(header)
    )
    if magic != LCD_DEBUG_FRAME_MAGIC:
        raise CaptureError("LCDデバッグフレームのマジックが不正です")
    if version != LCD_DEBUG_PROTOCOL_VERSION:
        raise CaptureError(f"未対応のLCDデバッグプロトコルです: {version}")
    if size != LCD_BYTES:
        raise CaptureError(f"LCDフレーム長が不正です: {size}")

    data = _read_exact(stream, size)
    actual_crc = crc16_xmodem(data)
    if actual_crc != expected_crc:
        raise CaptureError(
            f"LCDフレームのCRCが一致しません: {actual_crc:04X} != {expected_crc:04X}"
        )
    return CapturedFrame(event, status, flags, LcdFrame.from_bytes(data))


def make_contact_sheet(images: list[tuple[str, Image.Image]], title: str) -> Image.Image:
    scale = images[0][1].width // LCD_WIDTH
    margin = 12
    label_height = 24
    columns = 3
    rows = (len(images) + columns - 1) // columns
    cell_width = LCD_WIDTH * scale + margin * 2
    cell_height = LCD_HEIGHT * scale + label_height + margin
    result = Image.new(
        "RGB", (cell_width * columns, cell_height * rows + 28), "#eeeeee"
    )
    draw = ImageDraw.Draw(result)
    draw.text((margin, 8), title, fill="#111111")
    for index, (label, image) in enumerate(images):
        column = index % columns
        row = index // columns
        x = column * cell_width + margin
        y = row * cell_height + 28 + label_height
        draw.rectangle(
            (x - 1, y - 1, x + image.width, y + image.height), outline="#888888"
        )
        result.paste(image, (x, y))
        draw.text((x, y - label_height + 4), label, fill="#111111")
    return result


def _save(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    print(path)


def _capture_one(transport: BinaryIO, event: str) -> CapturedFrame:
    transport.write(build_request(event))
    captured = read_frame(transport)
    expected = EVENTS[event]
    if captured.event != expected:
        raise CaptureError(
            f"応答イベントが一致しません: {captured.event} != {expected}"
        )
    if captured.status != 0:
        raise CaptureError(f"ファームウェアがイベントを描画できませんでした: {event}")
    return captured


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", help="デバッグファームを接続したCOMポート")
    parser.add_argument("--event", choices=STANDARD_EVENTS)
    parser.add_argument("--all", action="store_true", help="規定の全イベントを取得する")
    parser.add_argument("--raw", type=Path, help="1024-byteフレームを画像化する")
    parser.add_argument("--out", type=Path, default=Path("tmp/lcd-frame.png"))
    parser.add_argument("--scale", type=int, default=4)
    parser.add_argument("--lcd", choices=tuple(LCD_PALETTES), default="classic")
    parser.add_argument("--timeout", type=float, default=2.0)
    args = parser.parse_args(argv)

    if args.raw is not None:
        if args.port or args.event or args.all:
            parser.error("--rawは--port/--event/--allと併用できません")
        frame = LcdFrame.from_bytes(args.raw.read_bytes())
        _save(frame.image(args.scale, args.lcd), args.out)
        return 0

    if not args.port:
        parser.error("実機フレーム取得には--portが必要です")
    if bool(args.event) == args.all:
        parser.error("--eventまたは--allのどちらか一方を指定してください")

    try:
        import serial
    except ImportError as exc:
        raise SystemExit("pyserialが必要です。tools/host/requirements.txtを導入してください。") from exc

    with serial.Serial(args.port, BAUD_RATE, timeout=args.timeout,
                       write_timeout=args.timeout) as transport:
        if args.event:
            captured = _capture_one(transport, args.event)
            _save(captured.frame.image(args.scale, args.lcd), args.out)
        else:
            out_dir = args.out if args.out.suffix == "" else args.out.parent / "lcd-frames"
            contact_path = args.out if args.out.suffix else out_dir / "contact-sheet.png"
            images = []
            for event in STANDARD_EVENTS:
                captured = _capture_one(transport, event)
                image = captured.frame.image(args.scale, args.lcd)
                _save(image, out_dir / f"{event}.png")
                images.append((event, image))
            _save(make_contact_sheet(images, "K1 LCD debug firmware frames"), contact_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
