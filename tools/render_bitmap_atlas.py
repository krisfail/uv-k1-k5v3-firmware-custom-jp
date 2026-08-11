#!/usr/bin/env python3
"""Render C uint8_t bitmap/font arrays as an SVG atlas.

The source arrays are treated as OLED columns: bit 0 is drawn at the top.
This is an offline inspection tool and does not modify firmware sources or
participate in the build.
"""

from __future__ import annotations

import argparse
import ast
import html
import json
import re
from dataclasses import dataclass
from pathlib import Path


DECL_RE = re.compile(
    r"\b(?:(?:static)\s+)?const\s+(?:uint8_t|unsigned\s+char)\s+"
    r"(?P<name>[A-Za-z_]\w*)(?P<dims>(?:\s*\[[^\]]*\])+?)\s*=\s*\{"
)
NUMBER_RE = re.compile(r"(?<![A-Za-z0-9_])(?:0[xX][0-9A-Fa-f]+|0[bB][01]+|[0-9]+)[uUlL]*")
SHARED_GLYPH_LABELS = dict(zip(
    range(0x80, 0x98),
    "受信変調追加保存削除名長短押音電源更圧表示画面無",
))
FONT_ELEMENT_CODES = {
    "gFontSmall": tuple(range(0x21, 0x7F)),
    "gFontSmallBold": tuple(range(0x21, 0x7F)),
    "gFont3x5": tuple(range(0x20, 0x80)),
    "gFontSmallDigits": tuple(range(0x30, 0x3A)) + (0x2D,),
    "gFontBigDigits": tuple(range(0x30, 0x3A)) + (0x2D,),
}


def font_element_label(name: str, index: int) -> str:
    codes = FONT_ELEMENT_CODES.get(name)
    if codes is None or index >= len(codes):
        return f"element {index}"
    code = codes[index]
    character = chr(code) if 0x20 <= code < 0x7F else ""
    return f"0x{code:02X}{f' {character}' if character else ''}"


@dataclass
class Array:
    name: str
    source: str
    dimensions: list[str]
    values: bytes
    occurrence: int
    element_width: int | None
    glyphs: list[dict] | None

    @property
    def label(self) -> str:
        suffix = f" [{self.occurrence}]" if self.occurrence > 1 else ""
        return f"{self.name}{suffix}"

    @property
    def category(self) -> str:
        if self.name.startswith("BITMAP_"):
            return "bitmap"
        if self.name.startswith("gFont"):
            return "font"
        return "array"

    @property
    def glyph_layout(self) -> tuple[int, int] | None:
        """Return (columns, pages) for fonts stored as two OLED pages."""
        if self.name in {"gFontBig", "gFontBigJapanese"} and self.element_width == 14:
            return (7, 2)
        if self.name == "gFontJapaneseExtraLarge" and self.element_width == 20:
            return (10, 2)
        if self.name == "gFontSmallJapanese" and self.element_width == 6:
            return (6, 1)
        if self.name == "gFontBigDigits" and self.element_width and self.element_width % 2 == 0:
            return (self.element_width // 2, 2)
        return None

    @property
    def glyph_data(self) -> list[bytes] | None:
        if not self.glyphs:
            return None
        return [bytes(glyph["bytes"]) for glyph in self.glyphs]

    @property
    def editable_chunks(self) -> list[dict]:
        """Describe non-glyph arrays as independently editable byte chunks."""
        if self.glyphs is not None:
            return []
        chunk_size = self.element_width or 64
        if chunk_size <= 0 or chunk_size > 64:
            chunk_size = 64
        chunks = []
        for index, offset in enumerate(range(0, len(self.values), chunk_size)):
            length = min(chunk_size, len(self.values) - offset)
            label = font_element_label(self.name, index) if self.category == "font" else f"element {index}"
            chunks.append({
                "index": index,
                "offset": offset,
                "length": length,
                "label": label,
            })
        return chunks


def remove_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.DOTALL)
    return re.sub(r"//.*", " ", text)


