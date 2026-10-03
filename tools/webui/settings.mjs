export const SETTINGS_BASE = 0xA000;
export const SETTINGS_SIZE = 0x170;
export const FM_MIN = 760;
export const FM_MAX = 950;

const backlightChoices = ["OFF"];
for (let seconds = 5; seconds <= 300; seconds += 5) {
  backlightChoices.push(seconds < 60 ? `${seconds}秒` : `${Math.floor(seconds / 60)}分${seconds % 60 ? `${String(seconds % 60).padStart(2, "0")}秒` : ""}`);
}
backlightChoices.push("常時点灯");
const sleepChoices = ["OFF", ...Array.from({ length: 120 }, (_, index) => `${index + 1}分`)];
const autoLockChoices = ["OFF", ...Array.from({ length: 40 }, (_, index) => {
  const seconds = (index + 1) * 15;
  return `${Math.floor(seconds / 60)}分${String(seconds % 60).padStart(2, "0")}秒`;
})];
const scanResumeChoices = ["停止", ...Array.from({ length: 80 }, (_, index) => `キャリア解消後 ${((index + 1) * 0.25).toFixed(2)}秒`),
  ...Array.from({ length: 24 }, (_, index) => `タイムアウト後 ${(index + 1) * 5}秒`)];
const actionChoices = ["なし", "ライト", "モニター", "スキャン", "FMラジオ", "キーロック",
  "A/B切替", "VFO/メモリ切替", "モード切替", "最低輝度解除", "受信モード",
  "受信専用", "W/N", "バックライト", "ミュート", "受信音声", "（現在値を保持）"];
const actionRaw = Object.freeze({
  "なし": 0, "ライト": 1, "モニター": 3, "スキャン": 4, "FMラジオ": 7,
  "キーロック": 9, "A/B切替": 10, "VFO/メモリ切替": 11, "モード切替": 12,
  "最低輝度解除": 13, "受信モード": 14, "受信専用": 15, "W/N": 17,
  "バックライト": 18, "ミュート": 19, "受信音声": 20,
});

