/**
 * WRX-JP WebSerial protocol.
 *
 * The module contains the protocol and its write allowlist only.  It does not
 * know anything about the page or the browser UI.
 */

export const BAUD_RATE = 38400;
export const SESSION_TIMESTAMP = 0x6457396A;
export const MAX_BLOCK = 0x80;
export const WRITE_RETRIES = 3;

export const LOGICAL_MEMORY_END = 0xB200;
export const CALIBRATION_LOGICAL_BASE = 0xB000;
export const CALIBRATION_LOGICAL_END = 0xB200;
export const EXTERNAL_FLASH_SIZE = 0x200000;
export const CALIBRATION_FLASH_SECTOR_BASE = 0x010000;
export const CALIBRATION_FLASH_SECTOR_END = 0x011000;

export const JAPANESE_FONT_BASE = 0x020000;
export const JAPANESE_FONT_SIZE = 251208;
export const JAPANESE_FONT_END = JAPANESE_FONT_BASE + JAPANESE_FONT_SIZE;
export const JAPANESE_NAME_BASE = 0x060000;
export const JAPANESE_NAME_RECORD_SIZE = 32;
export const JAPANESE_NAME_COUNT = 1024;
export const JAPANESE_NAME_SIZE = JAPANESE_NAME_RECORD_SIZE * JAPANESE_NAME_COUNT;
export const JAPANESE_NAME_END = JAPANESE_NAME_BASE + JAPANESE_NAME_SIZE;

export const NORMAL_LOGICAL_WRITE_RANGES = Object.freeze([
  Object.freeze([0x0000, 0x8870]),
  Object.freeze([0x9000, 0x90E8]),
  Object.freeze([0xA000, 0xA170]),
]);

const XOR_TABLE = Object.freeze([
  22, 108, 20, 230, 46, 145, 13, 64,
  33, 53, 213, 64, 19, 3, 233, 128,
]);

export class HostToolError extends Error {}
export class ProtocolError extends HostToolError {}
export class SafetyError extends HostToolError {}

function concatBytes(...chunks) {
  const length = chunks.reduce((total, chunk) => total + chunk.length, 0);
  const result = new Uint8Array(length);
  let offset = 0;
  for (const chunk of chunks) {
    result.set(chunk, offset);
    offset += chunk.length;
  }
  return result;
}

function xorBytes(data) {
  const result = new Uint8Array(data.length);
  for (let index = 0; index < data.length; index += 1) {
    result[index] = data[index] ^ XOR_TABLE[index % XOR_TABLE.length];
  }
  return result;
}

export function crc16Xmodem(data) {
  let crc = 0;
  for (const byte of data) {
    crc ^= byte << 8;
    for (let bit = 0; bit < 8; bit += 1) {
      crc <<= 1;
      if (crc & 0x10000) crc = (crc ^ 0x1021) & 0xFFFF;
    }
  }
  return crc & 0xFFFF;
}

export function frameCommand(data) {
  if (!data.length || data.length > 0xFF) {
    throw new ProtocolError("command body must be 1..255 bytes");
  }
  const packet = new Uint8Array(data.length + 2);
  packet.set(data);
  const view = new DataView(packet.buffer);
  view.setUint16(data.length, crc16Xmodem(data), true);
  const encoded = xorBytes(packet);
  const result = new Uint8Array(4 + encoded.length + 2);
  const header = new DataView(result.buffer);
  header.setUint16(0, 0xABCD, false);
  header.setUint8(2, data.length);
  header.setUint8(3, 0);
  result.set(encoded, 4);
  result.set([0xDC, 0xBA], result.length - 2);
  return result;
}

function rangeContains(base, size, address, length) {
  return length >= 0 && address >= base && address - base <= size &&
    length <= size - (address - base);
}

function rangesOverlap(firstBase, firstEnd, secondBase, secondEnd) {
  return firstBase < secondEnd && secondBase < firstEnd;
}

