"""Minimal, safety-bounded UART protocol for the K1/K5 V3 host tool.

This module deliberately exposes only the protocol operations needed by the
dedicated tool.  In particular, calibration can be read for diagnostics but
there is no host-tool write path for it.
"""

from __future__ import annotations

import struct
from typing import BinaryIO


BAUD_RATE = 38400
SESSION_TIMESTAMP = 0x6457396A
MAX_BLOCK = 0x80
WRITE_RETRIES = 3

LOGICAL_MEMORY_END = 0xB200
CALIBRATION_LOGICAL_BASE = 0xB000
CALIBRATION_LOGICAL_END = 0xB200
EXTERNAL_FLASH_SIZE = 0x200000
CALIBRATION_FLASH_SECTOR_BASE = 0x010000
CALIBRATION_FLASH_SECTOR_END = 0x011000

JAPANESE_FONT_BASE = 0x020000
JAPANESE_FONT_SIZE = 125604
JAPANESE_FONT_END = JAPANESE_FONT_BASE + JAPANESE_FONT_SIZE
JAPANESE_NAME_BASE = 0x040000
JAPANESE_NAME_RECORD_SIZE = 32
JAPANESE_NAME_COUNT = 1024
JAPANESE_NAME_SIZE = JAPANESE_NAME_RECORD_SIZE * JAPANESE_NAME_COUNT
JAPANESE_NAME_END = JAPANESE_NAME_BASE + JAPANESE_NAME_SIZE

# These are the normal logical upload areas from the K1/K5 V3 profile.  The
# first end includes the two-byte rounded CHIRP boundary; it is still far
# below the calibration window and is retained for compatibility.
NORMAL_LOGICAL_WRITE_RANGES = (
    (0x0000, 0x8870),
    (0x9000, 0x90E8),
    (0xA000, 0xA170),
)


class HostToolError(Exception):
    """Base class for actionable host-tool errors."""


class ProtocolError(HostToolError):
    """The radio returned a malformed or unexpected protocol frame."""


class SafetyError(HostToolError):
    """An operation falls outside the host tool's fixed write contract."""


def _xorarr(data: bytes) -> bytes:
    table = (22, 108, 20, 230, 46, 145, 13, 64,
             33, 53, 213, 64, 19, 3, 233, 128)
    return bytes(byte ^ table[index % len(table)]
                 for index, byte in enumerate(data))


def crc16_xmodem(data: bytes) -> int:
    crc = 0
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc <<= 1
            if crc & 0x10000:
                crc = (crc ^ 0x1021) & 0xFFFF
    return crc & 0xFFFF


def frame_command(data: bytes) -> bytes:
    """Build the same framed command used by the firmware UART handler."""
    if not data or len(data) > 0xFF:
        raise ProtocolError("command body must be 1..255 bytes")
    packet = data + struct.pack("<H", crc16_xmodem(data))
    return (struct.pack(">HBB", 0xABCD, len(data), 0) +
            _xorarr(packet) + b"\xDC\xBA")


def _range_contains(base: int, size: int, address: int, length: int) -> bool:
    return (length >= 0 and address >= base and address - base <= size and
            length <= size - (address - base))


def _ranges_overlap(first_base: int, first_end: int,
                    second_base: int, second_end: int) -> bool:
    return first_base < second_end and second_base < first_end


def validate_layout() -> None:
    """Fail closed if fixed host constants ever overlap."""
    if JAPANESE_NAME_END > EXTERNAL_FLASH_SIZE:
        raise SafetyError("Japanese resources exceed the external flash")
    if _ranges_overlap(JAPANESE_FONT_BASE, JAPANESE_FONT_END,
                       CALIBRATION_FLASH_SECTOR_BASE,
                       CALIBRATION_FLASH_SECTOR_END):
        raise SafetyError("Japanese font overlaps the calibration sector")
    if _ranges_overlap(JAPANESE_NAME_BASE, JAPANESE_NAME_END,
                       CALIBRATION_FLASH_SECTOR_BASE,
                       CALIBRATION_FLASH_SECTOR_END):
        raise SafetyError("Japanese name table overlaps the calibration sector")
    if _ranges_overlap(JAPANESE_FONT_BASE, JAPANESE_FONT_END,
                       JAPANESE_NAME_BASE, JAPANESE_NAME_END):
        raise SafetyError("Japanese font overlaps the name table")


def validate_logical_read(offset: int, length: int) -> None:
    if offset < 0 or length <= 0 or offset + length > LOGICAL_MEMORY_END:
        raise SafetyError("logical read is outside the K1 memory window")


def validate_logical_write(offset: int, length: int) -> None:
    if offset < 0 or length <= 0 or length % 8:
        raise SafetyError("logical writes must be a non-empty 8-byte multiple")
    if offset + length > LOGICAL_MEMORY_END:
        raise SafetyError("logical write is outside the K1 memory window")
    if (offset < CALIBRATION_LOGICAL_END and
            CALIBRATION_LOGICAL_BASE < offset + length):
        raise SafetyError("calibration is read-only in the host tool")
    if not any(start <= offset and offset + length <= end
               for start, end in NORMAL_LOGICAL_WRITE_RANGES):
        raise SafetyError("logical write is outside a supported normal range")


