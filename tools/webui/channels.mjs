import { JAPANESE_NAME_RECORD_SIZE, JAPANESE_NAME_SIZE } from "./protocol.mjs";
import { validateName } from "./resources.mjs";

export const CHANNEL_COUNT = 1024;
export const CHANNEL_RECORD_SIZE = 16;
export const CHANNEL_IMAGE_SIZE = 0x8870;
export const CHANNEL_NAME_BASE = 0x4000;
export const CHANNEL_ATTRIBUTE_BASE = 0x8000;

export const STEPS = Object.freeze([
  2.5, 5, 6.25, 10, 12.5, 25, 8.33, 0.01, 0.05, 0.1, 0.25, 0.5,
  1, 1.25, 9, 15, 20, 30, 50, 100, 125, 200, 250, 500,
]);
export const CTCSS_TONES = Object.freeze([
  67.0, 69.3, 71.9, 74.4, 77.0, 79.7, 82.5, 85.4, 88.5, 91.5,
  94.8, 97.4, 100.0, 103.5, 107.2, 110.9, 114.8, 118.8, 123.0,
  127.3, 131.8, 136.5, 141.3, 146.2, 151.4, 156.7, 159.8, 162.2,
  165.5, 167.9, 171.3, 173.8, 177.3, 179.9, 183.5, 186.2, 189.9,
  192.8, 196.6, 199.5, 203.5, 206.5, 210.7, 218.1, 225.7, 229.1,
  233.6, 241.8, 250.3, 254.1,
]);
export const DTCS_CODES = Object.freeze([
  23, 25, 26, 31, 32, 36, 43, 47, 51, 53, 54, 65, 71, 72, 73, 74,
  114, 115, 116, 122, 125, 131, 132, 134, 143, 145, 152, 155, 156,
  162, 165, 172, 174, 205, 212, 223, 225, 226, 243, 244, 245, 246,
  251, 252, 255, 261, 263, 265, 266, 271, 274, 306, 311, 315, 325,
  331, 332, 343, 346, 351, 356, 364, 365, 371, 411, 412, 413, 423,
  431, 432, 445, 446, 452, 454, 455, 462, 464, 465, 466, 503, 506,
  516, 523, 526, 532, 546, 565, 606, 612, 624, 627, 631, 632, 654,
  662, 664, 703, 712, 723, 731, 732, 734, 743, 754,
]);
export const MODES = Object.freeze(["FM", "NFM", "AM", "NAM", "USB"]);
export const TONE_MODES = Object.freeze(["", "Tone", "TSQL", "DTCS"]);
export const FIELDNAMES_V1 = Object.freeze([
  "channel", "frequency_hz", "mode", "tone_mode", "tone", "dtcs",
  "dtcs_polarity", "tuning_step_khz", "scan_lists", "name",
]);
export const FIELDNAMES_V2 = Object.freeze([...FIELDNAMES_V1.slice(0, -1), "name", "ascii_name"]);

const decoder = new TextDecoder("utf-8");
const asciiDecoder = new TextDecoder("ascii");
const encoder = new TextEncoder();

function readU16(bytes, offset) {
  return new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength).getUint16(offset, true);
}

function readU32(bytes, offset) {
  return new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength).getUint32(offset, true);
}

function writeU16(bytes, offset, value) {
  new DataView(bytes.buffer).setUint16(offset, value, true);
}

function writeU32(bytes, offset, value) {
  new DataView(bytes.buffer).setUint32(offset, value, true);
}

function fixedText(bytes, decoderToUse = decoder) {
  let end = bytes.findIndex((value) => value === 0 || value === 0xFF);
  if (end < 0) end = bytes.length;
  return decoderToUse.decode(bytes.slice(0, end));
}

function decodeMode(raw) {
  const index = ((raw[11] >> 4) & 0x0F) * 2 + ((raw[12] >> 1) & 1);
  return MODES[index] ?? "FM";
}