export const SETTING_FIELDS = Object.freeze([
  { key: "squelch", label: "スケルチ", group: "基本設定", kind: "number", min: 0, max: 9 },
  { key: "channelDisplay", label: "チャンネル表示", group: "基本設定", kind: "select", options: ["周波数", "チャンネル番号", "名前", "名前＋周波数"] },
  { key: "batterySave", label: "バッテリーセーブ", group: "基本設定", kind: "select", options: ["OFF", "1:1", "1:2", "1:3", "1:4", "1:5"] },
  { key: "dualWatch", label: "デュアル受信", group: "基本設定", kind: "select", options: ["OFF", "A", "B"] },
  { key: "backlightTime", label: "バックライト時間", group: "基本設定", kind: "select", options: backlightChoices },
  { key: "scanResume", label: "スキャン再開", group: "基本設定", kind: "select", options: scanResumeChoices },
  { key: "powerOnDisplay", label: "起動画面", group: "基本設定", kind: "select", options: ["全画面", "音声", "メッセージ", "電圧", "ロゴ", "ロゴ＋メッセージ", "ロゴ＋全画面", "なし"] },
  { key: "batteryType", label: "バッテリー種別", group: "基本設定", kind: "select", options: ["1600mAh K5", "2200mAh K5", "3500mAh K5", "1500mAh K1", "2500mAh K1"] },
  { key: "backlightMin", label: "バックライト最低輝度", group: "表示・操作", kind: "number", min: 0, max: 10 },
  { key: "backlightMax", label: "バックライト最高輝度", group: "表示・操作", kind: "number", min: 0, max: 10 },
  { key: "contrast", label: "コントラスト", group: "表示・操作", kind: "number", min: 1, max: 15 },
  { key: "invertDisplay", label: "表示反転", group: "表示・操作", kind: "checkbox" },
  { key: "meterStyle", label: "Sメーター表示", group: "表示・操作", kind: "select", options: ["TINY", "CLASSIC"] },
  { key: "guiStyle", label: "GUI表示", group: "表示・操作", kind: "checkbox" },
  { key: "japaneseMainFont", label: "主画面チャンネル名", group: "表示・操作", kind: "select", options: ["16×16日本語", "8×8美咲", "ASCII", "14×14日本語"] },
  { key: "menuLock", label: "メニューロック範囲", group: "表示・操作", kind: "select", options: ["キー", "キー＋操作", "キー＋PTT", "キー＋操作＋PTT"] },
  { key: "sleepTimer", label: "スリープタイマー", group: "表示・操作", kind: "select", options: sleepChoices },
  { key: "beep", label: "キービープ", group: "表示・操作", kind: "checkbox" },
  { key: "keyLock", label: "キーロック", group: "表示・操作", kind: "checkbox" },
  { key: "autoKeypadLock", label: "自動キーロック", group: "表示・操作", kind: "select", options: autoLockChoices },
  { key: "key1Short", label: "サイドキー1 短押し", group: "プログラマブルキー", kind: "select", options: actionChoices },
  { key: "key1Long", label: "サイドキー1 長押し", group: "プログラマブルキー", kind: "select", options: actionChoices },
  { key: "key2Short", label: "サイドキー2 短押し", group: "プログラマブルキー", kind: "select", options: actionChoices },
  { key: "key2Long", label: "サイドキー2 長押し", group: "プログラマブルキー", kind: "select", options: actionChoices },
  { key: "keyMLong", label: "［M］長押し", group: "プログラマブルキー", kind: "select", options: actionChoices },
  { key: "scanList", label: "標準スキャンリスト", group: "スキャン設定", kind: "select", options: [...Array.from({ length: 24 }, (_, index) => `リスト ${index + 1}`), "全チャンネル"] },
  { key: "scanListEnabled", label: "標準スキャンリストを有効化", group: "スキャン設定", kind: "checkbox" },
  { key: "priority1", label: "優先チャンネル1（0=未設定）", group: "スキャン設定", kind: "number", min: 0, max: 1024 },
  { key: "priority2", label: "優先チャンネル2（0=未設定）", group: "スキャン設定", kind: "number", min: 0, max: 1024 },
  { key: "callChannel", label: "コールチャンネル（0=未設定）", group: "スキャン設定", kind: "number", min: 0, max: 1024 },
  { key: "audioFm", label: "FM受信音声プロファイル", group: "F4HWN受信設定", kind: "select", options: ["FLAT", "CLEAN", "MID", "BOOST", "MAX"] },
  { key: "audioAm", label: "AM受信音声プロファイル", group: "F4HWN受信設定", kind: "select", options: ["SHARP", "STOCK", "OPEN"] },
  { key: "nfmNarrower", label: "NFMナロー化", group: "F4HWN受信設定", kind: "checkbox" },
  { key: "logo1", label: "ロゴ1（ASCII 16文字）", group: "起動画面ロゴ", kind: "text", maxLength: 16 },
  { key: "logo2", label: "ロゴ2（ASCII 16文字）", group: "起動画面ロゴ", kind: "text", maxLength: 16 },
]);

function u16(data, offset) {
  return new DataView(data.buffer, data.byteOffset, data.byteLength).getUint16(offset, true);
}
function putU16(data, offset, value) {
  new DataView(data.buffer).setUint16(offset, value, true);
}
function choice(options, value, fallback = 0) {
  return options[value] ?? options[fallback];
}
function channelValue(data, offset) {
  const value = u16(data, offset);
  return value >= 1024 ? 0 : value + 1;
}
function actionValue(raw) {
  const entry = Object.entries(actionRaw).find(([, value]) => value === raw);
  return entry?.[0] ?? "（現在値を保持）";
}
function actionValueToRaw(value, fallback) {
  return value === "（現在値を保持）" || value === undefined ? fallback : (actionRaw[value] ?? fallback);
}
function asciiValue(data, start) {
  let result = "";
  for (let index = 0; index < 16; index += 1) {
    const value = data[start + index];
    if (value === 0 || value === 0xFF || value < 0x20 || value > 0x7E) break;
    result += String.fromCharCode(value);
  }
  return result;
}