def remove_if_zero_blocks(text: str) -> str:
    """Remove disabled #if 0 branches while retaining their #else branch."""
    lines = text.splitlines(keepends=True)
    output: list[str] = []
    index = 0
    while index < len(lines):
        if not re.match(r"^\s*#if\s+0\b", lines[index]):
            output.append(lines[index])
            index += 1
            continue
        depth = 1
        else_index: int | None = None
        cursor = index + 1
        while cursor < len(lines) and depth:
            line = lines[cursor]
            if re.match(r"^\s*#if(?:def|ndef)?\b", line):
                depth += 1
            elif re.match(r"^\s*#endif\b", line):
                depth -= 1
            elif depth == 1 and re.match(r"^\s*#else\b", line):
                else_index = cursor
            cursor += 1
        if depth:
            raise ValueError("unterminated #if 0 block")
        if else_index is not None:
            output.extend(lines[else_index + 1 : cursor - 1])
        index = cursor
    return "".join(output)


def matching_brace(text: str, opening: int) -> int:
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return index
    raise ValueError(f"unterminated initializer at offset {opening}")


def eval_dimension(expression: str) -> int | None:
    expression = expression.strip()
    if not expression:
        return None
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError:
        return None
    allowed = (ast.Expression, ast.Constant, ast.UnaryOp, ast.UAdd, ast.USub, ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.FloorDiv)
    if any(not isinstance(node, allowed) for node in ast.walk(tree)):
        return None
    try:
        value = eval(compile(tree, "<dimension>", "eval"), {"__builtins__": {}}, {})
    except (ArithmeticError, NameError, TypeError, ValueError):
        return None
    return value if isinstance(value, int) and value > 0 else None


def eval_integer_expression(expression: str) -> int | None:
    expression = expression.strip()
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError:
        return None
    allowed = (ast.Expression, ast.Constant, ast.UnaryOp, ast.UAdd, ast.USub,
               ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.FloorDiv)
    if any(not isinstance(node, allowed) for node in ast.walk(tree)):
        return None
    try:
        value = eval(compile(tree, "<expression>", "eval"), {"__builtins__": {}}, {})
    except (ArithmeticError, NameError, TypeError, ValueError):
        return None
    return value if isinstance(value, int) else None


def parse_values(initializer: str) -> bytes:
    initializer = remove_comments(initializer)
    initializer = re.sub(r"\[[^\]]*\]\s*=", " ", initializer)
    values: list[int] = []
    for match in NUMBER_RE.finditer(initializer):
        token = match.group(0).rstrip("uUlL")
        value = int(token, 0)
        if not 0 <= value <= 0xFF:
            raise ValueError(f"non-byte initializer {token}")
        values.append(value)
    if not values:
        raise ValueError("initializer contains no byte literals")
    return bytes(values)


def comment_label(comment: str) -> str | None:
    """Extract all human annotation fragments after a glyph initializer.

    Some tables use two comments, for example ``//0x98 専 //（自作）``.
    Keeping both fragments makes the generated inventory round-trip the
    source annotation instead of silently replacing it with the last comment.
    """
    parts = [part.strip() for part in comment.split("//") if part.strip()]
    if not parts:
        return None
    labels = []
    for part in parts:
        candidate = re.sub(r"^0[xX][0-9A-Fa-f]+\s*", "", part)
        candidate = candidate.strip(" ,")
        if len(candidate) >= 2 and candidate[0] in "'\"" and candidate[-1] == candidate[0]:
            candidate = candidate[1:-1].strip()
        if candidate:
            labels.append(candidate)
    return " ".join(labels) or None


def parse_manifest_code(value: str | int) -> int:
    """Parse a firmware byte written as JSON number or hexadecimal text."""

    if isinstance(value, int):
        code = value
    elif isinstance(value, str):
        code = int(value, 0)
    else:
        raise ValueError(f"invalid firmware code {value!r}")
    if not 0 <= code <= 0xFF:
        raise ValueError(f"firmware code is outside one byte: 0x{code:X}")
    return code


