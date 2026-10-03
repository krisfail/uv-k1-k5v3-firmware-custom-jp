import {
  JAPANESE_NAME_BASE,
  RadioSession,
  WebSerialTransport,
  ProtocolError,
  SafetyError,
  validateLogicalWrite,
  changedBlockCount,
} from "./protocol.mjs";
import { MEMORY_PRESETS, bytesToHex, diffSummary, hexToBytes, parseInteger, validateMemoryEditorRange, formatAddress } from "./memory.mjs";
import {
  CHANNEL_COUNT,
  CHANNEL_IMAGE_SIZE,
  CTCSS_TONES,
  DTCS_CODES,
  FIELDNAMES_V2,
  MODES,
  STEPS,
  TONE_MODES,
  decodeChannelList,
  emptyChannel,
  encodeChannelList,
  formatChannelList,
  parseChannelList,
} from "./channels.mjs";
import { downloadBytes, downloadText, loadBundledFont, loadCodepoints, linesToText, packNameLines, parseNameFile, unpackNameTable } from "./resources.mjs";
import { SETTINGS_BASE, SETTINGS_SIZE, SETTING_FIELDS, applySettings, readSettings as decodeSettings } from "./settings.mjs";

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const state = {
  port: null,
  transport: null,
  session: null,
  busy: false,
  memory: { offset: 0, before: null },
  channels: { image: null, names: null, rows: [] },
  settings: { raw: null, values: null },
  pendingNames: null,
  toastTimer: null,
};

function log(message, isError = false) {
  const item = document.createElement("li");
  item.textContent = `${new Date().toLocaleTimeString("ja-JP")}　${message}`;
  if (isError) item.dataset.error = "true";
  $("#activity-log").prepend(item);
}

function toast(message) {
  const element = $("#toast");
  element.textContent = message;
  element.classList.add("show");
  clearTimeout(state.toastTimer);
  state.toastTimer = setTimeout(() => element.classList.remove("show"), 4200);
}

function setConnectionState(message, kind = "") {
  const banner = $("#connection-state");
  banner.classList.toggle("connected", kind === "connected");
  banner.classList.toggle("error", kind === "error");
  $("#connection-text").textContent = message;
}

function formatError(error) {
  if (error instanceof SafetyError || error instanceof ProtocolError) return error.message;
  const message = String(error?.message ?? error ?? "");
  if (/requestPort|user cancelled|cancelled/i.test(message)) return "ポートの選択をキャンセルしました。";
  if (/already open|open\(\)/i.test(message)) return "ポートを開けませんでした。ほかのソフトウェアが使用していないか確認してください。";
  if (/not supported|navigator\.serial/i.test(message)) return "このブラウザーはWebSerialに対応していません。ChromeまたはEdgeのHTTPSページで開いてください。";
  if (/network|disconnect|device/i.test(message)) return "無線機との接続が切れました。画面を通常の受信画面に戻してから再接続してください。";
  return "操作を完了できませんでした。入力内容、接続状態、無線機の画面を確認してください。";
}

async function runTask(label, task) {
  if (state.busy) {
    toast("別の通信処理が実行中です。完了するまでお待ちください。");
    return null;
  }
  if (!state.session && label !== "接続") {
    const error = new SafetyError("先に無線機へ接続してください。");
    toast(error.message);
    return null;
  }
  state.busy = true;
  document.body.dataset.busy = "true";
  log(`${label}を開始しました。`);
  try {
    const result = await task((progress) => {
      if (!progress?.total) return;
      const percent = Math.round((progress.completed / progress.total) * 100);
      setConnectionState(`${label}：${percent}%`, "connected");
    });
    log(`${label}が完了しました。`);
    return result;
  } catch (error) {
    const message = formatError(error);
    if (error instanceof ProtocolError) await discardSession();
    setConnectionState(message, "error");
    log(`${label}に失敗しました：${message}`, true);
    toast(message);
    return null;
  } finally {
    state.busy = false;
    document.body.dataset.busy = "false";
    if (state.session) setConnectionState(`接続中：${state.session.firmware || "WRX-JP"}`, "connected");
    updateActionState();
  }
}

function ensureSession() {
  if (!state.session) throw new SafetyError("先に無線機へ接続してください。");
  return state.session;
}

async function discardSession() {
  const transport = state.transport;
  state.session = null;
  state.transport = null;
  if (transport) await transport.close();
}

function setButtonBusy(button, busy) {
  if (button) button.disabled = busy;
}

