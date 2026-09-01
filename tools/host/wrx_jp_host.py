"""Small Windows GUI for the WRX-JP UV-K1 / UV-K5 V3 host contract."""

from __future__ import annotations

import binascii
import queue
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from protocol import (  # type: ignore[no-redef]
        JAPANESE_NAME_SIZE,
        JAPANESE_NAME_BASE,
        RadioSession,
        SafetyError,
        HostToolError,
    )
    import resources  # type: ignore[no-redef]
    import settings  # type: ignore[no-redef]
    import channels  # type: ignore[no-redef]
else:
    from .protocol import (JAPANESE_NAME_BASE, JAPANESE_NAME_SIZE,
                           HostToolError, RadioSession, SafetyError)
    from . import channels, resources, settings


SETTINGS_BASE = 0xA000
SETTINGS_SIZE = 0x170


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


class WRXJPHost(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("WRX-JP Host Tool")
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

        self.port = tk.StringVar(value="COM3")
        self.status = tk.StringVar(value="未接続")
        self.name_path = tk.StringVar()
        self._build_connection_bar()
        self._build_tabs()
        self.after(50, self._drain_jobs)
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _build_connection_bar(self) -> None:
        bar = ttk.Frame(self, padding=8)
        bar.pack(fill="x")
        ttk.Label(bar, text="COMポート").pack(side="left")
        ttk.Entry(bar, textvariable=self.port, width=12).pack(side="left", padx=(6, 8))
        ttk.Button(bar, text="接続", command=self._connect).pack(side="left")
        ttk.Button(bar, text="切断", command=self._disconnect).pack(side="left", padx=4)
        ttk.Label(bar, textvariable=self.status).pack(side="left", padx=12)

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
        ttk.Label(tab, text="論理offset").grid(row=0, column=0, sticky="w")
        self.memory_offset = tk.StringVar(value="0x0000")
        ttk.Entry(tab, textvariable=self.memory_offset, width=12).grid(
            row=0, column=1, sticky="w", padx=6)
        ttk.Label(tab, text="読出し長（byte）").grid(row=0, column=2, sticky="w")
        self.memory_length = tk.StringVar(value="0x80")
        ttk.Entry(tab, textvariable=self.memory_length, width=12).grid(
            row=0, column=3, sticky="w", padx=6)
        ttk.Button(tab, text="読出し", command=self._read_memory).grid(
            row=0, column=4, padx=4)
        ttk.Button(tab, text="書込み", command=self._write_memory).grid(
            row=0, column=5, padx=4)
        ttk.Label(
            tab,
            text="calibration（0xB000–0xB1FF）は読出しのみ。書込みは常に拒否する。",
            foreground="#9a3412",
        ).grid(row=1, column=0, columnspan=6, sticky="w", pady=(8, 4))
        self.memory_text = self._text_box(tab, 2)

    def _build_channels_tab(self, notebook: ttk.Notebook) -> None:
        tab = ttk.Frame(notebook, padding=8)
        notebook.add(tab, text="チャンネル一覧")
        ttk.Label(
            tab,
            text="1024件の通常チャンネルをTSVで読出し・編集・書込みする。",
        ).grid(row=0, column=0, columnspan=6, sticky="w")
        ttk.Label(
            tab,
            text="周波数・mode・tone・step・scan list・名前を扱う。RX-onlyのため送信周波数は保持しない。",
            foreground="#9a3412",
        ).grid(row=1, column=0, columnspan=6, sticky="w", pady=(6, 8))
        ttk.Button(tab, text="無線機から読出し", command=self._read_channels).grid(
            row=2, column=0, sticky="w")
        ttk.Button(tab, text="書込み", command=self._write_channels).grid(
            row=2, column=1, sticky="w", padx=4)
        ttk.Button(tab, text="TSVを読込", command=self._load_channels).grid(
            row=2, column=2, sticky="w", padx=4)
        ttk.Button(tab, text="TSVを保存", command=self._save_channels).grid(
            row=2, column=3, sticky="w", padx=4)
        ttk.Label(
            tab,
            text="fontは「日本語リソース」タブで先に書込む。calibrationはこの操作の対象外。",
            foreground="#9a3412",
        ).grid(row=3, column=0, columnspan=6, sticky="w", pady=(8, 4))
        self.channel_text = self._text_box(tab, 4)

    def _build_settings_tab(self, notebook: ttk.Notebook) -> None:
        tab = ttk.Frame(notebook, padding=8)
        notebook.add(tab, text="設定")
        ttk.Label(
            tab,
            text="確認済みのRX-safe設定／FM領域 0xA000–0xA16F。F4HWN互換の項目名で編集する。",
        ).grid(row=0, column=0, columnspan=4, sticky="w")
        ttk.Label(
            tab,
            text="未知byteは保持し、既知のBasic／Display／Keys／Scan／F4HWN／Logo／FM項目だけを更新する。",
            foreground="#9a3412",
        ).grid(row=1, column=0, columnspan=4, sticky="w", pady=(6, 8))
        ttk.Button(tab, text="読出し", command=self._read_settings).grid(
            row=2, column=0, sticky="w", pady=(0, 6))
        ttk.Button(tab, text="書込み", command=self._write_settings).grid(
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
            text="固定同梱のIzumi 16 fontと1024件のUTF-8名前テーブルを一つの操作で書き込む。",
        ).grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(
            tab,
            text="任意BDFのアップロードは行わない。31 UTF-8 byte、文字集合、表示幅を事前検査する。",
            foreground="#9a3412",
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(6, 12))
        ttk.Label(tab, text="名前ファイル（UTF-8、1024行）").grid(
            row=2, column=0, sticky="w")
        ttk.Entry(tab, textvariable=self.name_path, width=72).grid(
            row=2, column=1, sticky="ew", padx=6)
        ttk.Button(tab, text="参照", command=self._choose_names).grid(
            row=2, column=2, sticky="w")
        ttk.Button(tab, text="日本語リソースを書込み", command=self._write_japanese).grid(
            row=3, column=0, sticky="w", pady=12)
        ttk.Button(tab, text="名前テーブルを読出し", command=self._read_japanese_names).grid(
            row=3, column=1, sticky="w", padx=6, pady=12)
        ttk.Label(
            tab,
            text="font: docs/fonts/japanese_font.bin（固定） / name table: 0x040000–0x047FFF",
        ).grid(row=4, column=0, columnspan=3, sticky="w")
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
            raise HostToolError("先にJpRxOnly無線機へ接続する")
        return self.session

    def _submit(self, label, operation, on_success, error_title) -> None:
        if self._busy:
            self._log("別の通信処理が実行中")
            return
        self._busy = True
        self._log("{}中…".format(label))

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
                if error is not None:
                    messagebox.showerror(error_title, str(error))
                    continue
                try:
                    on_success(result)
                except Exception as exc:
                    messagebox.showerror(error_title, str(exc))
        except queue.Empty:
            pass
        self.after(50, self._drain_jobs)

    def _finish_memory_read(self, data: bytes) -> None:
        self.memory_text.delete("1.0", "end")
        self.memory_text.insert("1.0", _format_hex(data))
        self._log("メモリー読出し完了")

    def _finish_settings_read(self, data: bytes) -> None:
        values = settings.read_settings(data)
        for key, (_field, variable) in self.settings_vars.items():
            variable.set(values[key])
        self.settings_raw = data
        self._log("設定領域読出し完了")

    def _finish_settings_write(self, data: bytes) -> None:
        self.settings_raw = data
        self._log("設定書込み・readback完了")

    def _read_channels(self) -> None:
        try:
            session = self._require_session()
        except Exception as exc:
            messagebox.showerror("チャンネル読出しエラー", str(exc))
            return

        def work():
            image = session.read_memory(0x0000, channels.CHANNEL_IMAGE_SIZE)
            name_table = session.read_external_names()
            rows = channels.decode_channel_list(image, name_table)
            return image, name_table, channels.format_channel_list(rows)

        self._submit("チャンネル一覧読出し", work,
                     self._finish_channels_read, "チャンネル読出しエラー")

    def _finish_channels_read(self, result) -> None:
        image, name_table, text = result
        self.channel_image_raw = image
        self.channel_names_raw = name_table
        self.channel_text.delete("1.0", "end")
        self.channel_text.insert("1.0", text)
        self._log("1024件のチャンネル一覧読出し完了")

    def _write_channels(self) -> None:
        try:
            if self.channel_image_raw is None or self.channel_names_raw is None:
                raise SafetyError("先にチャンネル一覧を読出す")
            rows = channels.parse_channel_list(self.channel_text.get("1.0", "end"))
            old_image = self.channel_image_raw
            old_names = self.channel_names_raw
            image, name_table = channels.encode_channel_list(
                rows, old_image, old_names)
            session = self._require_session()
        except Exception as exc:
            messagebox.showerror("チャンネル書込みエラー", str(exc))
            return

        def work():
            session.write_memory_changed(0x0000, old_image, image)
            session.write_external_changed(
                JAPANESE_NAME_BASE, old_names, name_table)
            return image, name_table

        self._submit("チャンネル一覧書込み", work,
                     lambda result: self._finish_channels_write(result),
                     "チャンネル書込みエラー")

    def _finish_channels_write(self, result) -> None:
        self.channel_image_raw, self.channel_names_raw = result
        self._log("チャンネル一覧書込み・readback完了")

    def _load_channels(self) -> None:
        path = filedialog.askopenfilename(
            title="WRX-JPチャンネルTSVを選択",
            filetypes=(("TSV text", "*.tsv"), ("All files", "*.*")),
        )
        if not path:
            return
        try:
            text = Path(path).read_text(encoding="utf-8")
            channels.parse_channel_list(text)
            self.channel_text.delete("1.0", "end")
            self.channel_text.insert("1.0", text)
            self._log("TSVを読込（書込み前に内容を確認する）")
        except Exception as exc:
            messagebox.showerror("TSV読込エラー", str(exc))

    def _save_channels(self) -> None:
        try:
            text = self.channel_text.get("1.0", "end")
            channels.parse_channel_list(text)
            path = filedialog.asksaveasfilename(
                title="チャンネルTSVを保存", defaultextension=".tsv",
                filetypes=(("TSV text", "*.tsv"), ("All files", "*.*")),
            )
            if not path:
                return
            Path(path).write_text(text, encoding="utf-8", newline="\n")
            self._log("チャンネルTSVを保存")
        except Exception as exc:
            messagebox.showerror("TSV保存エラー", str(exc))

    def _connect(self) -> None:
        if self._busy:
            self._log("別の通信処理が実行中")
            return
        port = self.port.get().strip()
        if not port:
            messagebox.showerror("接続エラー", "COMポートを指定する")
            return

        def work():
            import serial
            transport = serial.Serial(port, 38400, timeout=0.5)
            try:
                session = RadioSession(transport)
                firmware = session.connect()
                if not any(marker in firmware.lower() for marker in ("j1", "wrx", "jp")):
                    raise HostToolError(
                        "JpRxOnlyの確認に失敗した（応答: {!r}）".format(firmware))
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
            self._log("JpRxOnly／外部Flashコマンド確認: {}".format(firmware))

        self._submit("接続", work, connected, "接続エラー")

    def _disconnect(self) -> None:
        if self._busy:
            self._log("通信中のため切断を待機")
            return
        if self.transport is not None:
            try:
                self.transport.close()
            except Exception:
                pass
        self.transport = None
        self.session = None
        self.status.set("未接続")

    def _read_memory(self) -> None:
        try:
            offset = _parse_integer(self.memory_offset.get())
            length = _parse_integer(self.memory_length.get())
            session = self._require_session()
        except Exception as exc:
            messagebox.showerror("読出しエラー", str(exc))
            return
        self._submit(
            "メモリー読出し",
            lambda: session.read_memory(offset, length),
            lambda data: self._finish_memory_read(data),
            "読出しエラー",
        )

    def _write_memory(self) -> None:
        try:
            offset = _parse_integer(self.memory_offset.get())
            data = _parse_hex(self.memory_text.get("1.0", "end"))
            session = self._require_session()
        except Exception as exc:
            messagebox.showerror("書込みエラー", str(exc))
            return
        self._submit(
            "メモリー書込み",
            lambda: session.write_memory(offset, data),
            lambda _result: self._log("メモリー書込み・readback完了"),
            "書込みエラー",
        )

    def _read_settings(self) -> None:
        try:
            session = self._require_session()
        except Exception as exc:
            messagebox.showerror("設定読出しエラー", str(exc))
            return
        self._submit(
            "設定読出し",
            lambda: session.read_memory(SETTINGS_BASE, SETTINGS_SIZE),
            self._finish_settings_read,
            "設定読出しエラー",
        )

    def _write_settings(self) -> None:
        try:
            if self.settings_raw is None:
                raise SafetyError("先に設定を読出す")
            values = {key: variable.get()
                      for key, (_field, variable) in self.settings_vars.items()}
            data = settings.apply_settings(self.settings_raw, values)
            session = self._require_session()
        except Exception as exc:
            messagebox.showerror("設定書込みエラー", str(exc))
            return
        self._submit(
            "設定書込み",
            lambda: session.write_memory(SETTINGS_BASE, data),
            lambda _result: self._finish_settings_write(data),
            "設定書込みエラー",
        )

    def _choose_names(self) -> None:
        path = filedialog.askopenfilename(
            title="1024行のUTF-8名前ファイルを選択",
            filetypes=(("UTF-8 text", "*.txt"), ("All files", "*.*")),
        )
        if path:
            self.name_path.set(path)

    def _write_japanese(self) -> None:
        try:
            path = Path(self.name_path.get())
            if not path.is_file():
                raise ValueError("1024行の名前ファイルを選択する")
            name_table = resources.read_name_file(path)
            font = resources.load_font()
            if len(name_table) != JAPANESE_NAME_SIZE:
                raise SafetyError("名前テーブルのサイズが不正")
            if not messagebox.askyesno(
                    "日本語リソース書込み",
                    "固定fontと1024件の名前を外部Flashへ書き込む。続行する？"):
                return
            session = self._require_session()
        except Exception as exc:
            messagebox.showerror("日本語リソース書込みエラー", str(exc))
            return
        self._submit(
            "日本語リソース書込み",
            lambda: session.write_japanese_resource(font, name_table),
            lambda _result: self._log("日本語リソース書込み・readback完了"),
            "日本語リソース書込みエラー",
        )

    def _read_japanese_names(self) -> None:
        try:
            session = self._require_session()
        except Exception as exc:
            messagebox.showerror("名前読出しエラー", str(exc))
            return

        def finish(data):
            path = filedialog.asksaveasfilename(
                title="名前テーブルを保存", defaultextension=".txt",
                filetypes=(("UTF-8 text", "*.txt"),))
            if not path:
                return
            names = resources.unpack_name_table(data)
            with Path(path).open("w", encoding="utf-8", newline="\n") as stream:
                stream.write("\n".join(names) + "\n")
            self._log("1024件の名前テーブルを保存")

        self._submit("名前テーブル読出し",
                     session.read_external_names,
                     finish, "名前読出しエラー")

    def _log(self, message: str) -> None:
        self.status.set(message)

    def _close(self) -> None:
        if self._busy:
            self._log("通信中のため終了を待機")
            return
        self._disconnect()
        self.destroy()


if __name__ == "__main__":
    WRXJPHost().mainloop()