def load_font_manifest(path: Path, root: Path) -> dict:
    """Load the repository-relative font inventory manifest safely."""

    manifest_path = path.resolve()
    try:
        manifest_path.relative_to(root)
    except ValueError as error:
        raise ValueError("font manifest must be inside the repository") from error
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != 1:
        raise ValueError("unsupported font manifest schema")
    if not isinstance(manifest.get("sources"), list) or not manifest["sources"]:
        raise ValueError("font manifest must contain at least one source")
    for source in manifest["sources"]:
        if not isinstance(source, dict) or not isinstance(source.get("path"), str):
            raise ValueError("each font manifest source needs a relative path")
        candidate = (root / source["path"]).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as error:
            raise ValueError(f"font source escapes repository: {source['path']}") from error
    return manifest


def manifest_sources(manifest: dict, root: Path) -> list[tuple[Path, set[str] | None]]:
    """Return source paths and optional array allow-lists from the manifest."""

    result = []
    for source in manifest["sources"]:
        arrays = source.get("arrays")
        if arrays is not None:
            if not isinstance(arrays, list) or not all(isinstance(name, str) for name in arrays):
                raise ValueError("font manifest arrays must be a list of names")
            arrays = set(arrays)
        result.append(((root / source["path"]).resolve(), arrays))
    return result


def apply_font_manifest(arrays: list[Array], manifest: dict) -> list[Array]:
    """Apply canonical selection and code-point annotations to parsed arrays."""

    array_specs = manifest.get("arrays", {})
    labels = {
        parse_manifest_code(code): label
        for code, label in manifest.get("codepoint_labels", {}).items()
    }
    selected: list[Array] = []
    for array in arrays:
        spec = array_specs.get(array.name, {})
        if spec.get("include", True) is False:
            continue
        if array.glyphs is not None:
            array_labels = dict(labels)
            array_labels.update({
                parse_manifest_code(code): value
                for code, value in spec.get("labels", {}).items()
            })
            for glyph in array.glyphs:
                if glyph["code"] in array_labels:
                    glyph["label"] = array_labels[glyph["code"]]
        selected.append(array)
    if not selected:
        raise ValueError("font manifest selected no parsed arrays")
    return selected


def parse_glyph_annotations(
    name: str,
    initializer: str,
    element_width: int | None,
    declared_count: int | None = None,
) -> list[dict] | None:
    """Return code-point and label annotations for Japanese glyph tables."""
    if name == "gFontBig" and element_width == 14:
        # The source keeps a disabled space glyph as a line comment.  Do not
        # count that brace as a real glyph, otherwise every code point shifts.
        initializer = re.sub(r"//\s*\{[^\r\n]*", "", initializer)
        entries = re.findall(r"\{([^{}]*)\}([^\r\n]*)", initializer)
        glyphs = []
        for index, (body, comment) in enumerate(entries):
            code = 0x21 + index
            values = parse_values(body)
            if len(values) != element_width:
                raise ValueError(
                    f"{name} glyph 0x{code:02X} has {len(values)} bytes; "
                    f"expected {element_width}"
                )
            label = comment_label(comment) or SHARED_GLYPH_LABELS.get(code)
            if label is None and 0x20 < code < 0x7F:
                label = chr(code)
            glyphs.append({"code": code, "label": label, "bytes": values,
                           "occupied": any(values), "source_index": index})
        if declared_count is not None:
            if len(glyphs) > declared_count:
                raise ValueError(
                    f"{name} contains {len(glyphs)} glyphs but declares {declared_count}"
                )
            for index in range(len(glyphs), declared_count):
                glyphs.append({
                    "code": 0x21 + index,
                    "label": None,
                    "bytes": bytes(element_width),
                    "occupied": False,
                    "source_index": index,
                })
        return glyphs

    if name == "gFontJapaneseExtraLarge" and element_width == 20:
        # The compact table carries each firmware code in its row comment.
        entries = re.findall(r"\{([^{}]*)\}([^\r\n]*)", initializer)
        glyphs = []
        seen_codes: set[int] = set()
        for source_index, (body, comment) in enumerate(entries):
            code_match = re.search(r"0[xX]([0-9A-Fa-f]{2})", comment)
            if code_match is None:
                raise ValueError(f"{name} glyph {source_index} has no code annotation")
            code = int(code_match.group(1), 16)
            if code in seen_codes:
                raise ValueError(f"duplicate glyph code 0x{code:02X} in {name}")
            seen_codes.add(code)
            values = parse_values(body)
            if len(values) != element_width:
                raise ValueError(
                    f"{name} glyph 0x{code:02X} has {len(values)} bytes; "
                    f"expected {element_width}"
                )
            glyphs.append({"code": code, "label": comment_label(comment),
                           "bytes": values, "occupied": any(values),
                           "source_index": source_index})
        return glyphs

    if name not in {"gFontBigJapanese", "gFontSmallJapanese"}:
        return None

    entries = re.findall(r"\[([^\]]+)\]\s*=\s*\{([^{}]*)\}([ \t]*,?[ \t]*(?://[^\r\n]*)?)", initializer)
    parsed: dict[int, tuple[str | None, bytes]] = {}
    max_code = 0x7F
    for expression, body, comment in entries:
        index = eval_integer_expression(expression)
        if index is None:
            raise ValueError(f"cannot evaluate glyph index {expression!r} in {name}")
        code = index + 0x7F
        if code in parsed:
            raise ValueError(f"duplicate glyph code 0x{code:02X} in {name}")
        values = parse_values(body)
        if element_width is not None:
            if len(values) != element_width:
                raise ValueError(
                    f"{name} glyph 0x{code:02X} has {len(values)} bytes; "
                    f"expected {element_width}"
                )
        parsed[code] = (comment_label(comment) or SHARED_GLYPH_LABELS.get(code), values)
        max_code = max(max_code, code)
    if not parsed:
        return []
    glyphs = []
    for code in range(0x80, max_code + 1):
        entry = parsed.get(code)
        values = entry[1] if entry is not None else bytes(element_width or 0)
        glyphs.append({"code": code, "label": entry[0] if entry else None,
                       "bytes": values, "occupied": any(values),
                       "source_index": code - 0x80})
    return glyphs