function updateActionState() {
  const connected = Boolean(state.session) && !state.busy;
  $("#connect").disabled = state.busy || Boolean(state.session);
  $("#disconnect").disabled = state.busy || !state.session;
  ["memory-read", "channels-read", "settings-read", "names-read"].forEach((id) => { if ($("#" + id)) $("#" + id).disabled = !connected; });
  $("#memory-write").disabled = !connected || !state.memory.before || !memoryHasChanges();
  $("#channels-write").disabled = !connected || !state.channels.image;
  $("#settings-write").disabled = !connected || !state.settings.raw;
  $("#font-write").disabled = !connected;
  $("#names-write").disabled = !connected || !state.pendingNames;
  $("#memory-export").disabled = !state.memory.before;
  $("#channels-export").disabled = state.channels.rows.length !== CHANNEL_COUNT;
}

async function refreshPorts() {
  if (!navigator.serial) return;
  const ports = await navigator.serial.getPorts();
  const select = $("#granted-ports");
  select.replaceChildren(new Option("許可済みポートを選択", ""));
  ports.forEach((port, index) => {
    const info = port.getInfo();
    const suffix = info.usbVendorId ? `USB ${info.usbVendorId.toString(16).toUpperCase()}:${(info.usbProductId ?? 0).toString(16).toUpperCase()}` : `ポート ${index + 1}`;
    const option = new Option(info.usbVendorId ? suffix : "許可済みシリアルポート", String(index));
    select.append(option);
  });
  select._ports = ports;
  if (state.port) {
    const index = ports.indexOf(state.port);
    if (index >= 0) select.value = String(index);
  }
}

async function choosePort() {
  try {
    state.port = await navigator.serial.requestPort({ filters: [] });
    await refreshPorts();
    log("ポートを選択しました。接続を押してください。");
  } catch (error) {
    if (!/cancel/i.test(String(error?.message ?? error))) {
      setConnectionState(formatError(error), "error");
      toast(formatError(error));
    }
  }
}

async function connect() {
  await runTask("接続", async () => {
    const select = $("#granted-ports");
    state.port = state.port || select._ports?.[Number(select.value)];
    if (!state.port) throw new SafetyError("ポートを選択してください。");
    const transport = new WebSerialTransport(state.port);
    state.transport = transport;
    try {
      await transport.open();
      state.session = new RadioSession(transport);
      await state.session.connect();
      await state.session.probeExternalJapanese();
    } catch (error) {
      await transport.close();
      state.transport = null;
      state.session = null;
      throw error;
    }
    setConnectionState(`接続中：${state.session.firmware || "WRX-JP"}`, "connected");
  });
  updateActionState();
}

async function disconnect() {
  if (state.busy) return;
  await discardSession();
  setConnectionState("無線機を接続してください");
  log("切断しました。");
  updateActionState();
}

function initializeMemoryPresets() {
  const select = $("#memory-preset");
  MEMORY_PRESETS.forEach((preset) => select.append(new Option(preset.label, preset.id)));
  select.addEventListener("change", () => {
    const preset = MEMORY_PRESETS.find((candidate) => candidate.id === select.value);
    if (!preset) return;
    $("#memory-offset").value = formatAddress(preset.offset);
    $("#memory-length").value = formatAddress(preset.length);
    $("#memory-range-help").textContent = preset.writable
      ? `${formatAddress(preset.offset)}–${formatAddress(preset.offset + preset.length - 1)}。通常メモリーの許可範囲です。`
      : `${formatAddress(preset.offset)}–${formatAddress(preset.offset + preset.length - 1)}。読み出し専用です。`;
    updateActionState();
  });
  select.dispatchEvent(new Event("change"));
}

function currentMemoryBytes() {
  const bytes = hexToBytes($("#memory-editor").value);
  const expected = state.memory.before?.length;
  if (expected !== undefined && bytes.length !== expected) {
    throw new SafetyError(`メモリー長が一致しません（${bytes.length} / ${expected} byte）。`);
  }
  return bytes;
}

function memoryHasChanges() {
  if (!state.memory.before) return false;
  try { return diffSummary(state.memory.before, currentMemoryBytes()).bytes > 0; } catch { return false; }
}

