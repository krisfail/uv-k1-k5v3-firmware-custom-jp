import {
  JAPANESE_FONT_SIZE,
  JAPANESE_NAME_COUNT,
  JAPANESE_NAME_RECORD_SIZE,
  JAPANESE_NAME_SIZE,
} from "./protocol.mjs";

const encoder = new TextEncoder();
const decoder = new TextDecoder("utf-8", { fatal: true });
let manifestPromise;

const RESOURCE_PATHS = Object.freeze({
  manifest: [
    "./japanese_font_manifest.json",
    "../japanese_font_manifest.json",
    "../../tools/japanese_font_manifest.json",
  ],
  font: [
    "./japanese_font.bin",
    "../fonts/japanese_font.bin",
    "../../docs/fonts/japanese_font.bin",
  ],
});

async function fetchFirst(paths) {
  let lastError;
  for (const path of paths) {
    try {
      const response = await fetch(path, { cache: "no-store" });
      if (response.ok) return response;
      lastError = new Error(`${path}: HTTP ${response.status}`);
    } catch (error) {
      lastError = error;
    }
  }
  throw lastError ?? new Error("リソースを読み込めませんでした。");
}

export async function loadManifest() {
  if (!manifestPromise) {
    manifestPromise = fetchFirst(RESOURCE_PATHS.manifest)
      .then((response) => response.json());
  }
  return manifestPromise;
}

export async function loadBundledFont() {
  const bytes = new Uint8Array(await (await fetchFirst(RESOURCE_PATHS.font)).arrayBuffer());
  if (bytes.length !== JAPANESE_FONT_SIZE) {
    throw new Error(`同梱フォントのサイズが不正です（${bytes.length} byte）。`);
  }
  return bytes;
}

export async function loadCodepoints() {
  const manifest = await loadManifest();
  return new Set((manifest.codepoints ?? []).map((value) => Number(value)));
}

export function validateName(name, codepoints = new Set()) {
  const text = String(name);
  if (text.includes("\t") || text.includes("\r") || text.includes("\n")) {
    throw new Error("チャンネル名にタブまたは改行は使用できません。");
  }
  const encoded = encoder.encode(text);
  if (encoded.length > JAPANESE_NAME_RECORD_SIZE - 1) {
    throw new Error("チャンネル名はUTF-8で31 byte以内にしてください。");
  }
  let width = 0;
  for (const character of text) {
    const codepoint = character.codePointAt(0);
    if (codepoint < 0x20 || codepoint > 0x7E) {
      if (!codepoints.has(codepoint)) {
        throw new Error(`チャンネル名に未収録文字 U+${codepoint.toString(16).toUpperCase().padStart(4, "0")} があります。`);
      }
      width += 16;
    } else {
      width += 8;
    }
  }
  if (width > 95) throw new Error("チャンネル名がLCDの表示幅を超えています。");
  return encoded;
}

export function packNameLines(lines, codepoints = new Set()) {
  if (lines.length !== JAPANESE_NAME_COUNT) {
    throw new Error(`名前テーブルは${JAPANESE_NAME_COUNT}行で指定してください。`);
  }
  const table = new Uint8Array(JAPANESE_NAME_SIZE);
  lines.forEach((line, index) => {
    const encoded = validateName(line, codepoints);
    table.set(encoded, index * JAPANESE_NAME_RECORD_SIZE);
  });
  return table;
}

export function parseNameFile(text, codepoints = new Set()) {
  let normalized = String(text).replace(/^\uFEFF/, "");
  let lines = normalized.split(/\r\n?|\n/);
  if (lines.at(-1) === "") lines = lines.slice(0, -1);
  return { lines, table: packNameLines(lines, codepoints) };
}

export function unpackNameTable(data) {
  if (data.length !== JAPANESE_NAME_SIZE) {
    throw new Error("名前テーブルのサイズが不正です。");
  }
  const lines = [];
  for (let index = 0; index < JAPANESE_NAME_COUNT; index += 1) {
    const record = data.slice(index * JAPANESE_NAME_RECORD_SIZE,
      (index + 1) * JAPANESE_NAME_RECORD_SIZE);
    let end = record.findIndex((value) => value === 0 || value === 0xFF);
    if (end < 0) end = record.length;
    try {
      lines.push(decoder.decode(record.slice(0, end)));
    } catch {
      throw new Error(`名前テーブルの${index + 1}行目がUTF-8として不正です。`);
    }
  }
  return lines;
}

export function linesToText(lines) {
  return `${lines.join("\n")}\n`;
}

export function downloadBytes(bytes, filename, mime = "application/octet-stream") {
  const url = URL.createObjectURL(new Blob([bytes], { type: mime }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

export function downloadText(text, filename, mime = "text/plain;charset=utf-8") {
  downloadBytes(new TextEncoder().encode(text), filename, mime);
}
