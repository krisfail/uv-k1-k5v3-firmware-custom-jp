# wrx-jp CHIRP driver notice

`wrx_jp.py` is an RX-only adaptation for the Japanese `wrx-jp` firmware for
UV-K1 / UV-K5 V3 (PY32F071, external-flash map).

The protocol and memory-layout work is adapted from
`armel/uv-k5-chirp-driver`, distributed under CC BY-SA 4.0. The upstream
attribution chain includes Jacek Lipkowski, EGZUMER, JOC2, F4HWN, and the
CHIRP template by Dan Smith. See `LICENSE.txt` for the license text.

`wrx_jp_standalone.py` is generated from this driver and embeds the Japanese
font binary and manifest so that CHIRP can load one module file. The embedded
font is the Izumi 16-derived bitmap described in `docs/fonts/README.ja.md`;
its source and redistribution terms are recorded there.

This driver is provided as-is. Keep a complete download from the exact radio
before uploading, and do not use the driver to enable or configure
transmission.