function updateMemorySummary() {
  const editor = $("#memory-editor");
  let current;
  try {
    current = hexToBytes(editor.value);
    $("#memory-editor-count").textContent = `${current.length} byte`;
    if (state.memory.before) {
      const summary = diffSummary(state.memory.before, current, state.memory.offset);
      $("#memory-diff-bytes").textContent = String(summary.bytes);
      $("#memory-diff-blocks").textContent = String(summary.blocks);
      $("#memory-check").textContent = current.length === state.memory.before.length ? "形式OK" : "長さ不一致";
    }
  } catch (error) {
    $("#memory-editor-count").textContent = "入力エラー";
    $("#memory-check").textContent = formatError(error);
  }
  updateActionState();
}

async function readMemory() {
  await runTask("メモリー読み出し", async (progress) => {
    const offset = parseInteger($("#memory-offset").value, "開始アドレス");
    const length = parseInteger($("#memory-length").value, "長さ");
    validateMemoryEditorRange(offset, length);
    const data = await ensureSession().readMemory(offset, length, progress);
    state.memory.offset = offset;
    state.memory.before = data;
    $("#memory-editor").value = bytesToHex(data);
    $("#memory-state").textContent = `${formatAddress(offset)}から${length} byte`;
    $("#memory-check").textContent = "readback済み";
    updateMemorySummary();
  });
}

async function writeMemory() {
  let after;
  try {
    after = currentMemoryBytes();
    const offset = state.memory.offset;
    validateLogicalWrite(offset, after.length);
    const summary = diffSummary(state.memory.before, after, offset);
    if (!summary.bytes) { toast("変更はありません。"); return; }
    const confirmed = await confirmAction("メモリーを書き込みます", `${summary.bytes} byte、${summary.blocks} blockを変更します。\n書き込み後に各blockをreadback検証します。`);
    if (!confirmed) return;
  } catch (error) {
    toast(formatError(error));
    return;
  }
  await runTask("メモリー書き込み", (progress) => ensureSession().writeMemoryChanged(
    state.memory.offset, state.memory.before, after, true, progress)).then((result) => {
    if (result === undefined && state.session) {
      state.memory.before = after;
      $("#memory-check").textContent = "書き込み・readback済み";
      updateMemorySummary();
    }
  });
}

async function importMemoryFile(file) {
  const name = file.name.toLowerCase();
  const data = name.endsWith(".bin") ? new Uint8Array(await file.arrayBuffer()) : hexToBytes(await file.text());
  if (state.memory.before && data.length !== state.memory.before.length) throw new SafetyError("ファイルの長さが現在の読出し領域と一致しません。");
  $("#memory-editor").value = bytesToHex(data);
  $("#memory-check").textContent = state.memory.before ? "変更候補" : "無線機の基準値がありません";
  updateMemorySummary();
}

function makeChannelInput(row, field, value, className, type = "text") {
  const input = document.createElement("input");
  input.className = className;
  input.type = type;
  input.value = value ?? "";
  input.dataset.field = field;
  input.addEventListener("input", () => {
    const parsed = input.type === "number" ? (input.value === "" ? null : Number(input.value)) : input.value;
    row[field] = parsed;
    input.closest("tr")?.classList.toggle("changed", true);
    updateActionState();
  });
  return input;
}

function makeChannelSelect(row, field, value, options, className) {
  const select = document.createElement("select");
  select.className = className;
  select.dataset.field = field;
  options.forEach((option) => select.append(new Option(option || "なし", option)));
  select.value = value ?? options[0];
  select.addEventListener("change", () => { row[field] = select.value; select.closest("tr")?.classList.toggle("changed", true); updateActionState(); });
  return select;
}

function channelMatches(row, filter) {
  if (!filter) return true;
  return `${row.channel} ${row.frequencyHz ?? ""} ${row.name} ${row.asciiName}`.toLowerCase().includes(filter.toLowerCase());
}