export function readSettings(data) {
  if (data.length !== SETTINGS_SIZE) throw new Error("設定領域のサイズが不正です。");
  const values = {
    squelch: data[1] < 10 ? data[1] : 1,
    channelDisplay: choice(SETTING_FIELDS[1].options, data[9]),
    batterySave: choice(SETTING_FIELDS[2].options, data[11], 4),
    dualWatch: choice(SETTING_FIELDS[3].options, data[12], 1),
    backlightTime: choice(backlightChoices, data[13], 12),
    scanResume: choice(scanResumeChoices, data[0xA8 + 5], 14),
    powerOnDisplay: choice(SETTING_FIELDS[6].options, data[0xA8 + 7], 3),
    batteryType: choice(SETTING_FIELDS[7].options, data[0xA8 + 0x1C]),
    backlightMin: Math.min(data[8] >> 4, 10),
    backlightMax: Math.min(data[8] & 0x0F, 10),
    contrast: (data[0x15D] & 0x0F) || 10,
    invertDisplay: Boolean(data[0x15D] & 0x10),
    meterStyle: data[0x15D] & 0x40 ? "CLASSIC" : "TINY",
    guiStyle: Boolean(data[0x15D] & 0x80),
    japaneseMainFont: choice(SETTING_FIELDS[14].options, data[0x15B] & 3),
    menuLock: choice(SETTING_FIELDS[15].options, data[0x15A]),
    sleepTimer: choice(sleepChoices, data[0x15C] >> 1, 60),
    beep: Boolean(data[0xA8] & 1),
    keyLock: Boolean(data[4] & 1),
    autoKeypadLock: choice(autoLockChoices, data[0xA8 + 6]),
    key1Short: actionValue(data[0xA9]), key1Long: actionValue(data[0xAA]),
    key2Short: actionValue(data[0xAB]), key2Long: actionValue(data[0xAC]),
    keyMLong: actionValue(data[0xA8] >> 1),
    _actionRaw: {
      key1Short: data[0xA9], key1Long: data[0xAA],
      key2Short: data[0xAB], key2Long: data[0xAC], keyMLong: data[0xA8] >> 1,
    },
    scanList: choice(SETTING_FIELDS[25].options, Math.max(0, (data[0x130] & 0x7F) - 1)),
    scanListEnabled: Boolean(data[0x130] & 0x80),
    priority1: channelValue(data, 0x131), priority2: channelValue(data, 0x133),
    callChannel: channelValue(data, 0x135),
    audioFm: choice(SETTING_FIELDS[30].options, data[0] & 0x0F),
    audioAm: choice(SETTING_FIELDS[31].options, data[0] >> 4),
    nfmNarrower: Boolean(data[14] & 2),
    logo1: asciiValue(data, 0xC8), logo2: asciiValue(data, 0xD8),
    fmCurrent: Math.min(Math.max(u16(data, 0x20), FM_MIN), FM_MAX),
    fmStations: Array.from({ length: 48 }, (_, index) => {
      const value = u16(data, 0x28 + index * 2);
      return value >= FM_MIN && value <= FM_MAX ? value : 0;
    }),
  };
  if (values.backlightMin >= values.backlightMax) values.backlightMin = 0;
  return values;
}

function intValue(values, key, minimum, maximum, fallback) {
  const value = values[key] === undefined ? fallback : Number(values[key]);
  if (!Number.isInteger(value) || value < minimum || value > maximum) throw new Error(`${key}の値が範囲外です。`);
  return value;
}
function indexValue(options, value, fallback) {
  const index = options.indexOf(value);
  if (value === undefined) return fallback;
  if (index < 0) throw new Error("設定値が不正です。");
  return index;
}