def parse_source(
    path: Path,
    occurrences: dict[str, int],
    source_label: str | None = None,
) -> list[Array]:
    text = remove_if_zero_blocks(path.read_text(encoding="utf-8"))
    arrays: list[Array] = []
    for match in DECL_RE.finditer(text):
        opening = text.find("{", match.start(), match.end())
        closing = matching_brace(text, opening)
        values = parse_values(text[opening + 1 : closing])
        dimensions = re.findall(r"\[([^\]]*)\]", match.group("dims"))
        width = eval_dimension(dimensions[-1]) if dimensions else None
        if width is None and len(dimensions) == 1:
            # A one-dimensional byte table is one editable byte per element,
            # even when its declared length is a macro.
            width = 1
        initializer = text[opening + 1 : closing]
        declared_count = eval_dimension(dimensions[0]) if dimensions else None
        glyphs = parse_glyph_annotations(match.group("name"), initializer, width, declared_count)
        if glyphs:
            # Designated initializers omit blank slots from the source text;
            # the inventory must still represent the complete runtime table.
            values = b"".join(bytes(glyph["bytes"]) for glyph in glyphs)
        occurrences[match.group("name")] = occurrences.get(match.group("name"), 0) + 1
        # Keep generated inspection artifacts independent of the analyst's
        # absolute filesystem layout.
        arrays.append(Array(match.group("name"), source_label or path.name, dimensions, values,
                            occurrences[match.group("name")], width,
                            glyphs))
    return arrays


def xml_text(value: str) -> str:
    return html.escape(value, quote=True)


def append_grid_pattern(lines: list[str], scale: int) -> str:
    pattern_id = f"cell-grid-{scale}"
    lines.extend([
        f'<pattern id="{pattern_id}" width="{scale}" height="{scale}" patternUnits="userSpaceOnUse">',
        f'<rect width="{scale}" height="{scale}" fill="#f1f1f1"/>',
        f'<path d="M {scale} 0H0V{scale}" fill="none" stroke="#d6dde4" stroke-width="1"/>',
        "</pattern>",
    ])
    return pattern_id