function renderChannels() {
  const body = $("#channels-body");
  const filter = $("#channels-filter").value.trim();
  body.replaceChildren();
  let shown = 0;
  state.channels.rows.forEach((row) => {
    if (!channelMatches(row, filter)) return;
    shown += 1;
    const tr = document.createElement("tr");
    if (row.frequencyHz === null) tr.classList.add("empty-row");
    const number = document.createElement("td"); number.textContent = String(row.channel); tr.append(number);
    const frequency = document.createElement("td"); frequency.append(makeChannelInput(row, "frequencyHz", row.frequencyHz ?? "", "freq", "number")); tr.append(frequency);
    const mode = document.createElement("td"); mode.append(makeChannelSelect(row, "mode", row.mode, MODES, "mode")); tr.append(mode);
    const tone = document.createElement("td");
    tone.append(makeChannelSelect(row, "toneMode", row.toneMode, TONE_MODES, "tone"));
    const toneInput = makeChannelInput(row, row.toneMode === "DTCS" ? "dtcs" : "tone", row.toneMode === "DTCS" ? row.dtcs : row.tone, "tone-value", "text");
    toneInput.title = row.toneMode === "DTCS" ? "DTCS code" : "CTCSS tone";
    tone.append(toneInput); tr.append(tone);
    const step = document.createElement("td");
    step.append(makeChannelSelect(row, "tuningStepKhz", row.tuningStepKhz, STEPS.map((value) => String(value)), "step"));
    tr.append(step);
    const scan = document.createElement("td"); scan.append(makeChannelInput(row, "scanLists", row.scanLists, "scan", "number")); tr.append(scan);
    const name = document.createElement("td"); name.append(makeChannelInput(row, "name", row.name, "name")); tr.append(name);
    const alias = document.createElement("td"); alias.append(makeChannelInput(row, "asciiName", row.asciiName, "alias")); tr.append(alias);
    body.append(tr);
  });
  $("#channels-count").textContent = `${shown} / ${CHANNEL_COUNT}件`;
}

async function readChannels() {
  await runTask("チャンネル一覧読み出し", async (progress) => {
    const image = await ensureSession().readMemory(0, CHANNEL_IMAGE_SIZE, progress);
    const names = await ensureSession().readExternalNames(progress);
    state.channels.image = image;
    state.channels.names = names;
    state.channels.rows = decodeChannelList(image, names);
    renderChannels();
    updateActionState();
  });
}

async function importChannels(file) {
  const rows = parseChannelList(await file.text());
  state.channels.rows = rows;
  renderChannels();
  log("TSVを読み込みました。書き込み前に内容を確認してください。");
  updateActionState();
}

async function writeChannels() {
  if (!state.channels.image || !state.channels.names) { toast("先に無線機からチャンネル一覧を読み出してください。"); return; }
  try {
    const codepoints = await loadCodepoints();
    const encoded = encodeChannelList(state.channels.rows, state.channels.image, state.channels.names, codepoints);
    const memoryDiff = diffSummary(state.channels.image, encoded.image, 0);
    const namesDiff = diffSummary(state.channels.names, encoded.nameTable, JAPANESE_NAME_BASE);
    if (!memoryDiff.bytes && !namesDiff.bytes) { toast("変更はありません。"); return; }
    const confirmed = await confirmAction("チャンネル一覧を書き込みます", `${memoryDiff.bytes + namesDiff.bytes} byteを変更します。\nチャンネル領域と日本語名前テーブルをreadback検証します。`);
    if (!confirmed) return;
    const result = await runTask("チャンネル一覧書き込み", async (progress) => {
      if (memoryDiff.bytes) await ensureSession().writeMemoryChanged(0, state.channels.image, encoded.image, true, progress);
      if (namesDiff.bytes) await ensureSession().writeExternalChanged(JAPANESE_NAME_BASE, state.channels.names, encoded.nameTable, true, progress);
    });
    if (result === undefined && state.session) {
      state.channels.image = encoded.image;
      state.channels.names = encoded.nameTable;
      state.channels.rows = decodeChannelList(encoded.image, encoded.nameTable);
      renderChannels();
    }
  } catch (error) { toast(formatError(error)); }
}

