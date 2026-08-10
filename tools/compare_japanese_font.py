#!/usr/bin/env python3
"""Compare Japanese 7x16 glyph bytes with a reference C source.

This tool reads source initializers only.  It does not copy reference font
data into the firmware and it does not change either source file.
"""

from __future__ import annotations

import argparse
import html
import json
import re
from dataclasses import dataclass
from pathlib import Path


HEX_RE = re.compile(r"0[xX][0-9A-Fa-f]+")
COMMENT_CODE_RE = re.compile(r"//\s*0[xX]([0-9A-Fa-f]{2})\b")
DESIGNATED_CODE_RE = re.compile(r"\[\s*0[xX]([0-9A-Fa-f]{2})\s*-\s*0[xX]7[Ff]\s*\]")
INITIALIZER_RE = re.compile(r"\{(?P<body>[^{}]*)\}")


@dataclass(frozen=True)
class FontEntry:
    code: int
    data: tuple[int, ...]
    label: str | None
    source: str
    line: int


def _label(line: str) -> str | None:
    comments = line.split("//")[1:]
    for comment in comments:
        value = re.sub(r"\s+", " ", comment).strip()
        if not value or re.fullmatch(r"0[xX][0-9A-Fa-f]{2}", value):
            continue
        return value
    return None


def parse_source(path: Path, start: int = 0x80, end: int = 0xFF, element_width: int = 14) -> dict[int, FontEntry]:
    """Read Japanese entries identified by a source comment or designation."""

    entries: dict[int, FontEntry] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        match = INITIALIZER_RE.search(line)
        if not match:
            continue
        code_match = COMMENT_CODE_RE.search(line) or DESIGNATED_CODE_RE.search(line)
        if not code_match:
            continue
        code = int(code_match.group(1), 16)
        if not start <= code <= end:
            continue
        body = re.sub(r"/\*.*?\*/", "", match.group("body"))
        values = tuple(int(value, 16) for value in HEX_RE.findall(body))
        if len(values) != element_width:
            continue
        entry = FontEntry(code, values, _label(line), path.name, line_number)
        previous = entries.get(code)
        if previous and previous.data != entry.data:
            raise ValueError(f"{path}:{line_number}: duplicate 0x{code:02X} with different bytes")
        entries[code] = entry
    return entries


def load_sources(paths: list[Path], start: int, end: int, element_width: int = 14) -> dict[int, FontEntry]:
    entries: dict[int, FontEntry] = {}
    for path in paths:
        for code, entry in parse_source(path, start, end, element_width).items():
            previous = entries.get(code)
            if previous and previous.data != entry.data:
                raise ValueError(
                    f"duplicate 0x{code:02X}: {previous.source}:{previous.line} and {entry.source}:{entry.line}"
                )
            entries[code] = entry
    return entries


def _byte(data: tuple[int, ...] | None, index: int) -> int:
    return data[index] if data and index < len(data) else 0


def compare(reference: dict[int, FontEntry], current: dict[int, FontEntry]) -> dict:
    codes = sorted(set(reference) | set(current))
    rows = []
    for code in codes:
        reference_entry = reference.get(code)
        current_entry = current.get(code)
        reference_data = reference_entry.data if reference_entry else ()
        current_data = current_entry.data if current_entry else ()
        length = max(len(reference_data), len(current_data))
        byte_changes = [index for index in range(length) if _byte(reference_data, index) != _byte(current_data, index)]
        changed_bits = sum((_byte(reference_data, index) ^ _byte(current_data, index)).bit_count() for index in range(length))
        reference_only_bits = sum(
            (_byte(reference_data, index) & ~_byte(current_data, index)).bit_count() for index in range(length)
        )
        current_only_bits = sum(
            (_byte(current_data, index) & ~_byte(reference_data, index)).bit_count() for index in range(length)
        )
        if not reference_entry:
            status = "current-only"
        elif not current_entry:
            status = "reference-only"
        elif not byte_changes:
            status = "same"
        else:
            status = "different"
        rows.append(
            {
                "code": f"0x{code:02X}",
                "code_value": code,
                "label": (
                    current_entry.label
                    if current_entry and current_entry.label
                    else reference_entry.label
                    if reference_entry
                    else None
                ),
                "status": status,
                "reference_bytes": [f"0x{value:02X}" for value in reference_data],
                "current_bytes": [f"0x{value:02X}" for value in current_data],
                "changed_bytes": byte_changes,
                "changed_bits": changed_bits,
                "reference_only_bits": reference_only_bits,
                "current_only_bits": current_only_bits,
            }
        )
    counts = {status: sum(row["status"] == status for row in rows) for status in ("same", "different", "reference-only", "current-only")}
    return {
        "summary": {
            "codes": len(rows),
            **counts,
            "changed_bytes": sum(len(row["changed_bytes"]) for row in rows),
            "changed_bits": sum(row["changed_bits"] for row in rows),
            "reference_only_bits": sum(row["reference_only_bits"] for row in rows),
            "current_only_bits": sum(row["current_only_bits"] for row in rows),
        },
        "rows": rows,
    }