function decodeTone(raw) {
  const flag = raw[10] & 0x0F;
  const code = raw[8];
  if (flag === 1 && code < CTCSS_TONES.length) {
    return { toneMode: "Tone", tone: CTCSS_TONES[code], dtcs: null, polarity: "N" };
  }
  if ((flag === 2 || flag === 3) && code < DTCS_CODES.length) {
    return { toneMode: "DTCS", tone: null, dtcs: DTCS_CODES[code], polarity: flag === 3 ? "R" : "N" };
  }
  return { toneMode: "", tone: null, dtcs: null, polarity: "N" };
}

export function emptyChannel(channel) {
  return {
    channel,
    frequencyHz: null,
    mode: "FM",
    toneMode: "",
    tone: null,
    dtcs: null,
    polarity: "N",
    tuningStepKhz: 12.5,
    scanLists: 0,
    name: "",
    asciiName: "",
  };
}

export function decodeChannelList(image, nameTable) {
  if (image.length !== CHANNEL_IMAGE_SIZE) throw new Error("チャンネル領域のサイズが不正です。");
  if (nameTable.length !== JAPANESE_NAME_SIZE) throw new Error("名前テーブルのサイズが不正です。");
  const rows = [];
  for (let index = 0; index < CHANNEL_COUNT; index += 1) {
    const offset = index * CHANNEL_RECORD_SIZE;
    const raw = image.slice(offset, offset + CHANNEL_RECORD_SIZE);
    const storedFrequency = readU32(raw, 0);
    const frequencyHz = storedFrequency === 0 || storedFrequency === 0xFFFFFFFF
      ? null : storedFrequency * 10;
    const tone = decodeTone(raw);
    const attrOffset = CHANNEL_ATTRIBUTE_BASE + index * 2;
    const scanLists = readU16(image, attrOffset) >> 8;
    const externalName = fixedText(nameTable.slice(
      index * JAPANESE_NAME_RECORD_SIZE, (index + 1) * JAPANESE_NAME_RECORD_SIZE));
    const storedAsciiName = fixedText(image.slice(
      CHANNEL_NAME_BASE + index * 16, CHANNEL_NAME_BASE + (index + 1) * 16), asciiDecoder);
    const hasFrequency = frequencyHz !== null;
    rows.push({
      channel: index + 1,
      frequencyHz: hasFrequency ? frequencyHz : null,
      mode: decodeMode(raw),
      toneMode: tone.toneMode,
      tone: tone.tone,
      dtcs: tone.dtcs,
      polarity: tone.polarity,
      tuningStepKhz: STEPS[raw[14]] ?? 12.5,
      scanLists,
      name: hasFrequency ? (externalName || storedAsciiName) : "",
      asciiName: hasFrequency && externalName ? storedAsciiName : "",
    });
  }
  return rows;
}

function parseOptionalInt(value, label) {
  const text = String(value ?? "").trim();
  if (!text) return null;
  if (!/^[+-]?\d+$/.test(text)) throw new Error(`${label}は整数で指定してください。`);
  return Number.parseInt(text, 10);
}

function parseOptionalFloat(value, label) {
  const text = String(value ?? "").trim();
  if (!text) return null;
  const result = Number.parseFloat(text);
  if (!Number.isFinite(result)) throw new Error(`${label}は数値で指定してください。`);
  return result;
}