def bitmap_path(data: bytes, width: int, rows: int, x: int, y: int, scale: int) -> str:
    """Return one compact path containing only lit horizontal runs."""
    commands: list[str] = []
    for row in range(rows):
        page = row // 8
        bit = 1 << (row % 8)
        column = 0
        while column < width:
            index = page * width + column
            if index >= len(data) or not data[index] & bit:
                column += 1
                continue
            start = column
            column += 1
            while column < width:
                index = page * width + column
                if index >= len(data) or not data[index] & bit:
                    break
                column += 1
            run_width = (column - start) * scale - 1
            commands.append(
                f"M{x + start * scale},{y + row * scale}"
                f"h{run_width}v{scale - 1}h-{run_width}z"
            )
    return "".join(commands)


def draw_bitmap(
    lines: list[str], data: bytes, x: int, y: int, scale: int, label: str,
    width: int, rows: int, pattern_id: str,
) -> int:
    lines.append(f'<text x="{x}" y="{y - 7}" class="sub">{xml_text(label)}</text>')
    lines.append(
        f'<rect x="{x}" y="{y}" width="{width * scale}" height="{rows * scale}" '
        f'fill="url(#{pattern_id})"/>'
    )
    path = bitmap_path(data, width, rows, x, y, scale)
    if path:
        lines.append(f'<path d="{path}" fill="#111111" shape-rendering="crispEdges"/>')
    return y + rows * scale