export function validateLayout() {
  if (JAPANESE_NAME_END > EXTERNAL_FLASH_SIZE) {
    throw new SafetyError("日本語リソースが外部フラッシュ容量を超えています。");
  }
  if (rangesOverlap(JAPANESE_FONT_BASE, JAPANESE_FONT_END,
      CALIBRATION_FLASH_SECTOR_BASE, CALIBRATION_FLASH_SECTOR_END) ||
      rangesOverlap(JAPANESE_NAME_BASE, JAPANESE_NAME_END,
        CALIBRATION_FLASH_SECTOR_BASE, CALIBRATION_FLASH_SECTOR_END) ||
      rangesOverlap(JAPANESE_FONT_BASE, JAPANESE_FONT_END,
        JAPANESE_NAME_BASE, JAPANESE_NAME_END)) {
    throw new SafetyError("外部フラッシュの固定領域が重なっています。");
  }
}

export function validateLogicalRead(offset, length) {
  if (!Number.isInteger(offset) || !Number.isInteger(length) || offset < 0 ||
      length <= 0 || offset + length > LOGICAL_MEMORY_END) {
    throw new SafetyError("論理メモリーの読み出し範囲が不正です。");
  }
}

export function validateLogicalWrite(offset, length) {
  if (!Number.isInteger(offset) || !Number.isInteger(length) || offset < 0 ||
      length <= 0 || length % 8 !== 0) {
    throw new SafetyError("論理メモリーの書き込みは8 byte単位で指定してください。");
  }
  if (offset + length > LOGICAL_MEMORY_END) {
    throw new SafetyError("論理メモリーの書き込み範囲が上限を超えています。");
  }
  if (offset < CALIBRATION_LOGICAL_END &&
      CALIBRATION_LOGICAL_BASE < offset + length) {
    throw new SafetyError("calibration領域は読み出し専用です。");
  }
  if (!NORMAL_LOGICAL_WRITE_RANGES.some(([start, end]) =>
      start <= offset && offset + length <= end)) {
    throw new SafetyError("許可された通常メモリー領域以外へは書き込めません。");
  }
}

export function validateExternalResourceRange(address, length) {
  validateLayout();
  const inFont = rangeContains(JAPANESE_FONT_BASE, JAPANESE_FONT_SIZE, address, length);
  const inNames = rangeContains(JAPANESE_NAME_BASE, JAPANESE_NAME_SIZE, address, length);
  if (length <= 0 || (!inFont && !inNames)) {
    throw new SafetyError("日本語リソース以外の外部フラッシュへはアクセスできません。");
  }
  if (rangesOverlap(address, address + length,
      CALIBRATION_FLASH_SECTOR_BASE, CALIBRATION_FLASH_SECTOR_END)) {
    throw new SafetyError("calibration sectorへはアクセスできません。");
  }
}

function readU16(bytes, offset) {
  return new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength)
    .getUint16(offset, true);
}

function readU32(bytes, offset) {
  return new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength)
    .getUint32(offset, true);
}

function putU16(bytes, offset, value) {
  new DataView(bytes.buffer).setUint16(offset, value, true);
}

function putU32(bytes, offset, value) {
  new DataView(bytes.buffer).setUint32(offset, value, true);
}

function logicalReadCommand(address, size) {
  const body = new Uint8Array(12);
  putU16(body, 0, 0x051B);
  putU16(body, 2, 8);
  putU16(body, 4, address);
  body[6] = size;
  putU32(body, 8, SESSION_TIMESTAMP);
  return body;
}

function logicalWriteCommand(address, data) {
  const body = new Uint8Array(12 + data.length);
  putU16(body, 0, 0x051D);
  putU16(body, 2, data.length + 8);
  putU16(body, 4, address);
  body[6] = data.length;
  body[7] = 1;
  putU32(body, 8, SESSION_TIMESTAMP);
  body.set(data, 12);
  return body;
}

function externalReadCommand(address, size) {
  const body = new Uint8Array(16);
  putU16(body, 0, 0x0531);
  putU16(body, 2, 12);
  putU32(body, 4, address);
  body[8] = size;
  putU32(body, 12, SESSION_TIMESTAMP);
  return body;
}

function externalWriteCommand(address, data) {
  const body = new Uint8Array(16 + data.length);
  putU16(body, 0, 0x0533);
  putU16(body, 2, 12 + data.length);
  putU32(body, 4, address);
  body[8] = data.length;
  body[9] = 1;
  putU32(body, 12, SESSION_TIMESTAMP);
  body.set(data, 16);
  return body;
}