def make_markdown(result: dict, reference_paths: list[Path], current_paths: list[Path], start: int, end: int) -> str:
    summary = result["summary"]
    lines = [
        "# 日本語大字形のrainy参照比較",
        "",
        "Cソースのコード注釈／指定初期化子から，参照側と現行側の14-byte大字形を比較した結果です．",
        "このレポートは比較用であり，参照フォントをファームウェアへコピーしたことを意味しません．",
        "",
        f"- 比較範囲: `0x{start:02X}`–`0x{end:02X}`",
        f"- 参照ソース: {', '.join(path.name for path in reference_paths)}",
        f"- 現行ソース: {', '.join(path.name for path in current_paths)}",
        f"- コード数: {summary['codes']}（一致 {summary['same']}，差分 {summary['different']}，参照のみ {summary['reference-only']}，現行のみ {summary['current-only']}）",
        f"- 差分: {summary['changed_bytes']} byte，{summary['changed_bits']} bit（参照のみ {summary['reference_only_bits']} bit，現行のみ {summary['current_only_bits']} bit）",
        "",
        "| コード | 文字 | 状態 | 変更byte数 | 変更bit数 | 参照byte列 | 現行byte列 |",
        "| --- | --- | --- | ---: | ---: | --- | --- |",
    ]
    for row in result["rows"]:
        label = row["label"] or ""
        reference_bytes = " ".join(row["reference_bytes"])
        current_bytes = " ".join(row["current_bytes"])
        lines.append(
            f"| `{row['code']}` | {label} | {row['status']} | {len(row['changed_bytes'])} | {row['changed_bits']} | `{reference_bytes}` | `{current_bytes}` |"
        )
    return "\n".join(lines) + "\n"


def make_svg(result: dict, scale: int = 3, columns: int = 8, width: int = 7, rows: int = 16) -> str:
    tile_width = width * scale + 12
    tile_height = rows * scale + 32
    margin = 16
    legend_height = 32
    tile_rows = (len(result["rows"]) + columns - 1) // columns
    svg_width = margin * 2 + columns * tile_width
    svg_height = margin * 2 + legend_height + tile_rows * tile_height
    output = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_width}" height="{svg_height}" viewBox="0 0 {svg_width} {svg_height}">',
        '<style>text{font-family:system-ui,sans-serif;font-size:11px}.grid{stroke:#d9dee5;stroke-width:.5}.same{fill:#151a20}.reference-only{fill:#1976d2}.current-only{fill:#c62828}.empty{fill:#fff}</style>',
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="16" y="20">rainy参照比較: 黒=双方点灯，青=参照のみ，赤=現行のみ</text>',
    ]
    for index, row in enumerate(result["rows"]):
        tile_x = margin + (index % columns) * tile_width
        tile_y = margin + legend_height + (index // columns) * tile_height
        output.append(f'<text x="{tile_x}" y="{tile_y + 11}">{html.escape(row["code"] + " " + (row["label"] or ""))}</text>')
        grid_y = tile_y + 16
        reference = tuple(int(value, 16) for value in row["reference_bytes"])
        current = tuple(int(value, 16) for value in row["current_bytes"])
        for y in range(rows):
            for x in range(width):
                reference_on = bool(_byte(reference, (y // 8) * width + x) & (1 << (y % 8)))
                current_on = bool(_byte(current, (y // 8) * width + x) & (1 << (y % 8)))
                if reference_on and current_on:
                    klass = "same"
                elif reference_on:
                    klass = "reference-only"
                elif current_on:
                    klass = "current-only"
                else:
                    klass = "empty"
                output.append(
                    f'<rect class="{klass} grid" x="{tile_x + x * scale}" y="{grid_y + y * scale}" width="{scale}" height="{scale}"/>'
                )
    output.append("</svg>")
    return "\n".join(output) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-source", action="append", type=Path, required=True)
    parser.add_argument("--current-source", action="append", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--start", type=lambda value: int(value, 0), default=0x80)
    parser.add_argument("--end", type=lambda value: int(value, 0), default=0xDF)
    parser.add_argument("--element-width", type=int, default=14, help="比較する1字形のbyte数（通常大字形は14）")
    args = parser.parse_args()
    if args.start > args.end:
        parser.error("--start must not exceed --end")
    reference = load_sources(args.reference_source, args.start, args.end, args.element_width)
    current = load_sources(args.current_source, args.start, args.end, args.element_width)
    result = compare(reference, current)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "font_diff.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.out / "font_diff.md").write_text(
        make_markdown(result, args.reference_source, args.current_source, args.start, args.end), encoding="utf-8"
    )
    (args.out / "font_diff.svg").write_text(make_svg(result), encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
