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
ARRAY_DECLARATION_RE = re.compile(
    r"(?m)^\s*(?:[A-Za-z_]\w*\s+)+[A-Za-z_]\w*(?:\s+__attribute__\s*\(.*?\))?\s+"
    r"(?P<name>[A-Za-z_]\w*)\s*(?P<dimensions>(?:\[[^\]]*\]\s*)+)=\s*\{",
    re.S,
)


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
        value = re.sub(r"^0[xX][0-9A-Fa-f]{2}\s*", "", value).strip()
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


def matching_brace(text: str, opening: int) -> int:
    """Return the closing brace while ignoring braces inside C comments/strings."""

    depth = 0
    in_block_comment = False
    in_line_comment = False
    in_string: str | None = None
    escaped = False
    for position in range(opening, len(text)):
        char = text[position]
        next_char = text[position + 1] if position + 1 < len(text) else ""
        if in_line_comment:
            if char in "\r\n":
                in_line_comment = False
            continue
        if in_block_comment:
            if char == "*" and next_char == "/":
                in_block_comment = False
            continue
        if in_string is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == in_string:
                in_string = None
            continue
        if char == "/" and next_char == "*":
            in_block_comment = True
            continue
        if char == "/" and next_char == "/":
            in_line_comment = True
            continue
        if char in "\"'":
            in_string = char
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return position
            if depth < 0:
                break
    raise ValueError("配列の閉じ括弧を特定できません")


def mask_inactive_preprocessor_lines(text: str) -> str:
    """Mask simple C preprocessor branches without changing character offsets.

    The rainy source keeps an older font in ``#if 0`` before the active array
    contents.  Parsing both branches would duplicate every positional glyph,
    so inactive lines are replaced with spaces while preserving newlines and
    offsets used for diagnostics.
    """

    directive_re = re.compile(r"^\s*#\s*(if|ifdef|ifndef|elif|else|endif)\b(.*)$")
    frames: list[dict[str, bool]] = []
    active = True
    output: list[str] = []
    for line in text.splitlines(keepends=True):
        match = directive_re.match(line.rstrip("\r\n"))
        if match:
            directive, expression = match.groups()
            if directive == "if":
                condition = expression.strip() != "0"
                frames.append({"parent": active, "branch": condition, "taken": condition})
                active = active and condition
            elif directive in {"ifdef", "ifndef"}:
                frames.append({"parent": active, "branch": True, "taken": True})
                active = active
            elif directive in {"elif", "else"}:
                if not frames:
                    raise ValueError(f"対応する#ifのない#{directive}を検出しました")
                frame = frames[-1]
                condition = directive == "else" or expression.strip() != "0"
                branch = condition and not frame["taken"]
                frame["branch"] = branch
                frame["taken"] = frame["taken"] or condition
                active = frame["parent"] and branch
            elif directive == "endif":
                if not frames:
                    raise ValueError("対応する#ifのない#endifを検出しました")
                frame = frames.pop()
                active = frame["parent"]
            output.append(line)
            continue
        if active:
            output.append(line)
        else:
            output.append("".join("\n" if char == "\n" else "\r" if char == "\r" else " " for char in line))
    if frames:
        raise ValueError("閉じられていない#ifを検出しました")
    return "".join(output)


def top_level_initializers(text: str, start: int, end: int) -> list[tuple[int, int]]:
    result: list[tuple[int, int]] = []
    position = start
    while position < end:
        if text.startswith("//", position):
            newline = text.find("\n", position + 2, end)
            position = end if newline < 0 else newline + 1
            continue
        if text.startswith("/*", position):
            close = text.find("*/", position + 2, end)
            position = end if close < 0 else close + 2
            continue
        if text[position] == "{":
            close = matching_brace(text, position)
            if close > end:
                raise ValueError("配列外まで続く初期化子を検出しました")
            result.append((position, close))
            position = close + 1
            continue
        position += 1
    return result