/** WebSerial adapter.  One RadioSession owns one reader and one writer. */
export class WebSerialTransport {
  constructor(port, timeoutMs = 2000) {
    this.port = port;
    this.timeoutMs = timeoutMs;
    this.reader = null;
    this.writer = null;
    this.readBuffer = new Uint8Array(0);
    this.closed = false;
  }

  async open() {
    if (!this.port) throw new ProtocolError("シリアルポートが選択されていません。");
    await this.port.open({ baudRate: BAUD_RATE });
    if (!this.port.readable || !this.port.writable) {
      await this.port.close().catch(() => {});
      throw new ProtocolError("シリアルポートの読み書きが利用できません。");
    }
    this.reader = this.port.readable.getReader();
    this.writer = this.port.writable.getWriter();
    this.closed = false;
  }

  async write(data) {
    if (!this.writer || this.closed) throw new ProtocolError("接続が閉じています。");
    await this.writer.write(data);
  }

  async _readWithTimeout() {
    if (!this.reader || this.closed) throw new ProtocolError("接続が閉じています。");
    let timer;
    try {
      return await Promise.race([
        this.reader.read(),
        new Promise((_, reject) => {
          timer = setTimeout(() => reject(new ProtocolError(
            "無線機からの応答がタイムアウトしました。")), this.timeoutMs);
        }),
      ]);
    } catch (error) {
      // A timed-out read keeps the Web Streams reader pending. Cancel it so
      // the failed session cannot leave the port locked for the next attempt.
      if (error instanceof ProtocolError && error.message.includes("タイムアウト")) {
        await this.reader?.cancel().catch(() => {});
        this.closed = true;
      }
      throw error;
    } finally {
      clearTimeout(timer);
    }
  }

  async readExact(length) {
    if (length === 0) return new Uint8Array(0);
    while (this.readBuffer.length < length) {
      const result = await this._readWithTimeout();
      if (result.done || !result.value) throw new ProtocolError("無線機からの応答が途中で終了しました。");
      this.readBuffer = concatBytes(this.readBuffer, result.value);
    }
    const result = this.readBuffer.slice(0, length);
    this.readBuffer = this.readBuffer.slice(length);
    return result;
  }

  async readFrameHeader() {
    let previous = -1;
    for (;;) {
      const byte = (await this.readExact(1))[0];
      if (previous === 0xAB && byte === 0xCD) {
        const rest = await this.readExact(2);
        return new Uint8Array([0xAB, 0xCD, rest[0], rest[1]]);
      }
      previous = byte;
    }
  }

  async close() {
    this.closed = true;
    if (this.reader) {
      await this.reader.cancel().catch(() => {});
      this.reader.releaseLock();
      this.reader = null;
    }
    if (this.writer) {
      await this.writer.close().catch(() => {});
      this.writer.releaseLock();
      this.writer = null;
    }
    if (this.port?.readable || this.port?.writable) {
      await this.port.close().catch(() => {});
    }
    this.readBuffer = new Uint8Array(0);
  }
}

export class RadioSession {
  constructor(transport) {
    this.transport = transport;
    this.firmware = "";
  }

  async exchange(body) {
    await this.transport.write(frameCommand(body));
    const header = await this.transport.readFrameHeader();
    if (header[3] !== 0) throw new ProtocolError("無線機の応答ヘッダーが不正です。");
    const response = await this.transport.readExact(header[2]);
    const footer = await this.transport.readExact(4);
    if (footer[2] !== 0xDC || footer[3] !== 0xBA) {
      throw new ProtocolError("無線機の応答終端が不正です。");
    }
    return xorBytes(response);
  }

  async connect() {
    const body = new Uint8Array(8);
    putU16(body, 0, 0x0514);
    putU16(body, 2, 4);
    putU32(body, 4, SESSION_TIMESTAMP);
    const reply = await this.exchange(body);
    if (reply.length >= 2 && readU16(reply, 0) === 0x0518) {
      throw new ProtocolError("無線機がプログラミングモードです。");
    }
    if (reply.length < 4) throw new ProtocolError("無線機の応答が短すぎます。");
    const versionBytes = reply.slice(4, 24);
    this.firmware = new TextDecoder("ascii").decode(versionBytes).split("\0", 1)[0];
    return this.firmware;
  }