def validate_external_resource_range(address: int, length: int) -> None:
    validate_layout()
    if length <= 0:
        raise SafetyError("external write must be non-empty")
    in_font = _range_contains(JAPANESE_FONT_BASE, JAPANESE_FONT_SIZE,
                              address, length)
    in_names = _range_contains(JAPANESE_NAME_BASE, JAPANESE_NAME_SIZE,
                               address, length)
    if not (in_font or in_names):
        raise SafetyError("external address is outside the Japanese resources")
    if _ranges_overlap(address, address + length,
                       CALIBRATION_FLASH_SECTOR_BASE,
                       CALIBRATION_FLASH_SECTOR_END):
        raise SafetyError("external write overlaps the calibration sector")


def _read_exact(transport: BinaryIO, length: int) -> bytes:
    data = transport.read(length)
    if data is None or len(data) != length:
        raise ProtocolError("short read from radio")
    return data


class RadioSession:
    """Synchronous session over a pyserial-compatible transport."""

    def __init__(self, transport: BinaryIO, timeout: float = 0.5):
        self.transport = transport
        if hasattr(transport, "timeout"):
            transport.timeout = timeout
        self.firmware = ""

    def _exchange(self, body: bytes) -> bytes:
        try:
            self.transport.write(frame_command(body))
            header = _read_exact(self.transport, 4)
            if header[:2] != b"\xAB\xCD" or header[3] != 0:
                raise ProtocolError("bad response header")
            response = _read_exact(self.transport, header[2])
            footer = _read_exact(self.transport, 4)
        except HostToolError:
            raise
        except Exception as exc:
            raise ProtocolError("radio communication failed") from exc
        if footer[2:] != b"\xDC\xBA":
            raise ProtocolError("bad response footer")
        return _xorarr(response)

    def connect(self) -> str:
        reply = self._exchange(
            struct.pack("<HHI", 0x0514, 4, SESSION_TIMESTAMP))
        if len(reply) >= 2 and struct.unpack_from("<H", reply, 0)[0] == 0x0518:
            raise ProtocolError("radio is in programming mode")
        if len(reply) < 4:
            raise ProtocolError("radio hello response is too short")
        raw = reply[4:24].split(b"\x00", 1)[0]
        self.firmware = raw.decode("ascii", errors="replace")
        return self.firmware

    def probe_external_japanese(self) -> None:
        """Verify the WRX-JP external-flash command before any write."""
        self.read_external(JAPANESE_FONT_BASE, 1)

    def read_external_names(self) -> bytes:
        return self.read_external(JAPANESE_NAME_BASE, JAPANESE_NAME_SIZE)

    def read_memory(self, offset: int, length: int) -> bytes:
        validate_logical_read(offset, length)
        result = bytearray()
        cursor = 0
        while cursor < length:
            size = min(MAX_BLOCK, length - cursor)
            address = offset + cursor
            reply = self._exchange(struct.pack(
                "<HHHBBI", 0x051B, 8, address, size, 0,
                SESSION_TIMESTAMP))
            if (len(reply) < 8 or
                    struct.unpack_from("<H", reply, 0)[0] != 0x051C or
                    struct.unpack_from("<H", reply, 4)[0] != address or
                    reply[6] != size or len(reply[8:]) != size):
                raise ProtocolError("bad logical memory read response")
            result.extend(reply[8:])
            cursor += size
        return bytes(result)

    def _write_memory_once(self, offset: int, data: bytes) -> None:
        reply = self._exchange(struct.pack(
            "<HHHBBI", 0x051D, len(data) + 8, offset, len(data), 1,
            SESSION_TIMESTAMP) + data)
        if (len(reply) < 6 or
                struct.unpack_from("<H", reply, 0)[0] != 0x051E or
                struct.unpack_from("<H", reply, 4)[0] != offset):
            raise ProtocolError("bad logical memory write response")

    def write_memory(self, offset: int, data: bytes,
                     verify: bool = True) -> None:
        validate_logical_write(offset, len(data))
        for cursor in range(0, len(data), MAX_BLOCK):
            block = data[cursor:cursor + MAX_BLOCK]
            if len(block) % 8:
                raise SafetyError("logical write block is not 8-byte aligned")
            address = offset + cursor
            last_error: Exception | None = None
            for _ in range(WRITE_RETRIES):
                try:
                    self._write_memory_once(address, block)
                    if not verify or self.read_memory(address, len(block)) == block:
                        last_error = None
                        break
                    last_error = ProtocolError("logical memory readback mismatch")
                except (HostToolError, OSError) as exc:
                    last_error = exc
            if last_error is not None:
                raise ProtocolError(
                    "logical memory write failed at 0x{:04X}".format(address)
                ) from last_error

    def write_memory_changed(self, offset: int, before: bytes, after: bytes,
                             verify: bool = True) -> None:
        """Write only changed blocks inside one already-approved range."""
        if len(before) != len(after):
            raise SafetyError("changed logical images must have equal sizes")
        validate_logical_write(offset, len(after))
        for cursor in range(0, len(after), MAX_BLOCK):
            old_block = before[cursor:cursor + MAX_BLOCK]
            block = after[cursor:cursor + MAX_BLOCK]
            if old_block == block:
                continue
            if len(block) % 8:
                raise SafetyError("logical write block is not 8-byte aligned")
            address = offset + cursor
            last_error: Exception | None = None
            for _ in range(WRITE_RETRIES):
                try:
                    self._write_memory_once(address, block)
                    if not verify or self.read_memory(address, len(block)) == block:
                        last_error = None
                        break
                    last_error = ProtocolError("logical memory readback mismatch")
                except (HostToolError, OSError) as exc:
                    last_error = exc
            if last_error is not None:
                raise ProtocolError(
                    "logical memory write failed at 0x{:04X}".format(address)
                ) from last_error

    def read_external(self, address: int, length: int) -> bytes:
        validate_external_resource_range(address, length)
        result = bytearray()
        cursor = 0
        while cursor < length:
            size = min(MAX_BLOCK, length - cursor)
            current = address + cursor
            reply = self._exchange(struct.pack(
                "<HHIB3xI", 0x0531, 12, current, size,
                SESSION_TIMESTAMP))
            if (len(reply) < 12 + size or
                    struct.unpack_from("<H", reply, 0)[0] != 0x0532 or
                    struct.unpack_from("<I", reply, 4)[0] != current or
                    reply[8] != size):
                raise ProtocolError("bad external flash read response")
            result.extend(reply[12:12 + size])
            cursor += size
        return bytes(result)

    def _write_external_once(self, address: int, data: bytes) -> None:
        reply = self._exchange(struct.pack(
            "<HHIBBHI", 0x0533, 12 + len(data), address, len(data),
            1, 0, SESSION_TIMESTAMP) + data)
        if (len(reply) < 12 or
                struct.unpack_from("<H", reply, 0)[0] != 0x0534 or
                struct.unpack_from("<I", reply, 4)[0] != address or
                reply[8] != len(data) or reply[9] != 0):
            raise ProtocolError("external flash write was rejected")

    def write_external(self, address: int, data: bytes,
                       verify: bool = True) -> None:
        validate_external_resource_range(address, len(data))
        for cursor in range(0, len(data), MAX_BLOCK):
            block = data[cursor:cursor + MAX_BLOCK]
            current = address + cursor
            last_error: Exception | None = None
            for _ in range(WRITE_RETRIES):
                try:
                    self._write_external_once(current, block)
                    if not verify or self.read_external(current, len(block)) == block:
                        last_error = None
                        break
                    last_error = ProtocolError("external flash readback mismatch")
                except (HostToolError, OSError) as exc:
                    last_error = exc
            if last_error is not None:
                raise ProtocolError(
                    "external resource write failed at 0x{:06X}".format(current)
                ) from last_error

    def write_external_changed(self, address: int, before: bytes,
                               after: bytes, verify: bool = True) -> None:
        """Write only changed blocks inside one Japanese resource range."""
        if len(before) != len(after):
            raise SafetyError("changed external images must have equal sizes")
        validate_external_resource_range(address, len(after))
        for cursor in range(0, len(after), MAX_BLOCK):
            old_block = before[cursor:cursor + MAX_BLOCK]
            block = after[cursor:cursor + MAX_BLOCK]
            if old_block == block:
                continue
            current = address + cursor
            last_error: Exception | None = None
            for _ in range(WRITE_RETRIES):
                try:
                    self._write_external_once(current, block)
                    if not verify or self.read_external(current, len(block)) == block:
                        last_error = None
                        break
                    last_error = ProtocolError("external flash readback mismatch")
                except (HostToolError, OSError) as exc:
                    last_error = exc
            if last_error is not None:
                raise ProtocolError(
                    "external resource write failed at 0x{:06X}".format(current)
                ) from last_error

    def write_japanese_resource(self, font_data: bytes,
                                name_table: bytes) -> None:
        if len(font_data) != JAPANESE_FONT_SIZE:
            raise SafetyError("Japanese font has an unexpected size")
        if len(name_table) != JAPANESE_NAME_SIZE:
            raise SafetyError("Japanese name table must contain 1024 records")
        # Validate both complete ranges before the first write.  The operation
        # is presented as one GUI action, but the two fixed ranges are checked
        # and transferred independently.
        validate_external_resource_range(JAPANESE_FONT_BASE, len(font_data))
        validate_external_resource_range(JAPANESE_NAME_BASE, len(name_table))
        current_font = self.read_external(JAPANESE_FONT_BASE, len(font_data))
        if current_font != font_data:
            self.write_external_changed(JAPANESE_FONT_BASE, current_font, font_data)
        current_names = self.read_external(JAPANESE_NAME_BASE, len(name_table))
        if current_names != name_table:
            self.write_external_changed(JAPANESE_NAME_BASE, current_names, name_table)

    def reset(self) -> None:
        try:
            self.transport.write(frame_command(struct.pack("<HH", 0x05DD, 0)))
        except Exception as exc:
            raise ProtocolError("radio reset command failed") from exc


validate_layout()
