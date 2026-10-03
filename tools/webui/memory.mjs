import {
  CALIBRATION_LOGICAL_BASE,
  CALIBRATION_LOGICAL_END,
  LOGICAL_MEMORY_END,
  MAX_BLOCK,
  NORMAL_LOGICAL_WRITE_RANGES,
  bytesEqual,
} from "./protocol.mjs";

export const MEMORY_PRESETS = Object.freeze([
  Object.freeze({ id: "channels", label: "チャンネル領域", offset: 0x0000, length: 0x8870, writable: true }),
  Object.freeze({ id: "extended", label: "拡張設定", offset: 0x9000, length: 0x00E8, writable: true }),
  Object.freeze({ id: "settings", label: "設定領域", offset: 0xA000, length: 0x0170, writable: true }),
  Object.freeze({ id: "calibration", label: "calibration（読み出し専用）", offset: 0xB000, length: 0x0200, writable: false }),
]);

export function parseInteger(value, label = "値") {
  const text = String(value).trim();
  if (!text) throw new Error(`${label}を入力してください。`);
  const parsed = Number.parseInt(text, 0);
  if (!Number.isSafeInteger(parsed) || parsed < 0) throw new Error(`${label}が不正です。`);
  return parsed;
}

export function formatAddress(value, width = 4) {
  return `0x${value.toString(16).toUpperCase().padStart(width, "0")}`;
}

export function bytesToHex(bytes, bytesPerLine = 16) {
  const lines = [];
  for (let offset = 0; offset < bytes.length; offset += bytesPerLine) {
    const line = Array.from(bytes.slice(offset, offset + bytesPerLine),
      (value) => value.toString(16).toUpperCase().padStart(2, "0"));
    lines.push(line.join(" "));
  }
  return lines.join("\n");
}

function parseHexLine(line, lineNumber) {
  let text = line.replace(/\/\/.*$/, "").replace(/#.*$/, "").trim();
  if (!text) return [];
  const addressPrefix = text.match(/^(?:0x)?[0-9a-f]{4,8}\s*[:|]\s*(.*)$/i);
  if (addressPrefix) text = addressPrefix[1];
  text = text.replace(/0x/gi, "").replace(/[\s,;]+/g, "");
  if (!/^[0-9a-f]*$/i.test(text) || text.length % 2 !== 0) {
    throw new Error(`16進数エディターの${lineNumber}行目が不正です。`);
  }
  return text ? text.match(/[0-9a-f]{2}/gi).map((value) => Number.parseInt(value, 16)) : [];
}

export function hexToBytes(text) {
  const values = [];
  String(text).split(/\r\n?|\n/).forEach((line, index) => {
    values.push(...parseHexLine(line, index + 1));
  });
  return new Uint8Array(values);
}

export function changedByteCount(before, after) {
  let count = 0;
  for (let index = 0; index < after.length; index += 1) {
    if (before[index] !== after[index]) count += 1;
  }
  return count;
}

export function changedBlocks(before, after, blockSize = MAX_BLOCK) {
  const blocks = [];
  for (let offset = 0; offset < after.length; offset += blockSize) {
    const oldBlock = before.slice(offset, offset + blockSize);
    const newBlock = after.slice(offset, offset + blockSize);
    if (!bytesEqual(oldBlock, newBlock)) blocks.push(offset);
  }
  return blocks;
}

export function diffSummary(before, after, base = 0) {
  const blocks = changedBlocks(before, after);
  return {
    bytes: changedByteCount(before, after),
    blocks: blocks.length,
    firstAddresses: blocks.slice(0, 6).map((offset) => formatAddress(base + offset, 6)),
  };
}

export function isWritableRange(offset, length) {
  if (!Number.isInteger(offset) || !Number.isInteger(length) || length <= 0) return false;
  if (offset < CALIBRATION_LOGICAL_END && CALIBRATION_LOGICAL_BASE < offset + length) return false;
  return NORMAL_LOGICAL_WRITE_RANGES.some(([start, end]) =>
    start <= offset && offset + length <= end);
}

export function validateMemoryEditorRange(offset, length, forWrite = false) {
  if (offset + length > LOGICAL_MEMORY_END) {
    throw new Error(`論理メモリーは${formatAddress(LOGICAL_MEMORY_END, 4)}未満で指定してください。`);
  }
  if (forWrite && !isWritableRange(offset, length)) {
    throw new Error("この範囲は安全上の理由で書き込めません。");
  }
}