  async probeExternalJapanese() {
    await this.readExternal(JAPANESE_FONT_BASE, 1);
  }

  async readMemory(offset, length, onProgress = () => {}) {
    validateLogicalRead(offset, length);
    const result = new Uint8Array(length);
    let cursor = 0;
    while (cursor < length) {
      const size = Math.min(MAX_BLOCK, length - cursor);
      const address = offset + cursor;
      const reply = await this.exchange(logicalReadCommand(address, size));
      if (reply.length !== 8 + size || readU16(reply, 0) !== 0x051C ||
          readU16(reply, 4) !== address || reply[6] !== size ||
          reply[7] !== 0) {
        throw new ProtocolError("論理メモリー読み出しの応答が不正です。");
      }
      result.set(reply.slice(8, 8 + size), cursor);
      cursor += size;
      onProgress({ completed: cursor, total: length, address });
    }
    return result;
  }

  async _writeMemoryOnce(address, data) {
    const reply = await this.exchange(logicalWriteCommand(address, data));
    if (reply.length < 6 || readU16(reply, 0) !== 0x051E ||
        readU16(reply, 4) !== address) {
      throw new ProtocolError("論理メモリー書き込みの応答が不正です。");
    }
  }

  async _writeMemoryBlock(address, block, verify) {
    let lastError = null;
    for (let attempt = 1; attempt <= WRITE_RETRIES; attempt += 1) {
      try {
        await this._writeMemoryOnce(address, block);
        if (!verify || bytesEqual(await this.readMemory(address, block.length), block)) return;
        lastError = new ProtocolError("論理メモリーのreadbackが一致しません。");
      } catch (error) {
        lastError = error;
      }
    }
    throw new ProtocolError(`論理メモリーの書き込みに失敗しました: 0x${hex(address, 4)}`,
      { cause: lastError });
  }

  async writeMemory(offset, data, verify = true, onProgress = () => {}) {
    const bytes = data instanceof Uint8Array ? data : new Uint8Array(data);
    validateLogicalWrite(offset, bytes.length);
    let completed = 0;
    for (let cursor = 0; cursor < bytes.length; cursor += MAX_BLOCK) {
      const block = bytes.slice(cursor, cursor + MAX_BLOCK);
      if (block.length % 8) throw new SafetyError("書き込みブロックが8 byte単位ではありません。");
      await this._writeMemoryBlock(offset + cursor, block, verify);
      completed += block.length;
      onProgress({ completed, total: bytes.length, address: offset + cursor });
    }
  }

  async writeMemoryChanged(offset, before, after, verify = true, onProgress = () => {}) {
    const oldBytes = before instanceof Uint8Array ? before : new Uint8Array(before);
    const newBytes = after instanceof Uint8Array ? after : new Uint8Array(after);
    if (oldBytes.length !== newBytes.length) throw new SafetyError("比較するメモリー長が一致しません。");
    validateLogicalWrite(offset, newBytes.length);
    const changed = changedBlockCount(oldBytes, newBytes);
    let completed = 0;
    for (let cursor = 0; cursor < newBytes.length; cursor += MAX_BLOCK) {
      const oldBlock = oldBytes.slice(cursor, cursor + MAX_BLOCK);
      const block = newBytes.slice(cursor, cursor + MAX_BLOCK);
      if (bytesEqual(oldBlock, block)) continue;
      await this._writeMemoryBlock(offset + cursor, block, verify);
      completed += 1;
      onProgress({ completed, total: changed, address: offset + cursor });
    }
  }

  async readExternal(address, length, onProgress = () => {}) {
    validateExternalResourceRange(address, length);
    const result = new Uint8Array(length);
    let cursor = 0;
    while (cursor < length) {
      const size = Math.min(MAX_BLOCK, length - cursor);
      const current = address + cursor;
      const reply = await this.exchange(externalReadCommand(current, size));
      if (reply.length !== 12 + size || readU16(reply, 0) !== 0x0532 ||
          readU32(reply, 4) !== current || reply[8] !== size) {
        throw new ProtocolError("外部フラッシュ読み出しの応答が不正です。");
      }
      result.set(reply.slice(12, 12 + size), cursor);
      cursor += size;
      onProgress({ completed: cursor, total: length, address: current });
    }
    return result;
  }