def draw_font_elements(
    lines: list[str], array: Array, x: int, y: int, scale: int, pattern_id: str,
) -> int:
    if not array.element_width or len(array.values) % array.element_width:
        raise ValueError(f"{array.label} has incomplete font elements")
    element_width = array.element_width
    element_count = len(array.values) // element_width
    per_row = 12 if element_width <= 7 else 8
    cell_width = element_width * scale + 24
    cell_height = 8 * scale + 30
    for index in range(element_count):
        cell_x = x + (index % per_row) * cell_width
        cell_y = y + (index // per_row) * cell_height
        offset = index * element_width
        draw_bitmap(
            lines,
            array.values[offset : offset + element_width],
            cell_x,
            cell_y,
            scale,
            font_element_label(array.name, index),
            element_width,
            8,
            pattern_id,
        )
    rows = (element_count + per_row - 1) // per_row
    return y + rows * cell_height


def draw_glyph_atlas(
    lines: list[str],
    array: Array,
    x: int,
    y: int,
    scale: int,
    pattern_id: str,
    wrap: int,
) -> int:
    layout = array.glyph_layout
    if layout is None:
        raise ValueError(f"no glyph layout for {array.name}")
    glyph_width, pages = layout
    glyph_size = glyph_width * pages
    glyph_data = array.glyph_data
    if glyph_data is None:
        if len(array.values) % glyph_size:
            raise ValueError(f"{array.label} has incomplete glyph data")
        glyph_data = [array.values[index:index + glyph_size]
                      for index in range(0, len(array.values), glyph_size)]
    glyph_count = len(glyph_data)
    # ``wrap`` also applies to glyph atlases.  This makes focused reviews
    # possible at a large inspection scale without clipping the last glyphs.
    default_per_row = 12 if glyph_width <= 7 else 8
    per_row = min(default_per_row, wrap)
    cell_width = glyph_width * scale + 24
    cell_height = pages * 8 * scale + 30
    for index in range(glyph_count):
        cell_x = x + (index % per_row) * cell_width
        cell_y = y + (index // per_row) * cell_height
        annotation = array.glyphs[index] if array.glyphs else None
        code_label = f"0x{annotation['code']:02X}" if annotation else font_element_label(array.name, index)
        if annotation and annotation.get("label"):
            # Keep provenance in the inventory while keeping the compact SVG
            # cell label short enough not to overlap its neighbours.
            display_label = annotation["label"].split(" (", 1)[0]
            code_label += f" {display_label}"
        draw_bitmap(
            lines, glyph_data[index], cell_x, cell_y, scale, code_label,
            glyph_width, pages * 8, pattern_id,
        )
    rows = (glyph_count + per_row - 1) // per_row
    return y + rows * cell_height


def make_svg(arrays: list[Array], scale: int, wrap: int) -> str:
    width = max(1200, 80 + wrap * scale + 700)
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" viewBox="0 0 {width} 100">',
        '<style>.title{font:bold 24px sans-serif}.meta{font:14px sans-serif}.section{font:bold 17px sans-serif}.sub{font:12px Consolas,monospace}</style>',
    ]
    pattern_id = append_grid_pattern(lines, scale)
    background_index = len(lines)
    lines.append('<rect width="100%" height="100%" fill="white"/>')
    lines.extend([
        '<text x="32" y="36" class="title">C bitmap/font atlas</text>',
        '<text x="32" y="60" class="meta">Each byte is one OLED column; bit 0 is at the top. Source order and conditional variants are preserved.</text>',
    ])
    y = 98
    for array in arrays:
        dims = "".join(f"[{d}]" for d in array.dimensions)
        lines.append(f'<text x="32" y="{y}" class="section">{xml_text(array.label)} ({xml_text(array.category)}, {len(array.values)} bytes, {xml_text(dims)})</text>')
        lines.append(f'<text x="32" y="{y + 20}" class="meta">source: {xml_text(array.source)}; element width: {array.element_width or "inferred"}</text>')
        y += 52
        if array.glyph_layout is not None:
            y = draw_glyph_atlas(lines, array, 48, y + 20, scale, pattern_id, wrap) + 42
        elif array.category == "font" and array.element_width:
            y = draw_font_elements(lines, array, 48, y + 20, scale, pattern_id) + 42
        else:
            for chunk_index in range(0, len(array.values), wrap):
                chunk = array.values[chunk_index : chunk_index + wrap]
                draw_bitmap(
                    lines, chunk, 48, y + 20, scale,
                    f"byte offset +0x{chunk_index:04X}", len(chunk), 8, pattern_id,
                )
                y += 8 * scale + 42
        y += 25
    lines[0] = lines[0].replace('viewBox="0 0 ' + str(width) + ' 100"', f'viewBox="0 0 {width} {y + 30}"')
    lines[background_index] = f'<rect width="100%" height="{y + 30}" fill="white"/>'
    lines.append(f'<text x="32" y="{y + 5}" class="meta">arrays: {len(arrays)}; generated offline from C sources</text>')
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def markdown_cell(value: object) -> str:
    """Escape a value for a Markdown table cell."""
    return str(value).replace("|", "\\|").replace("\n", " ")


def make_markdown_inventory(arrays: list[Array]) -> str:
    """Return a compact, human-readable font inventory."""
    lines = [
        "# フォント一覧",
        "",
        "この一覧は `tools/render_bitmap_atlas.py` が現行Cソースから生成したものです．",
        "コードはファームウェア内部の1バイトコードであり，Unicodeコードポイントではありません．",
        "字形の元バイト列は同じ出力ディレクトリの `bitmap_atlas_inventory.json` を参照してください．",
        "",
        "## 配列サマリー",
        "",
        "| 配列 | 種類 | サイズ(byte) | 要素幅 | 要素／グリフ数 | 使用中 |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for array in arrays:
        chunks = array.editable_chunks
        element_count = len(array.glyphs) if array.glyphs is not None else len(chunks)
        occupied = (
            sum(glyph["occupied"] for glyph in array.glyphs)
            if array.glyphs is not None
            else sum(any(array.values[chunk["offset"] : chunk["offset"] + chunk["length"]]) for chunk in chunks)
        )
        lines.append(
            f"| `{markdown_cell(array.label)}` | {array.category} | {len(array.values)} | "
            f"{array.element_width or '—'} | {element_count} | {occupied} |"
        )

    for array in arrays:
        if array.glyphs is None:
            continue
        lines.extend([
            "",
            f"## `{markdown_cell(array.label)}`",
            "",
            "| コード | 注釈 | 状態 | ソース順 |",
            "| --- | --- | --- | ---: |",
        ])
        for glyph in array.glyphs:
            label = glyph["label"] or "未注釈"
            state = "使用中" if glyph["occupied"] else "空き"
            lines.append(
                f"| `0x{glyph['code']:02X}` | {markdown_cell(label)} | {state} | "
                f"{glyph['source_index']} |"
            )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", action="append", type=Path, help="C source containing uint8_t arrays (repeatable)")
    parser.add_argument("--manifest", type=Path, help="repository-relative JSON font inventory manifest")
    parser.add_argument("--out", type=Path, default=Path("bitmap-atlas"), help="output directory")
    parser.add_argument("--markdown-out", type=Path, help="write a human-readable Markdown font inventory")
    parser.add_argument("--scale", type=int, default=6, help="pixels per bitmap cell in SVG")
    parser.add_argument("--wrap", type=int, default=64, help="maximum columns per rendered strip")
    args = parser.parse_args()
    if args.scale < 2 or args.wrap < 1:
        raise SystemExit("--scale must be >= 2 and --wrap must be >= 1")
    root = Path.cwd().resolve()
    manifest = None
    manifest_source_filters: dict[Path, set[str] | None] = {}
    if args.manifest:
        manifest = load_font_manifest(args.manifest, root)
        if args.source:
            raise SystemExit("--source and --manifest cannot be used together")
        manifest_sources_list = manifest_sources(manifest, root)
        sources = [source for source, _ in manifest_sources_list]
        manifest_source_filters = dict(manifest_sources_list)
    else:
        sources = args.source
    if not sources:
        candidates = [root / "bitmaps.c", root / "font.c", root / "App" / "bitmaps.c", root / "App" / "font.c", root / "App" / "japanese_font.c"]
        sources = [candidate for candidate in candidates if candidate.exists()]
    if not sources:
        raise SystemExit("no source supplied and no bitmaps.c/App/bitmaps.c found")
    arrays: list[Array] = []
    display_sources: list[str] = []
    occurrences: dict[str, int] = {}
    for source_arg in sources:
        source = source_arg.resolve()
        if not source.is_file():
            raise SystemExit(f"source not found: {source}")
        try:
            source_label = source.relative_to(root).as_posix()
        except ValueError:
            # Keep local inspection useful without publishing parent paths.
            source_label = source.name
        display_sources.append(source_label)
        parsed = parse_source(source, occurrences, source_label)
        allowed_arrays = manifest_source_filters.get(source)
        if allowed_arrays is not None:
            parsed = [array for array in parsed if array.name in allowed_arrays]
        arrays.extend(parsed)
    if not arrays:
        raise SystemExit("no uint8_t arrays found")
    if manifest is not None:
        arrays = apply_font_manifest(arrays, manifest)
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    inventory = []
    for array in arrays:
        layout = array.glyph_layout
        record = {"name": array.label, "category": array.category, "source": array.source, "dimensions": array.dimensions, "element_width": array.element_width, "size": len(array.values), "bytes_hex": array.values.hex(" "), "layout": f"glyph-{layout[1]}page" if layout else "column-strip", "element_count": len(array.glyphs) if array.glyphs is not None else len(array.editable_chunks)}
        if layout:
            record["glyph_width"] = layout[0]
            record["glyph_pages"] = layout[1]
            record["glyph_count"] = len(array.glyphs) if array.glyphs else len(array.values) // (layout[0] * layout[1])
        if array.glyphs:
            record["glyphs"] = [
                {"code": f"0x{glyph['code']:02X}", "label": glyph["label"],
                 "occupied": glyph["occupied"],
                 "bytes_hex": bytes(glyph["bytes"]).hex(" ")}
                for glyph in array.glyphs
            ]
        else:
            record["editable_chunks"] = array.editable_chunks
        inventory.append(record)
    inventory_document = {"sources": display_sources, "arrays": inventory}
    if manifest is not None:
        inventory_document["manifest"] = args.manifest.resolve().relative_to(root).as_posix()
        inventory_document["encoding"] = manifest.get("encoding", {})
    (out / "bitmap_atlas_inventory.json").write_text(json.dumps(inventory_document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "bitmap_atlas.svg").write_text(make_svg(arrays, args.scale, args.wrap), encoding="utf-8")
    if args.markdown_out:
        markdown_out = args.markdown_out.resolve()
        markdown_out.parent.mkdir(parents=True, exist_ok=True)
        markdown_out.write_text(make_markdown_inventory(arrays), encoding="utf-8")
    print(f"arrays: {len(arrays)}")
    print(f"svg: {out / 'bitmap_atlas.svg'}")
    print(f"inventory: {out / 'bitmap_atlas_inventory.json'}")
    if args.markdown_out:
        print(f"markdown: {args.markdown_out.resolve()}")


if __name__ == "__main__":
    main()

