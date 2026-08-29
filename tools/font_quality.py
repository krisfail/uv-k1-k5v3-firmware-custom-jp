#!/usr/bin/env python3
"""Detect structurally broken glyphs in a generated font inventory.

This checker deliberately evaluates the inventory contract, not visual taste.
An empty glyph is an error unless the manifest explicitly records that code
point as a reserved slot.  This keeps sparse Japanese tables useful while
catching accidental deletion and stale occupancy metadata.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any


CODE_SPEC_RE = re.compile(r"^(0[xX][0-9A-Fa-f]+|[0-9]+)(?:\s*-\s*(0[xX][0-9A-Fa-f]+|[0-9]+))?$")
SEVERITIES = ("error", "warning", "info")


@dataclass(frozen=True)
class Finding:
    severity: str
    array: str
    code: str | None
    message: str

    def as_dict(self) -> dict[str, str | None]:
        return {
            "severity": self.severity,
            "array": self.array,
            "code": self.code,
            "message": self.message,
        }


def parse_code(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError("boolean is not a code point")
    if isinstance(value, int):
        code = value
    elif isinstance(value, str):
        code = int(value.strip(), 0)
    else:
        raise ValueError(f"invalid code point: {value!r}")
    if not 0 <= code <= 0xFF:
        raise ValueError(f"code point is outside one byte: 0x{code:X}")
    return code


def expand_code_specs(values: Any) -> set[int]:
    if values is None:
        return set()
    if not isinstance(values, list):
        raise ValueError("expected_empty must be a list")
    result: set[int] = set()
    for value in values:
        if isinstance(value, int) and not isinstance(value, bool):
            first = last = value
        elif isinstance(value, str):
            match = CODE_SPEC_RE.fullmatch(value.strip())
            if match is None:
                raise ValueError(f"invalid expected_empty range: {value!r}")
            first = parse_code(match.group(1))
            last = parse_code(match.group(2) or match.group(1))
        else:
            raise ValueError(f"invalid expected_empty entry: {value!r}")
        if first > last:
            raise ValueError(f"expected_empty range is reversed: {value!r}")
        result.update(range(first, last + 1))
    return result


def parse_bytes(value: Any) -> bytes:
    if not isinstance(value, str):
        raise ValueError("bytes_hex must be a hexadecimal string")
    tokens = value.split()
    if any(re.fullmatch(r"(?:0[xX])?[0-9A-Fa-f]{2}", token) is None for token in tokens):
        raise ValueError("bytes_hex must contain space-separated byte values")
    return bytes(int(token.removeprefix("0x").removeprefix("0X"), 16) for token in tokens)


def array_spec(manifest: dict[str, Any] | None, name: str) -> dict[str, Any]:
    if not manifest:
        return {}
    base_name = name.split(" [", 1)[0]
    specs = manifest.get("arrays", {})
    spec = specs.get(base_name, {}) if isinstance(specs, dict) else {}
    return spec if isinstance(spec, dict) else {}


def quality_spec(record: dict[str, Any], manifest: dict[str, Any] | None) -> dict[str, Any]:
    if "quality" in record:
        embedded = record["quality"]
        if not isinstance(embedded, dict):
            raise ValueError("quality must be an object")
        return embedded
    manifest_quality = array_spec(manifest, str(record.get("name", ""))).get("quality", {})
    if not isinstance(manifest_quality, dict):
        raise ValueError("quality must be an object")
    return manifest_quality


def canonical_label(manifest: dict[str, Any] | None, code: int) -> str | None:
    if not manifest:
        return None
    labels = manifest.get("codepoint_labels", {})
    if not isinstance(labels, dict):
        return None
    for raw_code, label in labels.items():
        try:
            if parse_code(raw_code) == code:
                return label if isinstance(label, str) else None
        except ValueError:
            continue
    return None


def analyze_inventory(document: dict[str, Any], manifest: dict[str, Any] | None = None) -> list[Finding]:
    findings: list[Finding] = []
    arrays = document.get("arrays")
    if not isinstance(arrays, list):
        return [Finding("error", "<document>", None, "arraysを含む台帳JSONではありません")]

    for record in arrays:
        if not isinstance(record, dict):
            findings.append(Finding("error", "<document>", None, "配列レコードがオブジェクトではありません"))
            continue
        name = str(record.get("name", "<unnamed>"))
        try:
            raw_bytes = parse_bytes(record.get("bytes_hex", ""))
        except ValueError as error:
            findings.append(Finding("error", name, None, str(error)))
            raw_bytes = b""
        declared_size = record.get("size")
        if isinstance(declared_size, int) and declared_size != len(raw_bytes):
            findings.append(Finding("error", name, None, f"size={declared_size} と bytes_hex={len(raw_bytes)} が一致しません"))
        element_width = record.get("element_width")
        if isinstance(element_width, int) and element_width > 0 and len(raw_bytes) % element_width:
            findings.append(Finding("error", name, None, f"{len(raw_bytes)} bytes が element_width={element_width} で割り切れません"))

        try:
            expected_empty = expand_code_specs(quality_spec(record, manifest).get("expected_empty", []))
        except ValueError as error:
            findings.append(Finding("error", name, None, str(error)))
            expected_empty = set()
        glyphs = record.get("glyphs")
        if not isinstance(glyphs, list):
            continue
        seen_codes: set[int] = set()
        present_codes: set[int] = set()
        for glyph in glyphs:
            if not isinstance(glyph, dict):
                findings.append(Finding("error", name, None, "字形レコードがオブジェクトではありません"))
                continue
            raw_code = glyph.get("code")
            try:
                code = parse_code(raw_code)
            except ValueError as error:
                findings.append(Finding("error", name, str(raw_code), str(error)))
                continue
            code_label = f"0x{code:02X}"
            if code in seen_codes:
                findings.append(Finding("error", name, code_label, "同じコードポイントが重複しています"))
            seen_codes.add(code)
            present_codes.add(code)
            try:
                glyph_bytes = parse_bytes(glyph.get("bytes_hex", ""))
            except ValueError as error:
                findings.append(Finding("error", name, code_label, str(error)))
                continue
            if isinstance(element_width, int) and len(glyph_bytes) != element_width:
                findings.append(Finding("error", name, code_label, f"字形が {len(glyph_bytes)} bytes で，element_width={element_width} と一致しません"))
            occupied = any(glyph_bytes)
            if glyph.get("occupied") is not occupied:
                findings.append(Finding("error", name, code_label, "occupiedフラグと実際のビット列が一致しません"))
            label = glyph.get("label")
            if code in expected_empty:
                if occupied:
                    findings.append(Finding("error", name, code_label, "空きスロット指定なのに点灯ビットがあります"))
                else:
                    findings.append(Finding("info", name, code_label, "意図した空きスロット"))
            elif not occupied:
                description = f"「{label}」" if isinstance(label, str) and label else "未注釈"
                findings.append(Finding("error", name, code_label, f"{description}の字形が空です"))
            elif not isinstance(label, str) or not label.strip():
                findings.append(Finding("warning", name, code_label, "点灯ビットはありますが注釈がありません"))

            expected_label = canonical_label(manifest, code)
            if expected_label is not None and label != expected_label:
                findings.append(Finding("error", name, code_label, f"注釈が台帳定義と異なります（期待値: {expected_label} / 実値: {label}）"))

        for code in sorted(expected_empty - present_codes):
            findings.append(Finding("error", name, f"0x{code:02X}", "空きスロット指定されたコードポイントが字形表にありません"))
    return findings


def format_report(findings: list[Finding]) -> str:
    if not findings:
        return "品質診断: 問題なし"
    lines = []
    for finding in findings:
        location = finding.array + (f" {finding.code}" if finding.code else "")
        lines.append(f"[{finding.severity.upper()}] {location}: {finding.message}")
    counts = {severity: sum(f.severity == severity for f in findings) for severity in SEVERITIES}
    lines.append(f"合計: error={counts['error']}, warning={counts['warning']}, info={counts['info']}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="フォント台帳の構造品質を診断する")
    parser.add_argument("--inventory", type=Path, required=True, help="bitmap_atlas_inventory.json")
    parser.add_argument("--manifest", type=Path, help="font_inventory.json")
    parser.add_argument("--json", action="store_true", dest="as_json", help="診断結果をJSONで出力する")
    args = parser.parse_args()
    document = json.loads(args.inventory.read_text(encoding="utf-8"))
    manifest = json.loads(args.manifest.read_text(encoding="utf-8")) if args.manifest else None
    findings = analyze_inventory(document, manifest)
    if args.as_json:
        print(json.dumps([finding.as_dict() for finding in findings], ensure_ascii=False, indent=2))
    else:
        print(format_report(findings))
    return 1 if any(finding.severity == "error" for finding in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