function parseRow(fields, fieldnames, expectedChannel) {
  if (fields.length !== fieldnames.length) throw new Error(`${expectedChannel}行目の列数が不正です。`);
  const row = Object.fromEntries(fieldnames.map((key, index) => [key, fields[index]]));
  const channel = parseOptionalInt(row.channel, "channel");
  if (channel !== expectedChannel) throw new Error("チャンネル番号は1から1024まで連番で指定してください。");
  const frequencyHz = parseOptionalInt(row.frequency_hz, "frequency_hz");
  const mode = (row.mode || "FM").trim().toUpperCase();
  const toneMode = (row.tone_mode || "").trim();
  if (!MODES.includes(mode)) throw new Error(`${channel}番のmodeが不正です。`);
  if (!TONE_MODES.includes(toneMode)) throw new Error(`${channel}番のtone_modeが不正です。`);
  const tone = parseOptionalFloat(row.tone, "tone");
  const dtcs = parseOptionalInt(row.dtcs, "dtcs");
  const polarity = (row.dtcs_polarity || "N").trim().toUpperCase() || "N";
  if (!["N", "R"].includes(polarity)) throw new Error(`${channel}番のDTCS極性が不正です。`);
  const tuningStepKhz = parseOptionalFloat(row.tuning_step_khz || "12.5", "tuning_step_khz") ?? 12.5;
  if (!STEPS.some((step) => Math.abs(step - tuningStepKhz) < 1e-6)) throw new Error(`${channel}番のステップが不正です。`);
  const scanLists = parseOptionalInt(row.scan_lists || "0", "scan_lists") ?? 0;
  if (scanLists < 0 || scanLists > 0xFF) throw new Error(`${channel}番のscan_listsは0〜255で指定してください。`);
  if ((row.name ?? "").includes("\t") || (row.name ?? "").includes("\n")) throw new Error(`${channel}番の名前に改行があります。`);
  if ((row.ascii_name ?? "").includes("\t") || (row.ascii_name ?? "").includes("\n")) throw new Error(`${channel}番のASCII名に改行があります。`);
  return { channel, frequencyHz, mode, toneMode, tone, dtcs, polarity, tuningStepKhz, scanLists,
    name: row.name ?? "", asciiName: row.ascii_name ?? "" };
}

export function parseChannelList(text) {
  const lines = String(text).replace(/^\uFEFF/, "").split(/\r\n?|\n/)
    .filter((line) => line.trim() && !line.trimStart().startsWith("#"));
  if (!lines.length) throw new Error("チャンネル一覧が空です。");
  const fieldnames = lines[0].split("\t");
  const v1 = fieldnames.join("\t") === FIELDNAMES_V1.join("\t");
  const v2 = fieldnames.join("\t") === FIELDNAMES_V2.join("\t");
  if (!v1 && !v2) throw new Error("WRX-JP channel list v1/v2のヘッダーではありません。");
  const rows = lines.slice(1).map((line) => line.split("\t"));
  if (rows.length !== CHANNEL_COUNT) throw new Error("チャンネル一覧は1024行で指定してください。");
  return rows.map((fields, index) => {
    const row = parseRow(fields, v2 ? FIELDNAMES_V2 : FIELDNAMES_V1, index + 1);
    if (v1 && /^[\x00-\x7F]*$/.test(row.name)) row.asciiName = row.name;
    return row;
  });
}

function formatNumber(value) {
  return value === null || value === undefined ? "" : String(value);
}

export function formatChannelList(rows) {
  if (rows.length !== CHANNEL_COUNT) throw new Error("チャンネル一覧は1024行で指定してください。");
  const output = ["# WRX-JP channel list v2", FIELDNAMES_V2.join("\t")];
  for (const row of rows) {
    output.push([
      row.channel, formatNumber(row.frequencyHz), row.mode, row.toneMode,
      formatNumber(row.tone === null ? "" : Number(row.tone).toFixed(1)),
      formatNumber(row.dtcs), row.polarity, formatNumber(row.tuningStepKhz),
      row.scanLists, row.name, row.asciiName,
    ].join("\t"));
  }
  return `${output.join("\n")}\n`;
}

function encodeTone(row, raw) {
  let flag = 0;
  let code = 0;
  if (row.toneMode === "Tone" || row.toneMode === "TSQL") {
    if (row.tone === null || row.tone === undefined) throw new Error(`${row.channel}番のCTCSS toneが未指定です。`);
    code = CTCSS_TONES.findIndex((value) => Math.abs(value - Number(row.tone)) < 1e-6);
    if (code < 0) throw new Error(`${row.channel}番のCTCSS toneが未対応です。`);
    flag = 1;
  } else if (row.toneMode === "DTCS") {
    code = DTCS_CODES.indexOf(Number(row.dtcs));
    if (code < 0) throw new Error(`${row.channel}番のDTCS codeが未対応です。`);
    flag = row.polarity === "R" ? 3 : 2;
  }
  raw[8] = code;
  raw[9] = 0;
  raw[10] = (raw[10] & 0xF0) | flag;
}