def parse_contiguous_source(
    path: Path,
    array: str,
    array_start: int,
    start: int = 0x80,
    end: int = 0xFF,
    element_width: int = 14,
) -> dict[int, FontEntry]:
    """Parse every positional element of a named C array.

    ``array_start`` is the runtime code point represented by the first active
    element.  Labels are accepted only when an inline code comment agrees with
    the positional code; stale comments cannot silently change the mapping.
    """

    text = path.read_text(encoding="utf-8")
    declaration = next((match for match in ARRAY_DECLARATION_RE.finditer(text) if match.group("name") == array), None)
    if declaration is None:
        raise ValueError(f"配列宣言が見つかりません: {array}")
    opening = declaration.end() - 1
    closing = matching_brace(text, opening)
    body_start, body_end = opening + 1, closing
    masked = mask_inactive_preprocessor_lines(text)
    entries: dict[int, FontEntry] = {}
    for ordinal, (initializer_open, initializer_close) in enumerate(
        top_level_initializers(masked, body_start, body_end)
    ):
        code = array_start + ordinal
        if not start <= code <= end:
            continue
        body = re.sub(r"/\*.*?\*/", "", text[initializer_open + 1 : initializer_close], flags=re.S)
        body = re.sub(r"//[^\r\n]*", "", body)
        values = tuple(int(value, 16) for value in HEX_RE.findall(body))
        if len(values) != element_width:
            raise ValueError(
                f"{path}:{text.count(chr(10), 0, initializer_open) + 1}: "
                f"0x{code:02X} の要素幅が不正です: {len(values)} (expected {element_width})"
            )
        line_end = text.find("\n", initializer_close)
        if line_end < 0:
            line_end = len(text)
        line = text[initializer_open:line_end]
        code_comment = COMMENT_CODE_RE.search(line)
        label = None
        if code_comment and int(code_comment.group(1), 16) == code:
            label = _label(line)
        entries[code] = FontEntry(
            code=code,
            data=values,
            label=label,
            source=path.name,
            line=text.count("\n", 0, initializer_open) + 1,
        )
    if not entries:
        raise ValueError(f"連続配列から対象範囲を読み取れません: {array}")
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


def compare(
    reference: dict[int, FontEntry],
    current: dict[int, FontEntry],
    start: int | None = None,
    end: int | None = None,
    element_width: int = 14,
) -> dict:
    if (start is None) != (end is None):
        raise ValueError("startとendは同時に指定してください")
    codes = list(range(start, end + 1)) if start is not None and end is not None else sorted(set(reference) | set(current))
    rows = []
    for code in codes:
        reference_entry = reference.get(code)
        current_entry = current.get(code)
        if start is not None:
            reference_data = reference_entry.data if reference_entry else (0,) * element_width
            current_data = current_entry.data if current_entry else (0,) * element_width
        else:
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
        if not byte_changes:
            status = "same"
        elif not reference_entry:
            status = "current-only"
        elif not current_entry:
            status = "reference-only"
        else:
            status = "different"
        if reference_entry and current_entry:
            presence = "both"
        elif reference_entry:
            presence = "reference-only"
        elif current_entry:
            presence = "current-only"
        else:
            presence = "neither"
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
                "presence": presence,
                "reference_present": bool(reference_entry),
                "current_present": bool(current_entry),
                "reference_bytes": [f"0x{value:02X}" for value in reference_data],
                "current_bytes": [f"0x{value:02X}" for value in current_data],
                "changed_bytes": byte_changes,
                "changed_bits": changed_bits,
                "reference_only_bits": reference_only_bits,
                "current_only_bits": current_only_bits,
            }
        )
    counts = {status: sum(row["status"] == status for row in rows) for status in ("same", "different", "reference-only", "current-only")}
    presence_counts = {presence: sum(row["presence"] == presence for row in rows) for presence in ("both", "reference-only", "current-only", "neither")}
    return {
        "summary": {
            "codes": len(rows),
            **counts,
            "presence": presence_counts,
            "changed_bytes": sum(len(row["changed_bytes"]) for row in rows),
            "changed_bits": sum(row["changed_bits"] for row in rows),
            "reference_only_bits": sum(row["reference_only_bits"] for row in rows),
            "current_only_bits": sum(row["current_only_bits"] for row in rows),
        },
        "rows": rows,
    }


