"""Small Windows GUI for the WRX-JP UV-K1 / UV-K5 V3 host contract."""

from __future__ import annotations

import binascii
import queue
import re
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from protocol import (  # type: ignore[no-redef]
        BAUD_RATE,
        JAPANESE_FONT_BASE,
        JAPANESE_FONT_SIZE,
        JAPANESE_NAME_BASE,
        RadioSession,
        ProtocolError,
        SafetyError,
        HostToolError,
    )
    import resources  # type: ignore[no-redef]
    import settings  # type: ignore[no-redef]
    import channels  # type: ignore[no-redef]
else:
    from .protocol import (BAUD_RATE, JAPANESE_FONT_BASE, JAPANESE_FONT_SIZE,
                           JAPANESE_NAME_BASE,
                           HostToolError, ProtocolError, RadioSession,
                           SafetyError)
    from . import channels, resources, settings


SETTINGS_BASE = 0xA000
SETTINGS_SIZE = 0x170


def _serial_port_names() -> tuple[str, ...]:
    """接続中のシリアルポート名を取得する。"""
    try:
        from serial.tools import list_ports
    except ImportError:
        return ()
    names = {info.device for info in list_ports.comports() if info.device}

    def sort_key(name: str) -> tuple[int, str]:
        upper = name.upper()
        suffix = upper[3:]
        return (int(suffix), upper) if upper.startswith("COM") and suffix.isdigit() else (0xFFFF, upper)

    return tuple(sorted(names, key=sort_key))


def _parse_integer(value: str) -> int:
    return int(value.strip(), 0)


def _parse_hex(text: str) -> bytes:
    compact = "".join(text.split())
    if not compact:
        return b""
    try:
        return binascii.unhexlify(compact)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("hex data is invalid") from exc


def _format_hex(data: bytes) -> str:
    return " ".join("{:02X}".format(byte) for byte in data)


def _format_validation_error(detail: str) -> str:
    lowered = detail.lower()
    if "hex data is invalid" in lowered:
        return "16進数のデータを読み取れませんでした。入力内容を確認してください。"
    if "channel image" in lowered:
        return "チャンネル領域のサイズが正しくありません。機種と読み出し範囲を確認してください。"
    if "japanese font" in lowered:
        return "同梱フォントのサイズが正しくありません。ファイルを変更せずに再実行してください。"
    if "japanese name table must contain" in lowered:
        return "名前テーブルは1024件分で指定してください。"
    if "japanese name table" in lowered:
        return "日本語の名前テーブルを読み取れませんでした。外部フラッシュの内容を確認してください。"
    if "japanese resource requires exactly 1024" in lowered:
        return "名前ファイルはUTF-8の1024行で指定してください。"
    if "name record" in lowered and "valid utf-8" in lowered:
        return "名前テーブルにUTF-8として読めないデータがあります。"
    if "channel name exceeds 31" in lowered:
        return "チャンネル名はUTF-8で31 byte以内にしてください。"
    if "channel name exceeds the lcd display width" in lowered:
        return "チャンネル名がLCDの表示幅を超えています。短い名前にしてください。"
    if "channel name character u+" in lowered and "not in the font" in lowered:
        codepoint = re.search(r"U\+[0-9A-Fa-f]+", detail)
        suffix = "（{}）".format(codepoint.group(0)) if codepoint else ""
        return "チャンネル名に、フォントに収録されていない文字{}があります。".format(suffix)
    if "channel list is empty" in lowered:
        return "チャンネル一覧が空です。1件以上のチャンネルを入力してください。"
    if "header does not match" in lowered:
        return "チャンネル一覧の形式を判別できません。WRX-JP v1またはv2のTSVを使用してください。"
    if "exactly 1024" in lowered:
        return "チャンネル一覧は1024件で入力してください。"
    if "channel rows must be numbered" in lowered:
        return "チャンネル一覧は1〜1024の連番で入力してください。"
    if "incorrect number of fields" in lowered:
        return "チャンネル一覧の列数が正しくありません。TSVのヘッダーと各行を確認してください。"
    if "must be an integer" in lowered or "must be a number" in lowered:
        return "数値を読み取れませんでした。入力内容を確認してください。"
    if "unsupported mode" in lowered:
        return "チャンネル一覧に対応していないモードが含まれています。"
    if "unsupported tone_mode" in lowered:
        return "チャンネル一覧に対応していないトーン設定が含まれています。"
    if "invalid dtcs_polarity" in lowered:
        return "チャンネル一覧のDTCS極性が正しくありません。"
    if "tuning step" in lowered:
        return "チャンネル一覧に対応していないステップ幅が含まれています。"
    if "unsupported ctcss" in lowered or "unsupported dtcs" in lowered:
        return "チャンネル一覧に対応していないトーン値が含まれています。"
    if "tone is required" in lowered:
        return "トーン設定が必要なチャンネルに値がありません。"
    if "scan_lists" in lowered:
        return "スキャンリストは0〜255の範囲で指定してください。"
    if "contains a tab or newline" in lowered:
        return "チャンネル名とASCII別名にはタブや改行を含められません。"
    if "frequency must be positive" in lowered:
        return "周波数は正の値で指定してください。"
    if "outside" in lowered or "calibration" in lowered:
        return "指定したメモリー範囲は、この操作では書き込めません。"
    if "settings block" in lowered:
        return "設定領域のサイズが正しくありません。機種と読み出し範囲を確認してください。"
    if "invalid value" in lowered or "allowed range" in lowered:
        return "設定値が正しくありません。指定された範囲から選択してください。"
    if "backlight_min" in lowered:
        return "バックライト最低輝度は最高輝度以下にしてください。"
    if "ascii characters" in lowered or "ascii" in lowered and "limited" in lowered:
        return "ロゴはASCII文字を16文字以内で入力してください。"
    if "fm channel" in lowered:
        return "FM周波数は76.0〜95.0 MHzの範囲で指定してください。"
    if "programmable-key action" in lowered:
        return "プログラマブルキーには対応する受信操作を指定してください。"
    if "先に" in detail:
        return detail
    if any("ぁ" <= char <= "龯" for char in detail):
        return detail
    return "入力内容または操作範囲を確認してください。"


