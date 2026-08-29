#!/usr/bin/env python3
"""Safely round-trip annotated C bitmap-font arrays through JSON.

The JSON document is a full snapshot, not an unanchored list of line numbers.
Applying it verifies the source bytes recorded at extraction time and splices
only the initializer bodies belonging to the selected code points.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


FORMAT = "wrx-jp-font-source-v1"
LEGACY_PATCH_FORMAT = "wrx-jp-font-patch-v1"
HEX_RE = re.compile(r"0[xX][0-9A-Fa-f]+|\b[0-9]+\b")
DESIGNATED_RE = re.compile(
    r"\[\s*(?P<code>0[xX][0-9A-Fa-f]+)\s*-\s*(?P<base>0[xX][0-9A-Fa-f]+)\s*\]"
)
CODE_COMMENT_RE = re.compile(r"//\s*(?P<code>0[xX][0-9A-Fa-f]+)\b(?P<label>[^\r\n]*)")


@dataclass(frozen=True)
class SourceEntry:
    code: int
    index: int
    label: str
    values: tuple[int, ...]
    open_start: int
    close_end: int


@dataclass(frozen=True)
class ArraySource:
    name: str
    occurrence: int
    dimensions: tuple[str, ...]
    element_width: int
    body_start: int
    body_end: int
    entries: tuple[SourceEntry, ...]


def fail(message: str) -> "NoReturn":
    raise ValueError(message)


def strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    return re.sub(r"//[^\r\n]*", " ", text)


def matching_brace(text: str, opening: int) -> int:
    depth = 0
    in_block = False
    in_line = False
    in_string: str | None = None
    escaped = False
    for pos in range(opening, len(text)):
        char = text[pos]
        nxt = text[pos + 1] if pos + 1 < len(text) else ""
        if in_line:
            if char in "\r\n":
                in_line = False
            continue
        if in_block:
            if char == "*" and nxt == "/":
                in_block = False
            continue
        if in_string is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == in_string:
                in_string = None
            continue
        if char == "/" and nxt == "*":
            in_block = True
            continue
        if char == "/" and nxt == "/":
            in_line = True
            continue
        if char in "\"'":
            in_string = char
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return pos
            if depth < 0:
                break
    fail("閉じ括弧を特定できません")


def parse_values(body: str) -> tuple[int, ...]:
    cleaned = strip_comments(body)
    values: list[int] = []
    for token in HEX_RE.findall(cleaned):
        value = int(token, 0)
        if not 0 <= value <= 0xFF:
            fail(f"バイト値が範囲外です: {token}")
        values.append(value)
    return tuple(values)


def declaration_pattern(name: str) -> re.Pattern[str]:
    return re.compile(
        r"(?m)^\s*(?:const\s+)?[A-Za-z_]\w*(?:\s+__attribute__\s*\(.*?\))?\s+"
        + re.escape(name)
        + r"\s*(?P<dims>(?:\[[^\]]*\]\s*)+)=\s*\{",
        re.S,
    )


def parse_dimensions(text: str) -> tuple[str, ...]:
    return tuple(part.strip()[1:-1].strip() for part in re.findall(r"\[[^\]]*\]", text))


def top_level_initializers(text: str, start: int, end: int) -> list[tuple[int, int]]:
    result: list[tuple[int, int]] = []
    pos = start
    while pos < end:
        char = text[pos]
        if char == "/" and pos + 1 < end and text[pos + 1] == "/":
            newline = text.find("\n", pos + 2, end)
            pos = end if newline < 0 else newline + 1
            continue
        if char == "/" and pos + 1 < end and text[pos + 1] == "*":
            close = text.find("*/", pos + 2, end)
            pos = end if close < 0 else close + 2
            continue
        if char == "{":
            close = matching_brace(text, pos)
            if close > end:
                fail("配列外まで続く初期化子を検出しました")
            result.append((pos, close))
            pos = close + 1
            continue
        pos += 1
    return result


def parse_array(text: str, name: str, occurrence: int = 1, start_code: int | None = None) -> ArraySource:
    matches = list(declaration_pattern(name).finditer(text))
    if not matches:
        fail(f"配列宣言が見つかりません: {name}")
    if occurrence < 1 or occurrence > len(matches):
        fail(f"配列の出現番号が範囲外です: {name} ({occurrence}/{len(matches)})")
    match = matches[occurrence - 1]
    opening = match.end() - 1
    closing = matching_brace(text, opening)
    body_start, body_end = opening + 1, closing
    entries: list[SourceEntry] = []
    seen: set[int] = set()

    line_start = body_start
    while line_start < body_end:
        line_end = text.find("\n", line_start, body_end)
        if line_end < 0:
            line_end = body_end
        line = text[line_start:line_end]
        designated = DESIGNATED_RE.search(line)
        comment = CODE_COMMENT_RE.search(line)
        code: int | None = None
        label = ""
        initializer_start: int | None = None
        if designated:
            code = int(designated.group("code"), 0)
            initializer_start = line.find("{", designated.end())
            if initializer_start >= 0:
                label_match = re.search(r"//(.*)$", line)
                label = label_match.group(1).strip() if label_match else ""
        elif comment:
            initializer_start = line.find("{")
            if initializer_start >= 0 and initializer_start < comment.start():
                code = int(comment.group("code"), 0)
                label = comment.group("label").strip()
        if code is not None and initializer_start is not None:
            opening_pos = line_start + initializer_start
            if opening_pos < body_start or opening_pos >= body_end:
                fail(f"配列外の初期化子を検出しました: {name} 0x{code:02X}")
            closing_pos = matching_brace(text, opening_pos)
            if closing_pos > body_end:
                fail(f"配列外まで続く初期化子を検出しました: {name} 0x{code:02X}")
            values = parse_values(text[opening_pos + 1 : closing_pos])
            if code in seen:
                fail(f"コードポイントが重複しています: {name} 0x{code:02X}")
            seen.add(code)
            entries.append(
                SourceEntry(
                    code=code,
                    index=code - 0x7F,
                    label=label,
                    values=values,
                    open_start=opening_pos,
                    close_end=closing_pos + 1,
                )
            )
        line_start = line_end + 1

    if not entries and start_code is not None:
        for ordinal, (opening_pos, closing_pos) in enumerate(top_level_initializers(text, body_start, body_end)):
            values = parse_values(text[opening_pos + 1 : closing_pos])
            if not values:
                continue
            entries.append(
                SourceEntry(
                    code=start_code + ordinal,
                    index=ordinal,
                    label="",
                    values=values,
                    open_start=opening_pos,
                    close_end=closing_pos + 1,
                )
            )
    if not entries:
        fail(f"コードポイント付き初期化子が見つかりません: {name}（無注釈配列は--start-codeを指定）")
    widths = {len(entry.values) for entry in entries}
    if len(widths) != 1:
        fail(f"要素幅が一致しません: {sorted(widths)}")
    element_width = widths.pop()
    return ArraySource(
        name=name,
        occurrence=occurrence,
        dimensions=parse_dimensions(match.group("dims")),
        element_width=element_width,
        body_start=body_start,
        body_end=body_end,
        entries=tuple(entries),
    )


def fingerprint(entries: Iterable[SourceEntry]) -> str:
    canonical = "\n".join(
        f"{entry.code:04X}:" + ",".join(f"{value:02X}" for value in entry.values)
        for entry in sorted(entries, key=lambda item: item.code)
    )
    return hashlib.sha256(canonical.encode("ascii")).hexdigest()


def hex_bytes(values: Iterable[int]) -> str:
    return " ".join(f"{value:02X}" for value in values)


def parse_hex_bytes(value: object, width: int, field: str) -> tuple[int, ...]:
    if isinstance(value, list):
        values = tuple(int(item) for item in value)
    elif isinstance(value, str):
        tokens = re.findall(r"[0-9A-Fa-f]{2}", value)
        values = tuple(int(token, 16) for token in tokens)
    else:
        fail(f"{field} はバイト配列または16進文字列で指定してください")
    if len(values) != width or any(not 0 <= item <= 0xFF for item in values):
        fail(f"{field} の長さまたは値が不正です: {len(values)} bytes")
    return values


def extract_document(source: Path, array: str, occurrence: int, start_code: int | None = None) -> dict:
    text = source.read_bytes().decode("utf-8")
    parsed = parse_array(text, array, occurrence, start_code)
    return {
        "format": FORMAT,
        "source": source.name,
        "array": parsed.name,
        "occurrence": parsed.occurrence,
        "dimensions": list(parsed.dimensions),
        "element_width": parsed.element_width,
        "index_base": f"0x{(start_code if start_code is not None else 0x7F):02X}",
        "array_fingerprint": fingerprint(parsed.entries),
        "elements": [
            {
                "code": f"0x{entry.code:02X}",
                "index": entry.index,
                "label": entry.label,
                "base_bytes_hex": hex_bytes(entry.values),
                "bytes_hex": hex_bytes(entry.values),
            }
            for entry in sorted(parsed.entries, key=lambda item: item.code)
        ],
    }


def normalize_code(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value.strip(), 0)
    fail(f"コードポイントが不正です: {value!r}")


def format_initializer(values: Iterable[int]) -> str:
    return ",".join(f"0x{value:02x}" for value in values)


def apply_document(source: Path, document: dict, output: Path, legacy_patch: bool = False) -> int:
    text = source.read_bytes().decode("utf-8")
    if document.get("format") == FORMAT:
        array = document.get("array")
        occurrence = int(document.get("occurrence", 1))
        if not isinstance(array, str):
            fail("JSONの array がありません")
        if document.get("source") and document["source"] != source.name:
            fail(f"JSONのsourceと対象Cファイルが異なります: {document['source']} != {source.name}")
        index_base = document.get("index_base")
        start_code = normalize_code(index_base) if index_base is not None else None
        parsed = parse_array(text, array, occurrence, start_code)
        if document.get("dimensions") and tuple(document["dimensions"]) != parsed.dimensions:
            fail(f"配列次元が一致しません: JSON={document['dimensions']}, C={parsed.dimensions}")
        width = int(document.get("element_width", parsed.element_width))
        if width != parsed.element_width:
            fail(f"要素幅が一致しません: JSON={width}, C={parsed.element_width}")
        elements = document.get("elements")
        if not isinstance(elements, list):
            fail("JSONの elements が配列ではありません")
        current_by_code = {entry.code: entry for entry in parsed.entries}
        json_by_code: dict[int, dict] = {}
        for item in elements:
            if not isinstance(item, dict):
                fail("elements にオブジェクト以外が含まれています")
            code = normalize_code(item.get("code"))
            if code in json_by_code:
                fail(f"JSON内でコードポイントが重複しています: 0x{code:02X}")
            json_by_code[code] = item
        if set(json_by_code) != set(current_by_code):
            missing = sorted(set(current_by_code) - set(json_by_code))
            extra = sorted(set(json_by_code) - set(current_by_code))
            fail(f"JSONとCのコードポイント集合が異なります: missing={missing}, extra={extra}")
        if document.get("array_fingerprint") and document["array_fingerprint"] != fingerprint(parsed.entries):
            fail("抽出後にC配列の基準値が変わっています。再抽出してから編集してください")
        replacements: list[tuple[int, int, str]] = []
        for code, entry in current_by_code.items():
            item = json_by_code[code]
            base = parse_hex_bytes(item.get("base_bytes_hex"), width, f"0x{code:02X}.base_bytes_hex")
            if base != entry.values:
                fail(f"0x{code:02X} のC側がJSON抽出時から変更されています。再抽出してください")
            values = parse_hex_bytes(item.get("bytes_hex"), width, f"0x{code:02X}.bytes_hex")
            if values != entry.values:
                replacements.append((entry.open_start + 1, entry.close_end - 1, format_initializer(values)))
    elif document.get("format") == LEGACY_PATCH_FORMAT and legacy_patch:
        array = document.get("array")
        if not isinstance(array, str):
            fail("旧パッチJSONの array がありません")
        parsed = parse_array(text, array, int(document.get("occurrence", 1)))
        current_by_code = {entry.code: entry for entry in parsed.entries}
        replacements = []
        for item in document.get("changes", []):
            code = normalize_code(item.get("code"))
            if code not in current_by_code:
                fail(f"旧パッチのコードポイントがC配列にありません: 0x{code:02X}")
            raw = item.get("bytes_hex", item.get("bytes"))
            values = parse_hex_bytes(raw, parsed.element_width, f"0x{code:02X}.bytes")
            entry = current_by_code[code]
            replacements.append((entry.open_start + 1, entry.close_end - 1, format_initializer(values)))
    else:
        fail(f"未対応のJSON形式です: {document.get('format')!r}")

    for start, end, replacement in sorted(replacements, reverse=True):
        text = text[:start] + replacement + text[end:]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(text.encode("utf-8"))
    return len(replacements)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    extract = sub.add_parser("extract", help="C配列を完全スナップショットJSONへ変換")
    extract.add_argument("--source", type=Path, required=True)
    extract.add_argument("--array", required=True)
    extract.add_argument("--occurrence", type=int, default=1)
    extract.add_argument("--start-code", type=lambda value: int(value, 0), help="無注釈の連続配列の先頭コード")
    extract.add_argument("--output", type=Path, required=True)
    apply = sub.add_parser("apply", help="完全スナップショットJSONをC配列へ安全に反映")
    apply.add_argument("--source", type=Path, required=True)
    apply.add_argument("--input", type=Path, required=True)
    apply.add_argument("--output", type=Path)
    apply.add_argument("--in-place", action="store_true", help="sourceを直接更新する。明示指定が必要")
    apply.add_argument("--legacy-patch", action="store_true", help="旧patch-v1を許可する（基準値検証なし）")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "extract":
            document = extract_document(args.source, args.array, args.occurrence, args.start_code)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"抽出しました: {args.array} ({len(document['elements'])} elements)")
            return 0
        if args.in_place:
            output = args.source
        elif args.output is not None:
            output = args.output
            if output.resolve() == args.source.resolve():
                fail("sourceを上書きする場合は --in-place を明示してください")
        else:
            fail("--output または --in-place が必要です")
        count = apply_document(args.source, json.loads(args.input.read_text(encoding="utf-8")), output, args.legacy_patch)
        print(f"反映しました: {count} glyphs -> {output}")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"font_source_json: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