def make_markdown(
    result: dict,
    reference_paths: list[Path],
    current_paths: list[Path],
    start: int,
    end: int,
    reference_mapping: str = "コード注釈／指定初期化子",
    current_mapping: str = "コード注釈／指定初期化子",
) -> str:
    summary = result["summary"]
    lines = [
        "# 日本語大字形のrainy参照比較",
        "",
        "Cソースの指定した対応付けに従い，参照側と現行側の14-byte大字形を比較した結果です．",
        "このレポートは比較用であり，参照フォントをファームウェアへコピーしたことを意味しません．",
        "",
        f"- 比較範囲: `0x{start:02X}`–`0x{end:02X}`",
        f"- 参照ソース: {', '.join(path.name for path in reference_paths)}",
        f"- 現行ソース: {', '.join(path.name for path in current_paths)}",
        f"- 参照の対応付け: {reference_mapping}",
        f"- 現行の対応付け: {current_mapping}",
        f"- コード数: {summary['codes']}（一致 {summary['same']}，差分 {summary['different']}，参照のみ {summary['reference-only']}，現行のみ {summary['current-only']}）",
        f"- 差分: {summary['changed_bytes']} byte，{summary['changed_bits']} bit（参照のみ {summary['reference_only_bits']} bit，現行のみ {summary['current_only_bits']} bit）",
        f"- ソース上の要素: 両方 {summary['presence']['both']}，参照のみ {summary['presence']['reference-only']}，現行のみ {summary['presence']['current-only']}，両方なし {summary['presence']['neither']}（空白要素も比較）",
        "",
        "| コード | 文字 | 状態 | ソース上の要素 | 変更byte数 | 変更bit数 | 参照byte列 | 現行byte列 |",
        "| --- | --- | --- | --- | ---: | ---: | --- | --- |",
    ]
    for row in result["rows"]:
        label = row["label"] or ""
        reference_bytes = " ".join(row["reference_bytes"])
        current_bytes = " ".join(row["current_bytes"])
        lines.append(
            f"| `{row['code']}` | {label} | {row['status']} | {row['presence']} | {len(row['changed_bytes'])} | {row['changed_bits']} | `{reference_bytes}` | `{current_bytes}` |"
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
    parser.add_argument("--reference-array", help="参照側を指定名の連続配列として位置対応する")
    parser.add_argument("--reference-array-start", type=lambda value: int(value, 0), help="参照側連続配列の先頭コード")
    parser.add_argument("--current-array", help="現行側を指定名の連続配列として位置対応する")
    parser.add_argument("--current-array-start", type=lambda value: int(value, 0), help="現行側連続配列の先頭コード")
    args = parser.parse_args()
    if args.start > args.end:
        parser.error("--start must not exceed --end")
    if args.reference_array and args.reference_array_start is None:
        parser.error("--reference-array-start is required with --reference-array")
    if args.current_array and args.current_array_start is None:
        parser.error("--current-array-start is required with --current-array")
    if args.reference_array and len(args.reference_source) != 1:
        parser.error("連続配列の参照ソースは1つだけ指定してください")
    if args.current_array and len(args.current_source) != 1:
        parser.error("連続配列の現行ソースは1つだけ指定してください")
    if args.reference_array:
        reference = parse_contiguous_source(
            args.reference_source[0], args.reference_array, args.reference_array_start,
            args.start, args.end, args.element_width
        )
        reference_mapping = f"`{args.reference_array}`連続配列を`0x{args.reference_array_start:02X}`起点で順序対応"
    else:
        reference = load_sources(args.reference_source, args.start, args.end, args.element_width)
        reference_mapping = "コード注釈／指定初期化子"
    if args.current_array:
        current = parse_contiguous_source(
            args.current_source[0], args.current_array, args.current_array_start,
            args.start, args.end, args.element_width
        )
        current_mapping = f"`{args.current_array}`連続配列を`0x{args.current_array_start:02X}`起点で順序対応"
    else:
        current = load_sources(args.current_source, args.start, args.end, args.element_width)
        current_mapping = "コード注釈／指定初期化子"
    result = compare(reference, current, args.start, args.end, args.element_width)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "font_diff.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.out / "font_diff.md").write_text(
        make_markdown(
            result, args.reference_source, args.current_source, args.start, args.end,
            reference_mapping, current_mapping,
        ), encoding="utf-8"
    )
    (args.out / "font_diff.svg").write_text(make_svg(result), encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