  async _writeExternalOnce(address, data) {
    const reply = await this.exchange(externalWriteCommand(address, data));
    if (reply.length < 12 || readU16(reply, 0) !== 0x0534 ||
        readU32(reply, 4) !== address || reply[8] !== data.length || reply[9] !== 0) {
      throw new ProtocolError("外部フラッシュ書き込みが拒否されました。");
    }
  }

  async _writeExternalBlock(address, block, verify) {
    let lastError = null;
    for (let attempt = 1; attempt <= WRITE_RETRIES; attempt += 1) {
      try {
        await this._writeExternalOnce(address, block);
        if (!verify || bytesEqual(await this.readExternal(address, block.length), block)) return;
        lastError = new ProtocolError("外部フラッシュのreadbackが一致しません。");
      } catch (error) {
        lastError = error;
      }
    }
    throw new ProtocolError(`外部フラッシュの書き込みに失敗しました: 0x${hex(address, 6)}`,
      { cause: lastError });
  }

  async writeExternalChanged(address, before, after, verify = true, onProgress = () => {}) {
    const oldBytes = before instanceof Uint8Array ? before : new Uint8Array(before);
    const newBytes = after instanceof Uint8Array ? after : new Uint8Array(after);
    if (oldBytes.length !== newBytes.length) throw new SafetyError("比較するリソース長が一致しません。");
    validateExternalResourceRange(address, newBytes.length);
    const changed = changedBlockCount(oldBytes, newBytes);
    let completed = 0;
    for (let cursor = 0; cursor < newBytes.length; cursor += MAX_BLOCK) {
      const oldBlock = oldBytes.slice(cursor, cursor + MAX_BLOCK);
      const block = newBytes.slice(cursor, cursor + MAX_BLOCK);
      if (bytesEqual(oldBlock, block)) continue;
      await this._writeExternalBlock(address + cursor, block, verify);
      completed += 1;
      onProgress({ completed, total: changed, address: address + cursor });
    }
  }

  async readExternalFont(onProgress) {
    return this.readExternal(JAPANESE_FONT_BASE, JAPANESE_FONT_SIZE, onProgress);
  }

  async readExternalNames(onProgress) {
    return this.readExternal(JAPANESE_NAME_BASE, JAPANESE_NAME_SIZE, onProgress);
  }

  async writeJapaneseFont(font, verify = true, onProgress) {
    if (font.length !== JAPANESE_FONT_SIZE) throw new SafetyError("フォントサイズが契約と一致しません。");
    const current = await this.readExternalFont();
    await this.writeExternalChanged(JAPANESE_FONT_BASE, current, font, verify, onProgress);
  }

  async writeJapaneseNames(names, verify = true, onProgress) {
    if (names.length !== JAPANESE_NAME_SIZE) throw new SafetyError("名前テーブルのサイズが契約と一致しません。");
    const current = await this.readExternalNames();
    await this.writeExternalChanged(JAPANESE_NAME_BASE, current, names, verify, onProgress);
  }

  async reset() {
    const body = new Uint8Array(4);
    putU16(body, 0, 0x05DD);
    await this.transport.write(frameCommand(body));
  }
}

export function bytesEqual(first, second) {
  if (first.length !== second.length) return false;
  for (let index = 0; index < first.length; index += 1) {
    if (first[index] !== second[index]) return false;
  }
  return true;
}

export function changedBlockCount(before, after) {
  let count = 0;
  for (let offset = 0; offset < after.length; offset += MAX_BLOCK) {
    if (!bytesEqual(before.slice(offset, offset + MAX_BLOCK),
        after.slice(offset, offset + MAX_BLOCK))) count += 1;
  }
  return count;
}

export function hex(value, width = 2) {
  return value.toString(16).toUpperCase().padStart(width, "0");
}

validateLayout();