function renderSettings() {
  const container = $("#settings-form");
  container.replaceChildren();
  if (!state.settings.values) { container.append(Object.assign(document.createElement("div"), { className: "empty-state", textContent: "先に設定領域を読み出してください。" })); return; }
  const groups = [...new Set(SETTING_FIELDS.map((field) => field.group))];
  groups.forEach((group) => {
    const card = document.createElement("section"); card.className = "card settings-group";
    const heading = document.createElement("h3"); heading.textContent = group; card.append(heading);
    const fields = document.createElement("div"); fields.className = "settings-fields";
    SETTING_FIELDS.filter((field) => field.group === group).forEach((field) => {
      const label = document.createElement("label"); label.textContent = field.label; fields.append(label);
      let control;
      if (field.kind === "select") {
        control = document.createElement("select"); field.options.forEach((option) => control.append(new Option(option, option)));
        control.value = state.settings.values[field.key];
      } else if (field.kind === "checkbox") {
        control = document.createElement("input"); control.type = "checkbox"; control.checked = Boolean(state.settings.values[field.key]);
      } else {
        control = document.createElement("input"); control.type = field.kind === "number" ? "number" : "text"; control.value = state.settings.values[field.key] ?? "";
        if (field.min !== undefined) { control.min = field.min; control.max = field.max; }
        if (field.maxLength) control.maxLength = field.maxLength;
      }
      control.dataset.setting = field.key;
      control.addEventListener("input", () => { state.settings.values[field.key] = field.kind === "checkbox" ? control.checked : control.value; updateActionState(); });
      control.addEventListener("change", () => { state.settings.values[field.key] = field.kind === "checkbox" ? control.checked : control.value; updateActionState(); });
      fields.append(control);
    });
    card.append(fields); container.append(card);
  });
  const fm = document.createElement("section"); fm.className = "card fm-settings";
  const title = document.createElement("h3"); title.textContent = "FM放送プリセット（BK1080）"; fm.append(title);
  const currentLabel = document.createElement("label"); currentLabel.className = "field-help"; currentLabel.textContent = "現在周波数（0.1 MHz単位）";
  const current = document.createElement("input"); current.type = "number"; current.min = 760; current.max = 950; current.value = state.settings.values.fmCurrent;
  current.addEventListener("input", () => { state.settings.values.fmCurrent = current.value; updateActionState(); }); currentLabel.append(current); fm.append(current);
  const grid = document.createElement("div"); grid.className = "fm-grid";
  state.settings.values.fmStations.forEach((value, index) => {
    const label = document.createElement("label"); label.textContent = `FM ${String(index + 1).padStart(2, "0")}`;
    const input = document.createElement("input"); input.type = "number"; input.min = 0; input.max = 950; input.value = value || ""; input.placeholder = "空き";
    input.addEventListener("input", () => { state.settings.values.fmStations[index] = input.value === "" ? 0 : Number(input.value); updateActionState(); });
    label.append(input); grid.append(label);
  });
  fm.append(grid); container.append(fm);
}

async function readSettings() {
  await runTask("設定読み出し", async (progress) => {
    const raw = await ensureSession().readMemory(SETTINGS_BASE, SETTINGS_SIZE, progress);
    state.settings.raw = raw;
    state.settings.values = decodeSettings(raw);
    $("#settings-editor").value = bytesToHex(raw);
    $("#settings-editor").readOnly = true;
    $("#settings-state").textContent = "readback済み。未定義 byte は保持されます。";
    renderSettings();
    updateActionState();
  });
}

async function writeSettings() {
  if (!state.settings.raw) { toast("先に設定を読み出してください。"); return; }
  try {
    const after = applySettings(state.settings.raw, state.settings.values);
    const summary = diffSummary(state.settings.raw, after, SETTINGS_BASE);
    if (!summary.bytes) { toast("変更はありません。"); return; }
    if (!await confirmAction("設定を書き込みます", `${summary.bytes} byte、${summary.blocks} blockを変更します。\n未定義 byte は変更しません。`)) return;
    const result = await runTask("設定書き込み", (progress) => ensureSession().writeMemoryChanged(
      SETTINGS_BASE, state.settings.raw, after, true, progress));
    if (result === undefined && state.session) {
      state.settings.raw = after;
      $("#settings-editor").value = bytesToHex(after);
      $("#settings-state").textContent = "書き込み・readback済み";
      renderSettings();
    }
  } catch (error) { toast(formatError(error)); }
}

async function writeFont() {
  if (!await confirmAction("固定フォントを書き込みます", "同梱のIzumi 16・専用14px・美咲8×8を外部Flashへ書き込みます。\n名前テーブルは変更しません。")) return;
  await runTask("固定フォント書き込み", async (progress) => {
    const font = await loadBundledFont();
    await ensureSession().writeJapaneseFont(font, true, progress);
    $("#font-status").textContent = "書き込み・readback済み";
  });
}

async function readNames() {
  await runTask("名前テーブル読み出し", async (progress) => {
    const data = await ensureSession().readExternalNames(progress);
    const text = linesToText(unpackNameTable(data));
    downloadText(text, "wrx-jp-names.txt");
    $("#names-status").textContent = "読み出して保存しました。";
  });
}

async function selectNames(file) {
  const codepoints = await loadCodepoints();
  const parsed = parseNameFile(await file.text(), codepoints);
  state.pendingNames = parsed.table;
  $("#names-status").textContent = `${file.name}：1024行、検査済み`;
  updateActionState();
}