def _format_protocol_error(error: ProtocolError) -> str:
    detail = str(error)
    cause = error.__cause__
    cause_detail = str(cause) if cause is not None else ""
    logical = re.search(r"logical memory write failed at (0x[0-9A-Fa-f]+)", detail)
    if logical:
        if "readback mismatch" in cause_detail:
            reason = "書き込んだデータと、無線機から読み出したデータが一致しませんでした。"
        else:
            reason = "無線機から書き込み完了の応答を受信できませんでした。"
        return (
            "無線機のメモリー書き込みに失敗しました。\n"
            "書き込み位置：{}\n"
            "{}\n"
            "無線機を通常の受信画面に戻し、COMポートと接続状態を確認してから、もう一度お試しください。"
        ).format(logical.group(1).upper(), reason)

    external = re.search(r"external resource write failed at (0x[0-9A-Fa-f]+)", detail)
    if external:
        address = int(external.group(1), 16)
        target = "フォント" if JAPANESE_FONT_BASE <= address < JAPANESE_NAME_BASE else "名前テーブル"
        if "readback mismatch" in cause_detail:
            reason = "書き込んだデータと、無線機から読み出したデータが一致しませんでした。"
        else:
            reason = "無線機から書き込み完了の応答を受信できませんでした。"
        return (
            "日本語{}の書き込みに失敗しました。\n"
            "書き込み位置：{}\n"
            "{}\n"
            "無線機との接続と外部フラッシュの状態を確認してから、もう一度お試しください。"
        ).format(target, external.group(1).upper(), reason)

    if "programming mode" in detail:
        return "無線機が書き込みモードになっています。通常の受信画面に戻してから接続してください。"
    if "short read" in cause_detail or "communication failed" in detail:
        return "無線機から応答を受信できませんでした。COMポート、ケーブル、無線機の画面を確認してください。"
    if "readback mismatch" in detail:
        return "書き込んだデータと、無線機から読み出したデータが一致しませんでした。もう一度お試しください。"
    return "無線機との通信を確認できませんでした。COMポートと無線機の状態を確認して、もう一度お試しください。"