export function applySettings(input, values) {
  if (input.length !== SETTINGS_SIZE) throw new Error("設定領域のサイズが不正です。");
  const data = new Uint8Array(input);
  const current = readSettings(data);
  data[0] = indexValue(SETTING_FIELDS[30].options, values.audioFm, SETTING_FIELDS[30].options.indexOf(current.audioFm)) |
    (indexValue(SETTING_FIELDS[31].options, values.audioAm, SETTING_FIELDS[31].options.indexOf(current.audioAm)) << 4);
  data[1] = intValue(values, "squelch", 0, 9, current.squelch);
  data[9] = indexValue(SETTING_FIELDS[1].options, values.channelDisplay, SETTING_FIELDS[1].options.indexOf(current.channelDisplay));
  data[11] = indexValue(SETTING_FIELDS[2].options, values.batterySave, SETTING_FIELDS[2].options.indexOf(current.batterySave));
  data[12] = indexValue(SETTING_FIELDS[3].options, values.dualWatch, SETTING_FIELDS[3].options.indexOf(current.dualWatch));
  data[13] = indexValue(backlightChoices, values.backlightTime, backlightChoices.indexOf(current.backlightTime));
  const min = intValue(values, "backlightMin", 0, 10, current.backlightMin);
  const max = intValue(values, "backlightMax", 0, 10, current.backlightMax);
  if (min > max) throw new Error("最低輝度は最高輝度以下にしてください。");
  data[8] = (min << 4) | max;
  data[14] = (data[14] & ~2) | (values.nfmNarrower === undefined ? (current.nfmNarrower ? 2 : 0) : (values.nfmNarrower ? 2 : 0));
  data[4] = (data[4] & ~1) | (values.keyLock === undefined ? (current.keyLock ? 1 : 0) : (values.keyLock ? 1 : 0));
  const actions = [values.keyMLong, values.key1Short, values.key1Long, values.key2Short, values.key2Long];
  data[0xA8] = (data[0xA8] & 1) | (actionValueToRaw(actions[0], current._actionRaw.keyMLong) << 1);
  data[0xA8] = (data[0xA8] & ~1) | (values.beep === undefined ? (current.beep ? 1 : 0) : (values.beep ? 1 : 0));
  [0xA9, 0xAA, 0xAB, 0xAC].forEach((offset, index) => {
    const key = ["key1Short", "key1Long", "key2Short", "key2Long"][index];
    data[offset] = actionValueToRaw(actions[index + 1], current._actionRaw[key]);
  });
  data[0xA8 + 5] = indexValue(scanResumeChoices, values.scanResume, scanResumeChoices.indexOf(current.scanResume));
  data[0xA8 + 6] = indexValue(autoLockChoices, values.autoKeypadLock, autoLockChoices.indexOf(current.autoKeypadLock));
  data[0xA8 + 7] = indexValue(SETTING_FIELDS[6].options, values.powerOnDisplay, SETTING_FIELDS[6].options.indexOf(current.powerOnDisplay));
  data[0xA8 + 0x1C] = indexValue(SETTING_FIELDS[7].options, values.batteryType, SETTING_FIELDS[7].options.indexOf(current.batteryType));
  data[0x130] = (data[0x130] & 0x80) | (indexValue(SETTING_FIELDS[25].options, values.scanList, SETTING_FIELDS[25].options.indexOf(current.scanList)) + 1);
  data[0x130] = (data[0x130] & ~0x80) | (values.scanListEnabled === undefined ? (current.scanListEnabled ? 0x80 : 0) : (values.scanListEnabled ? 0x80 : 0));
  [["priority1", 0x131], ["priority2", 0x133], ["callChannel", 0x135]].forEach(([key, offset]) => {
    const value = intValue(values, key, 0, 1024, current[key]);
    putU16(data, offset, value === 0 ? 1024 : value - 1);
  });
  const contrast = intValue(values, "contrast", 1, 15, current.contrast);
  data[0x15D] = (data[0x15D] & 0xF0) | contrast;
  [["invertDisplay", 0x10], ["guiStyle", 0x80]].forEach(([key, mask]) => {
    const enabled = values[key] === undefined ? current[key] : Boolean(values[key]);
    data[0x15D] = enabled ? data[0x15D] | mask : data[0x15D] & ~mask;
  });
  data[0x15D] = values.meterStyle === undefined ? data[0x15D] : (values.meterStyle === "CLASSIC" ? data[0x15D] | 0x40 : data[0x15D] & ~0x40);
  data[0x15B] = (data[0x15B] & ~3) | indexValue(SETTING_FIELDS[14].options, values.japaneseMainFont, SETTING_FIELDS[14].options.indexOf(current.japaneseMainFont));
  data[0x15A] = indexValue(SETTING_FIELDS[15].options, values.menuLock, SETTING_FIELDS[15].options.indexOf(current.menuLock));
  data[0x15C] = (data[0x15C] & 1) | (indexValue(sleepChoices, values.sleepTimer, sleepChoices.indexOf(current.sleepTimer)) << 1);
  ["logo1", "logo2"].forEach((key, index) => {
    const value = String(values[key] ?? current[key]);
    if (!/^[\x20-\x7E]{0,16}$/.test(value)) throw new Error(`${key}はASCII 16文字以内で指定してください。`);
    const encoded = new TextEncoder().encode(value);
    data.fill(0, 0xC8 + index * 16, 0xD8 + index * 16);
    data.set(encoded, 0xC8 + index * 16);
  });
  putU16(data, 0x20, intValue(values, "fmCurrent", FM_MIN, FM_MAX, current.fmCurrent));
  data[0x23] = (data[0x23] & 0xF9) | 2;
  const stations = values.fmStations ?? current.fmStations;
  if (!Array.isArray(stations) || stations.length !== 48) throw new Error("FMプリセットは48件必要です。");
  stations.forEach((value, index) => {
    const station = intValue({ station: value }, "station", 0, FM_MAX, 0);
    if (station && (station < FM_MIN || station > FM_MAX)) throw new Error("FM放送周波数は76.0〜95.0 MHzで指定してください。");
    putU16(data, 0x28 + index * 2, station || 0xFFFF);
  });
  return data;
}