function nearestStep(value) {
  let best = 0;
  let distance = Infinity;
  STEPS.forEach((step, index) => {
    if (Math.abs(step - value) < distance) {
      best = index;
      distance = Math.abs(step - value);
    }
  });
  return best;
}

export function encodeChannelList(rows, image, nameTable, codepoints = new Set()) {
  if (rows.length !== CHANNEL_COUNT) throw new Error("チャンネル一覧は1024行で指定してください。");
  if (image.length !== CHANNEL_IMAGE_SIZE) throw new Error("チャンネル領域のサイズが不正です。");
  if (nameTable.length !== JAPANESE_NAME_SIZE) throw new Error("名前テーブルのサイズが不正です。");
  const updated = new Uint8Array(image);
  const updatedNames = new Uint8Array(nameTable);
  rows.forEach((row, index) => {
    if (row.channel !== index + 1) throw new Error("チャンネル番号は連番で指定してください。");
    const recordOffset = index * CHANNEL_RECORD_SIZE;
    const nameOffset = CHANNEL_NAME_BASE + index * 16;
    const externalOffset = index * JAPANESE_NAME_RECORD_SIZE;
    if (row.frequencyHz === null || row.frequencyHz === undefined || row.frequencyHz === "") {
      updated.fill(0xFF, recordOffset, recordOffset + 16);
      updated.fill(0, nameOffset, nameOffset + 16);
      updatedNames.fill(0, externalOffset, externalOffset + 32);
    } else {
      const frequency = Number(row.frequencyHz);
      if (!Number.isSafeInteger(frequency) || frequency <= 0 || frequency % 10 !== 0) {
        throw new Error(`${row.channel}番の周波数は10 Hz単位の正数で指定してください。`);
      }
      const stored = frequency / 10;
      if (stored > 0xFFFFFFFF) throw new Error(`${row.channel}番の周波数が大きすぎます。`);
      const raw = updated.slice(recordOffset, recordOffset + 16);
      writeU32(raw, 0, stored);
      raw.fill(0, 4, 8);
      const modeIndex = { FM: 0, NFM: 1, AM: 2, NAM: 3, USB: 5 }[row.mode];
      raw[11] = (raw[11] & 0x0F) | ((modeIndex >> 1) << 4);
      raw[12] = (raw[12] & 0xFD) | ((modeIndex & 1) << 1) | 0x40;
      encodeTone(row, raw);
      raw[14] = nearestStep(Number(row.tuningStepKhz));
      updated.set(raw, recordOffset);

      const encodedName = validateName(row.name ?? "", codepoints);
      const isJapanese = [...(row.name ?? "")].some((character) => character.codePointAt(0) > 0x7E);
      if (isJapanese) {
        const alias = encoder.encode(row.asciiName ?? "");
        if (alias.length > 10 || [...alias].some((value) => value < 0x20 || value > 0x7E)) {
          throw new Error(`${row.channel}番のASCII別名は印字可能な10 byte以内で指定してください。`);
        }
        updated.fill(0, nameOffset, nameOffset + 16);
        updated.set(alias, nameOffset);
        updatedNames.fill(0, externalOffset, externalOffset + 32);
        updatedNames.set(encodedName, externalOffset);
      } else {
        if (row.asciiName && row.asciiName !== row.name) throw new Error(`${row.channel}番のASCII別名は日本語名専用です。`);
        if (encodedName.length > 10) throw new Error(`${row.channel}番のASCII名は10 byte以内で指定してください。`);
        updated.fill(0, nameOffset, nameOffset + 16);
        updated.set(encodedName, nameOffset);
        updatedNames.fill(0, externalOffset, externalOffset + 32);
      }
    }
    const attrOffset = CHANNEL_ATTRIBUTE_BASE + index * 2;
    const attr = readU16(updated, attrOffset);
    writeU16(updated, attrOffset, (attr & 0x00FF) | (Number(row.scanLists) << 8));
  });
  return { image: updated, nameTable: updatedNames };
}