async function writeNames() {
  if (!state.pendingNames) { toast("先に名前ファイルを選択してください。"); return; }
  if (!await confirmAction("名前テーブルを書き込みます", "1024件の名前テーブルを外部Flashへ書き込みます。\nフォントは変更しません。")) return;
  await runTask("名前テーブル書き込み", async (progress) => {
    await ensureSession().writeJapaneseNames(state.pendingNames, true, progress);
    $("#names-status").textContent = "書き込み・readback済み";
  });
}

function confirmAction(title, message) {
  const dialog = $("#confirm-dialog");
  if (!dialog.showModal) return Promise.resolve(window.confirm(`${title}\n\n${message}`));
  $("#confirm-title").textContent = title;
  $("#confirm-message").textContent = message;
  dialog.showModal();
  return new Promise((resolve) => {
    dialog.addEventListener("close", () => resolve(dialog.returnValue === "ok"), { once: true });
  });
}

function initializeNavigation() {
  $$(".nav-item").forEach((button) => button.addEventListener("click", () => {
    const view = button.dataset.view;
    $$(".nav-item").forEach((item) => item.classList.toggle("active", item === button));
    $$(".view").forEach((panel) => { const active = panel.dataset.viewPanel === view; panel.hidden = !active; panel.classList.toggle("active", active); });
  }));
}

function bindEvents() {
  $("#choose-port").addEventListener("click", choosePort);
  $("#granted-ports").addEventListener("change", (event) => { state.port = event.target._ports?.[Number(event.target.value)] ?? null; });
  $("#connect").addEventListener("click", connect);
  $("#disconnect").addEventListener("click", disconnect);
  $("#memory-read").addEventListener("click", readMemory);
  $("#memory-write").addEventListener("click", writeMemory);
  $("#memory-editor").addEventListener("input", updateMemorySummary);
  $("#memory-import").addEventListener("click", () => $("#memory-file").click());
  $("#memory-file").addEventListener("change", async (event) => { if (event.target.files[0]) { try { await importMemoryFile(event.target.files[0]); } catch (error) { toast(formatError(error)); } } event.target.value = ""; });
  $("#memory-export").addEventListener("click", () => { try { downloadBytes(currentMemoryBytes(), `wrx-jp-memory-${formatAddress(state.memory.offset, 4).slice(2)}.bin`); } catch (error) { toast(formatError(error)); } });
  $("#channels-read").addEventListener("click", readChannels);
  $("#channels-write").addEventListener("click", writeChannels);
  $("#channels-filter").addEventListener("input", renderChannels);
  $("#channels-import").addEventListener("click", () => $("#channels-file").click());
  $("#channels-file").addEventListener("change", async (event) => { if (event.target.files[0]) { try { await importChannels(event.target.files[0]); } catch (error) { toast(formatError(error)); } } event.target.value = ""; });
  $("#channels-export").addEventListener("click", () => { try { downloadText(formatChannelList(state.channels.rows), "wrx-jp-channels.tsv", "text/tab-separated-values;charset=utf-8"); } catch (error) { toast(formatError(error)); } });
  $("#settings-read").addEventListener("click", readSettings);
  $("#settings-write").addEventListener("click", writeSettings);
  $("#font-write").addEventListener("click", writeFont);
  $("#names-read").addEventListener("click", readNames);
  $("#names-write").addEventListener("click", writeNames);
  $("#names-file").addEventListener("change", async (event) => { if (event.target.files[0]) { try { await selectNames(event.target.files[0]); } catch (error) { toast(formatError(error)); } } event.target.value = ""; });
  $("#clear-log").addEventListener("click", () => $("#activity-log").replaceChildren());
}

async function init() {
  initializeNavigation();
  initializeMemoryPresets();
  bindEvents();
  if (!navigator.serial) {
    $("#browser-support").textContent = "WebSerial非対応";
    setConnectionState("WebSerialに対応したChromeまたはEdgeで開いてください。", "error");
    $("#choose-port").disabled = true;
    updateActionState();
    return;
  }
  $("#browser-support").textContent = "WebSerial対応";
  await refreshPorts();
  navigator.serial.addEventListener("connect", refreshPorts);
  navigator.serial.addEventListener("disconnect", async (event) => {
    if (event.target === state.port && !state.busy) await disconnect();
    await refreshPorts();
  });
  window.addEventListener("pagehide", () => { if (state.transport) void state.transport.close(); });
  updateActionState();
}

void init();