def _format_error(error: Exception) -> str:
    if isinstance(error, ProtocolError):
        return _format_protocol_error(error)
    if isinstance(error, SafetyError):
        return _format_validation_error(str(error))
    if isinstance(error, HostToolError):
        detail = str(error)
        if any("ぁ" <= char <= "龯" for char in detail):
            return detail
        return "操作を実行できませんでした。入力内容と接続状態を確認してください。"
    if isinstance(error, ImportError):
        return "通信に必要なpyserialが見つかりません。requirements.txtからインストールしてください。"
    if isinstance(error, UnicodeError):
        return "UTF-8としてファイルを読み取れませんでした。文字コードを確認してください。"
    if isinstance(error, (OSError, IOError)):
        if type(error).__module__.startswith("serial"):
            return "COMポートとの通信に失敗しました。ポートが他のソフトウェアで使用されていないか確認してください。"
        return "ファイルを読み書きできませんでした。パスとアクセス権を確認してください。"
    if isinstance(error, ValueError):
        return _format_validation_error(str(error))
    return "処理中に予期しないエラーが発生しました。入力内容と接続状態を確認してください。"


class WRXJPHost(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("JpRxOnlyホストツール")
        self.geometry("900x680")
        self.minsize(760, 560)
        self.session: RadioSession | None = None
        self.transport = None
        self.settings_raw: bytes | None = None
        self.settings_vars = {}
        self.channel_image_raw: bytes | None = None
        self.channel_names_raw: bytes | None = None
        self._jobs = queue.Queue()
        self._busy = False

        self.port = tk.StringVar()
        self.status = tk.StringVar(value="COMポートを選択してください")
        self.name_path = tk.StringVar()
        self._build_connection_bar()
        self._build_tabs()
        self.after(50, self._drain_jobs)
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _build_connection_bar(self) -> None:
        bar = ttk.Frame(self, padding=8)
        bar.pack(fill="x")
        ttk.Label(bar, text="COMポート").pack(side="left")
        self.port_combo = ttk.Combobox(
            bar, textvariable=self.port, width=12, state="readonly")
        self.port_combo.pack(side="left", padx=(6, 4))
        ttk.Button(bar, text="再検出", command=self._refresh_ports).pack(
            side="left", padx=(0, 8))
        ttk.Button(bar, text="接続", command=self._connect).pack(side="left")
        ttk.Button(bar, text="切断", command=self._disconnect).pack(side="left", padx=4)
        ttk.Label(bar, textvariable=self.status).pack(side="left", padx=12)
        self.progress = ttk.Progressbar(bar, mode="indeterminate", length=120)
        self.progress.pack(side="right", padx=(8, 0))
        self._refresh_ports()

    def _refresh_ports(self) -> None:
        ports = _serial_port_names()
        self.port_combo["values"] = ports
        if self.port.get() not in ports:
            self.port.set(ports[0] if ports else "")
        if self.session is None:
            self.status.set(
                "COMポートを選択してください" if ports else
                "COMポートが見つかりません")

    def _build_tabs(self) -> None:
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self._build_memory_tab(notebook)
        self._build_channels_tab(notebook)
        self._build_settings_tab(notebook)
        self._build_japanese_tab(notebook)

    def _build_memory_tab(self, notebook: ttk.Notebook) -> None:
        tab = ttk.Frame(notebook, padding=8)
        notebook.add(tab, text="メモリー")
        ttk.Label(tab, text="論理アドレス").grid(row=0, column=0, sticky="w")
        self.memory_offset = tk.StringVar(value="0x0000")
        ttk.Entry(tab, textvariable=self.memory_offset, width=12).grid(
            row=0, column=1, sticky="w", padx=6)
        ttk.Label(tab, text="読み出す長さ（byte）").grid(row=0, column=2, sticky="w")
        self.memory_length = tk.StringVar(value="0x80")
        ttk.Entry(tab, textvariable=self.memory_length, width=12).grid(
            row=0, column=3, sticky="w", padx=6)
        ttk.Button(tab, text="読み出し", command=self._read_memory).grid(
            row=0, column=4, padx=4)
        ttk.Button(tab, text="書き込み", command=self._write_memory).grid(
            row=0, column=5, padx=4)
        ttk.Label(
            tab,
            text="calibration（0xB000〜0xB1FF）は読み出し専用です。書き込みはできません。",
            foreground="#9a3412",
        ).grid(row=1, column=0, columnspan=6, sticky="w", pady=(8, 4))
        self.memory_text = self._text_box(tab, 2)

    def _build_channels_tab(self, notebook: ttk.Notebook) -> None:
        tab = ttk.Frame(notebook, padding=8)
        notebook.add(tab, text="チャンネル一覧")
        ttk.Label(
            tab,
            text="1024件の通常チャンネルをTSVで読み出し、編集、書き込みできます。",
        ).grid(row=0, column=0, columnspan=6, sticky="w")
        ttk.Label(
            tab,
            text="周波数、モード、トーン、ステップ、スキャンリスト、表示名、ASCII別名を扱います。受信専用のため、送信周波数は保持しません。",
            foreground="#9a3412",
        ).grid(row=1, column=0, columnspan=6, sticky="w", pady=(6, 8))
        ttk.Button(tab, text="無線機から読み出し", command=self._read_channels).grid(
            row=2, column=0, sticky="w")
        ttk.Button(tab, text="書き込み", command=self._write_channels).grid(
            row=2, column=1, sticky="w", padx=4)
        ttk.Button(tab, text="TSVを読み込む", command=self._load_channels).grid(
            row=2, column=2, sticky="w", padx=4)
        ttk.Button(tab, text="TSVを保存する", command=self._save_channels).grid(
            row=2, column=3, sticky="w", padx=4)
        ttk.Label(
            tab,
            text="フォントは「日本語リソース」タブで先に書き込んでください。calibrationはこの操作の対象外です。",
            foreground="#9a3412",
        ).grid(row=3, column=0, columnspan=6, sticky="w", pady=(8, 4))
        self.channel_text = self._text_box(tab, 4)

    def _build_settings_tab(self, notebook: ttk.Notebook) -> None:
        tab = ttk.Frame(notebook, padding=8)
        notebook.add(tab, text="設定")
        ttk.Label(
            tab,
            text="確認済みの受信専用設定とFM領域（0xA000〜0xA16F）を編集できます。項目名はF4HWN互換です。",
        ).grid(row=0, column=0, columnspan=4, sticky="w")
        ttk.Label(
            tab,
            text="未定義のバイトは保持し、対応するBasic、Display、Keys、Scan、F4HWN、Logo、FM項目だけを更新します。",
            foreground="#9a3412",
        ).grid(row=1, column=0, columnspan=4, sticky="w", pady=(6, 8))
        ttk.Button(tab, text="読み出し", command=self._read_settings).grid(
            row=2, column=0, sticky="w", pady=(0, 6))
        ttk.Button(tab, text="書き込み", command=self._write_settings).grid(
            row=2, column=1, sticky="w", padx=4, pady=(0, 6))
        groups = []
        for field in settings.fields():
            if field.group not in groups:
                groups.append(field.group)
        tabs = ttk.Notebook(tab)
        tabs.grid(row=3, column=0, columnspan=6, sticky="nsew")
        for group in groups:
            group_tab = ttk.Frame(tabs, padding=6)
            tabs.add(group_tab, text=group)
            self._build_setting_group(
                group_tab, [field for field in settings.fields() if field.group == group])
        tab.rowconfigure(3, weight=1)
        tab.columnconfigure(0, weight=1)

    def _build_setting_group(self, parent: ttk.Frame, fields) -> None:
        canvas = tk.Canvas(parent, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)
        window = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)
        inner.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window, width=event.width))
        for row, field in enumerate(fields):
            ttk.Label(inner, text=field.label).grid(row=row, column=0, sticky="w", padx=(0, 10), pady=2)
            if field.kind == "choice":
                variable = tk.StringVar()
                widget = ttk.Combobox(inner, textvariable=variable,
                                      values=field.choices, state="readonly", width=30)
            elif field.kind == "bool":
                variable = tk.BooleanVar()
                widget = ttk.Checkbutton(inner, variable=variable)
            elif field.kind == "ascii":
                variable = tk.StringVar()
                widget = ttk.Entry(inner, textvariable=variable, width=22)
            else:
                variable = tk.StringVar()
                widget = ttk.Spinbox(inner, textvariable=variable,
                                     from_=field.minimum, to=field.maximum, width=10)
            widget.grid(row=row, column=1, sticky="w", pady=2)
            self.settings_vars[field.key] = (field, variable)
        inner.columnconfigure(1, weight=1)

    def _build_japanese_tab(self, notebook: ttk.Notebook) -> None:
        tab = ttk.Frame(notebook, padding=8)
        notebook.add(tab, text="日本語リソース")
        ttk.Label(
            tab,
            text="同梱フォントと名前テーブルは別々に書き込めます。既存の一方を変更せずに更新できます。",
        ).grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(
            tab,
            text="任意のBDFはアップロードしません。フォントは固定資産、名前はUTF-8 1024行として事前に検査します。",
            foreground="#9a3412",
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(6, 12))
        ttk.Label(
            tab,
            text="フォント：Izumi 16×16／専用14×14／美咲8×8（{} byte）".format(JAPANESE_FONT_SIZE),
        ).grid(row=2, column=0, columnspan=2, sticky="w")
        ttk.Button(tab, text="フォントを書き込む", command=self._write_japanese_font).grid(
            row=2, column=2, sticky="w")
        ttk.Label(tab, text="名前ファイル（UTF-8、1024行）").grid(
            row=3, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(tab, textvariable=self.name_path, width=72).grid(
            row=3, column=1, sticky="ew", padx=6, pady=(10, 0))
        ttk.Button(tab, text="参照", command=self._choose_names).grid(
            row=3, column=2, sticky="w", pady=(10, 0))
        ttk.Button(tab, text="名前テーブルを書き込む", command=self._write_japanese_names).grid(
            row=4, column=0, sticky="w", pady=12)
        ttk.Button(tab, text="名前テーブルを読み出す", command=self._read_japanese_names).grid(
            row=4, column=1, sticky="w", padx=6, pady=12)
        ttk.Label(
            tab,
            text="font: docs/fonts/japanese_font.bin（固定） / name table: 0x060000–0x067FFF",
        ).grid(row=5, column=0, columnspan=3, sticky="w")
        tab.columnconfigure(1, weight=1)

    @staticmethod
    def _text_box(parent: ttk.Frame, row: int) -> tk.Text:
        frame = ttk.Frame(parent)
        frame.grid(row=row, column=0, columnspan=6, sticky="nsew", pady=(4, 0))
        text = tk.Text(frame, wrap="word", undo=True)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        parent.rowconfigure(row, weight=1)
        parent.columnconfigure(0, weight=1)
        return text

    def _require_session(self) -> RadioSession:
        if self.session is None:
            raise HostToolError("先にJpRxOnly無線機へ接続してください。")
        return self.session

    def _submit(self, label, operation, on_success, error_title) -> None:
        if self._busy:
            self._log("別の通信処理を実行中です。完了するまでお待ちください。")
            return
        self._busy = True
        self._log("{}中です…".format(label))
        self.progress.start(12)

        def runner():
            try:
                result = operation()
            except Exception as exc:
                self._jobs.put((label, None, exc, on_success, error_title))
            else:
                self._jobs.put((label, result, None, on_success, error_title))

        threading.Thread(target=runner, name="wrx-jp-{}".format(label),
                         daemon=True).start()

    def _drain_jobs(self) -> None:
        try:
            while True:
                _label, result, error, on_success, error_title = self._jobs.get_nowait()
                self._busy = False
                self.progress.stop()
                if error is not None:
                    messagebox.showerror(error_title, _format_error(error))
                    continue
                try:
                    on_success(result)
                except Exception as exc:
                    messagebox.showerror(error_title, _format_error(exc))
        except queue.Empty:
            pass
        self.after(50, self._drain_jobs)

    def _finish_memory_read(self, data: bytes) -> None:
        self.memory_text.delete("1.0", "end")
        self.memory_text.insert("1.0", _format_hex(data))
        self._log("メモリーを読み出しました。")

    def _finish_settings_read(self, data: bytes) -> None:
        values = settings.read_settings(data)
        for key, (_field, variable) in self.settings_vars.items():
            variable.set(values[key])
        self.settings_raw = data
        self._log("設定領域を読み出しました。")

    def _finish_settings_write(self, data: bytes) -> None:
        self.settings_raw = data
        self._log("設定を書き込み、内容を確認しました。")

    def _read_channels(self) -> None:
        try:
            session = self._require_session()
        except Exception as exc:
            messagebox.showerror("チャンネル一覧を読み出せません", _format_error(exc))
            return

        def work():
            image = session.read_memory(0x0000, channels.CHANNEL_IMAGE_SIZE)
            name_table = session.read_external_names()
            rows = channels.decode_channel_list(image, name_table)
            return image, name_table, channels.format_channel_list(rows)

        self._submit("チャンネル一覧の読み出し", work,
                     self._finish_channels_read, "チャンネル一覧を読み出せません")

    def _finish_channels_read(self, result) -> None:
        image, name_table, text = result
        self.channel_image_raw = image
        self.channel_names_raw = name_table
        self.channel_text.delete("1.0", "end")
        self.channel_text.insert("1.0", text)
        self._log("1024件のチャンネル一覧を読み出しました。")

    def _write_channels(self) -> None:
        try:
            if self.channel_image_raw is None or self.channel_names_raw is None:
                raise SafetyError("先にチャンネル一覧を読み出してください。")
            rows = channels.parse_channel_list(self.channel_text.get("1.0", "end"))
            old_image = self.channel_image_raw
            old_names = self.channel_names_raw
            image, name_table = channels.encode_channel_list(
                rows, old_image, old_names)
            session = self._require_session()
        except Exception as exc:
            messagebox.showerror("チャンネル一覧を書き込めません", _format_error(exc))
            return

        def work():
            session.write_memory_changed(0x0000, old_image, image)
            session.write_external_changed(
                JAPANESE_NAME_BASE, old_names, name_table)
            return image, name_table

        self._submit("チャンネル一覧の書き込み", work,
                     lambda result: self._finish_channels_write(result),
                     "チャンネル一覧を書き込めません")

    def _finish_channels_write(self, result) -> None:
        self.channel_image_raw, self.channel_names_raw = result
        self._log("チャンネル一覧を書き込み、内容を確認しました。")

    def _load_channels(self) -> None:
        path = filedialog.askopenfilename(
            title="WRX-JPチャンネルTSVを選択",
            filetypes=(("TSVファイル", "*.tsv"), ("すべてのファイル", "*.*")),
        )
        if not path:
            return
        try:
            text = Path(path).read_text(encoding="utf-8")
            channels.parse_channel_list(text)
            self.channel_text.delete("1.0", "end")
            self.channel_text.insert("1.0", text)
            self._log("TSVを読み込みました。書き込む前に内容を確認してください。")
        except Exception as exc:
            messagebox.showerror("TSVを読み込めません", _format_error(exc))

    def _save_channels(self) -> None:
        try:
            text = self.channel_text.get("1.0", "end")
            channels.parse_channel_list(text)
            path = filedialog.asksaveasfilename(
                title="チャンネルTSVを保存", defaultextension=".tsv",
                filetypes=(("TSVファイル", "*.tsv"), ("すべてのファイル", "*.*")),
            )
            if not path:
                return
            Path(path).write_text(text, encoding="utf-8", newline="\n")
            self._log("チャンネルTSVを保存しました。")
        except Exception as exc:
            messagebox.showerror("TSVを保存できません", _format_error(exc))

    def _connect(self) -> None:
        if self._busy:
            self._log("別の通信処理を実行中です。完了するまでお待ちください。")
            return
        port = self.port.get().strip()
        if not port:
            messagebox.showerror("接続できません", "COMポートを選択してください。")
            return

        def work():
            import serial
            transport = serial.Serial(port, BAUD_RATE, timeout=2.0)
            try:
                session = RadioSession(transport)
                firmware = session.connect()
                # 応答の版表示はビルド設定で変わるため、固定文字列で判定しない。
                # WRX-JP専用の外部Flash read commandが通ることを実装確認とする。
                session.probe_external_japanese()
                return transport, session, firmware
            except Exception:
                try:
                    transport.close()
                except Exception:
                    pass
                raise

        def connected(result):
            self.transport, self.session, firmware = result
            self._log("JpRxOnlyと外部フラッシュを確認しました：{}".format(firmware))

        self._submit("接続", work, connected, "接続できません")

    def _disconnect(self) -> None:
        if self._busy:
            self._log("通信中です。処理が完了してから切断してください。")
            return
        if self.transport is not None:
            try:
                self.transport.close()
            except Exception:
                pass
        self.transport = None
        self.session = None
        self.status.set("未接続です")

    def _read_memory(self) -> None:
        try:
            offset = _parse_integer(self.memory_offset.get())
            length = _parse_integer(self.memory_length.get())
            session = self._require_session()
        except Exception as exc:
            messagebox.showerror("メモリーを読み出せません", _format_error(exc))
            return
        self._submit(
            "メモリーの読み出し",
            lambda: session.read_memory(offset, length),
            lambda data: self._finish_memory_read(data),
            "メモリーを読み出せません",
        )

    def _write_memory(self) -> None:
        try:
            offset = _parse_integer(self.memory_offset.get())
            data = _parse_hex(self.memory_text.get("1.0", "end"))
            session = self._require_session()
        except Exception as exc:
            messagebox.showerror("メモリーを書き込めません", _format_error(exc))
            return
        self._submit(
            "メモリーの書き込み",
            lambda: session.write_memory(offset, data),
            lambda _result: self._log("メモリーを書き込み、内容を確認しました。"),
            "メモリーを書き込めません",
        )

    def _read_settings(self) -> None:
        try:
            session = self._require_session()
        except Exception as exc:
            messagebox.showerror("設定を読み出せません", _format_error(exc))
            return
        self._submit(
            "設定の読み出し",
            lambda: session.read_memory(SETTINGS_BASE, SETTINGS_SIZE),
            self._finish_settings_read,
            "設定を読み出せません",
        )

    def _write_settings(self) -> None:
        try:
            if self.settings_raw is None:
                raise SafetyError("先に設定を読み出してください。")
            values = {key: variable.get()
                      for key, (_field, variable) in self.settings_vars.items()}
            data = settings.apply_settings(self.settings_raw, values)
            session = self._require_session()
        except Exception as exc:
            messagebox.showerror("設定を書き込めません", _format_error(exc))
            return
        self._submit(
            "設定の書き込み",
            lambda: session.write_memory(SETTINGS_BASE, data),
            lambda _result: self._finish_settings_write(data),
            "設定を書き込めません",
        )

    def _choose_names(self) -> None:
        path = filedialog.askopenfilename(
            title="1024行のUTF-8名前ファイルを選択",
            filetypes=(("UTF-8テキスト", "*.txt"), ("すべてのファイル", "*.*")),
        )
        if path:
            self.name_path.set(path)

    def _write_japanese_font(self) -> None:
        try:
            font = resources.load_font()
            session = self._require_session()
            if not messagebox.askyesno(
                    "フォントを書き込みます",
                    "同梱フォントを外部フラッシュへ書き込みます。名前テーブルは変更しません。続行しますか？"):
                return
        except Exception as exc:
            messagebox.showerror("フォントを書き込めません", _format_error(exc))
            return
        self._submit(
            "フォントの書き込み",
            lambda: session.write_japanese_font(font),
            lambda _result: self._log("フォントを書き込み、内容を確認しました。"),
            "フォントを書き込めません",
        )

    def _write_japanese_names(self) -> None:
        try:
            path = Path(self.name_path.get())
            if not path.is_file():
                raise ValueError("1024行の名前ファイルを選択してください。")
            name_table = resources.read_name_file(path)
            session = self._require_session()
            if not messagebox.askyesno(
                    "名前テーブルを書き込みます",
                    "1024件の名前テーブルを外部フラッシュへ書き込みます。フォントは変更しません。続行しますか？"):
                return
        except Exception as exc:
            messagebox.showerror("名前テーブルを書き込めません", _format_error(exc))
            return
        self._submit(
            "名前テーブルの書き込み",
            lambda: session.write_japanese_names(name_table),
            lambda _result: self._log("名前テーブルを書き込み、内容を確認しました。"),
            "名前テーブルを書き込めません",
        )

    def _read_japanese_names(self) -> None:
        try:
            session = self._require_session()
        except Exception as exc:
            messagebox.showerror("名前テーブルを読み出せません", _format_error(exc))
            return

        def finish(data):
            path = filedialog.asksaveasfilename(
                title="名前テーブルを保存", defaultextension=".txt",
                filetypes=(("UTF-8テキスト", "*.txt"),))
            if not path:
                return
            names = resources.unpack_name_table(data)
            with Path(path).open("w", encoding="utf-8", newline="\n") as stream:
                stream.write("\n".join(names) + "\n")
            self._log("1024件の名前テーブルを保存しました。")

        self._submit("名前テーブルの読み出し",
                     session.read_external_names,
                     finish, "名前テーブルを読み出せません")

    def _log(self, message: str) -> None:
        self.status.set(message)

    def _close(self) -> None:
        if self._busy:
            self._log("通信中です。処理が完了してから終了してください。")
            return
        self._disconnect()
        self.destroy()


if __name__ == "__main__":
    WRXJPHost().mainloop()
