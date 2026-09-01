"""Build the one-file CHIRP module used for wrx-jp distribution."""

from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
import textwrap
import zlib


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = PROJECT_ROOT / "tools" / "chirp" / "wrx_jp.py"
DEFAULT_MANIFEST = PROJECT_ROOT / "tools" / "japanese_font_manifest.json"
DEFAULT_BINARY = PROJECT_ROOT / "docs" / "fonts" / "japanese_font.bin"
DEFAULT_OUTPUT = PROJECT_ROOT / "tools" / "chirp" / "wrx_jp_standalone.py"
START_MARKER = "# BEGIN GENERATED EMBEDDED FONT BLOCK"
END_MARKER = "# END GENERATED EMBEDDED FONT BLOCK"


def _encoded_assignment(name, payload):
    encoded = base64.b64encode(zlib.compress(payload, 9)).decode("ascii")
    lines = textwrap.wrap(encoded, 76)
    return "{} = (\n{}\n)".format(
        name, "\n".join('    "{}"'.format(line) for line in lines))


def render_module(source_text, manifest, font_data):
    if source_text.count(START_MARKER) != 1 or source_text.count(END_MARKER) != 1:
        raise ValueError("embedded font block markers must occur exactly once")

    manifest_data = json.dumps(
        manifest, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    block = "\n".join((
        START_MARKER,
        "# Generated file: do not edit this block by hand.",
        _encoded_assignment(
            "_EMBEDDED_FONT_MANIFEST_ZLIB_BASE64",
            manifest_data.encode("utf-8")),
        _encoded_assignment(
            "_EMBEDDED_FONT_BINARY_ZLIB_BASE64", font_data),
        END_MARKER,
    ))
    start = source_text.index(START_MARKER)
    end = source_text.index(END_MARKER) + len(END_MARKER)
    return source_text[:start] + block + source_text[end:]


def build(source_path, manifest_path, binary_path, output_path, check=False):
    source_text = source_path.read_text(encoding="utf-8")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    font_data = binary_path.read_bytes()
    expected_size = int(manifest["total_bytes"])
    if len(font_data) != expected_size:
        raise ValueError(
            "font size {} does not match manifest {}".format(
                len(font_data), expected_size))

    rendered = render_module(source_text, manifest, font_data)
    if check:
        if not output_path.is_file():
            raise ValueError("generated module is missing: {}".format(output_path))
        current = output_path.read_text(encoding="utf-8")
        if current != rendered:
            raise ValueError("generated module is out of date: {}".format(output_path))
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8", newline="\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--binary", type=Path, default=DEFAULT_BINARY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--check", action="store_true",
        help="verify the generated module without changing it")
    args = parser.parse_args()
    build(args.source, args.manifest, args.binary, args.output, args.check)


if __name__ == "__main__":
    main()
