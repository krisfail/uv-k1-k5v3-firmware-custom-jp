# UV-K1 / UV-K5 V3 Japanese receive-only firmware

[日本語版README](README.ja.md) | [操作・ビルドcheatsheet](CHEATSHEET.ja.md) | [Developer guide](DEVELOPMENT.md) | [CHIRP driver](tools/chirp/README.ja.md) | [Technical feature details](docs/FEATURES_TECHNICAL.ja.md) | [Feature audit](docs/FEATURE_AUDIT.ja.md) | [Hardware test plan](docs/HARDWARE_TEST_PLAN.ja.md) | [Documentation site](docs/index.md)

This repository is the downstream fork [krisfail/uv-k1-k5v3-firmware-custom-jp](https://github.com/krisfail/uv-k1-k5v3-firmware-custom-jp), with [armel/uv-k1-k5v3-firmware-custom](https://github.com/armel/uv-k1-k5v3-firmware-custom) as its upstream. It adapts the F4HWN and [Egzumer custom firmware](https://github.com/egzumer/uv-k5-firmware-custom) lineage to the UV-K1 and UV-K5 V3, which use the PY32F071 MCU.

## Scope and safety

This fork targets Japanese-language, receive-only use on the UV-K1 and UV-K5 V3. It is not an official Quansheng, F4HWN, or armel release.

Some code analysis, implementation, test support, and documentation used AI assistance. Maintainers review the result, but AI assistance does not replace maintainer review or user testing.

The firmware is provided **as is**, without warranty. The maintainers are not responsible for radio damage, failed flashing, loss of EEPROM, calibration data or configuration, recovery failure, or use that violates local radio regulations. Back up calibration data and relevant memory before flashing, use an image for the exact hardware model, and keep a recovery method available.

## Available local build

The local Japanese build is `JpRxOnly`:

- Japanese menu labels and large/small Japanese glyph paths.
- Expanded Japanese LCD labels, including large-font long-vowel and restored katakana glyphs.
- The `専` and `用` glyphs, including the receive-only welcome display, are independently reduced from the public-domain [Izumi 16](https://unifoundry.com/japanese/) bitmap font; see [font provenance](docs/FONT_SOURCES.ja.md).
- TX paths and TX-related menus disabled.
- PTT assigned to monitor operation.
- `MAIN ONLY`, `DUAL RX`, and `SINGLE` receive modes.
- `W`, `N`, and `N-` bandwidth selection (20/12.5/6.25 kHz); K1 does not expose WIDE+ because BK4829 applies the same RF setting.
- Receive band presets, memory banks, automatic squelch, AGC protection, and temporary scan skipping.
- Receive audio profiles are enabled in `JpRxOnly`; the audio scope and level history remain receive-side diagnostics.
- The `RXExt` radio menu item enables or disables those added receive features as a group; it defaults to enabled.
- Domestic FM broadcast reception limited to `76.0–95.0 MHz`.

The receive-only UI omits TX power labels such as `LOW` and `HIGH`. Normal PTT operation is monitor control; only an unexpected request reaching the final TX guard shows `TX DISABLE`. Unsupported receive actions show a short reason such as `RXExt OFF`, `VFO ONLY`, `SCAN ACTIVE`, or `FM ONLY`.

`JpRxOnly` is the only supported CMake preset. The former upstream-style presets were removed from this fork so a Japanese or domestic receive-only build cannot be confused with a transmit-capable comparison image.

Detailed operation notes are in [README.ja.md](README.ja.md). The quick reference is in [CHEATSHEET.ja.md](CHEATSHEET.ja.md). Technical implementation details are in [docs/FEATURES_TECHNICAL.ja.md](docs/FEATURES_TECHNICAL.ja.md); current feature adoption and exclusions are consolidated in [docs/FEATURE_AUDIT.ja.md](docs/FEATURE_AUDIT.ja.md), with the hardware checklist in [docs/HARDWARE_TEST_PLAN.ja.md](docs/HARDWARE_TEST_PLAN.ja.md). CHIRP-specific memory-map and upload guidance is in [tools/chirp/README.ja.md](tools/chirp/README.ja.md); legal attribution remains in `tools/chirp/NOTICE.md` and `tools/chirp/LICENSE.txt`.

This README is a user-facing overview. Development-specific source layout, change boundaries, atlas generation, validation, and release handling are collected in [DEVELOPMENT.md](DEVELOPMENT.md).

## Building `JpRxOnly`

Run these commands from the repository root. The host build requires CMake, Ninja, and the ARM GNU toolchain (`arm-none-eabi-gcc`).

On a fresh checkout, configure first:

```powershell
cmake --preset JpRxOnly
cmake --build --preset JpRxOnly -j2
```

The outputs are under `build/JpRxOnly`:

- `wrx-jp.bin`: firmware image.
- `wrx-jp.hex`: HEX image.
- `wrx-jp.elf`: ELF image for debugging.
- `release/wrx-jp-v5.9.0J1.packed.bin`: versioned release-equivalent packed image.

## CHIRP driver

Copy `tools/chirp/wrx_jp.py` into the CHIRP driver directory and select `UV-K1 / UV-K5 V3 (wrx-jp RX-only)`. The same module contains a separate legacy UV-K5 profile; do not use it for K1 or UV-K5 V3. The driver is RX-only and its upload whitelist excludes calibration data. Read the [CHIRP guide](tools/chirp/README.ja.md) before writing.

After configuration, source-only changes can be rebuilt with:

```powershell
cmake --build --preset JpRxOnly -j2
```

Run the static checks with:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

The full developer workflow, source map, persistence boundaries, and atlas procedure are in [DEVELOPMENT.md](DEVELOPMENT.md).

## Flashing and backup

[UV Studio](https://armel.github.io/uvstudio/) can flash the UV-K1 and UV-K5 V3 through Web Serial. Before flashing:

1. Dump and save calibration data with [UV Studio](https://armel.github.io/uvstudio/#dump-calib).
2. Confirm the exact radio model and select its matching image.
3. Enter DFU mode and flash the image.
4. Confirm the firmware version, frequency input, FM reception, receive audio, and PTT monitor behavior after reboot.

Restore calibration data before returning to stock firmware or changing firmware families. Do not skip the backup because this fork is provided without warranty.

## Upstream feature summary

The upstream F4HWN work adds features across Fusion, spectrum analysis, broadcast FM, scanning, display and audio controls, memory handling, connectivity, RF logging, and related tools. This README keeps only that summary; consult the [upstream Wiki](https://github.com/armel/uv-k1-k5v3-firmware-custom/wiki) and [upstream repository](https://github.com/armel/uv-k1-k5v3-firmware-custom) for the full catalogue and general documentation.

## Other references

- [armel/k1-teardown](https://github.com/armel/k1-teardown)
- [UV Studio](https://armel.github.io/uvstudio/)
- [rainy-knight/uv-k5-jp](https://github.com/rainy-knight/uv-k5-jp) Japanese font reference

## Acknowledgements / 謝辞

This project carries forward the open-source work of DualTachyon, F4HWN, Egzumer, and the other contributors below. Forks and derived work should preserve the applicable license notices and credit the upstream projects.

### Donations

Special thanks to Jean-Cyrille F6IWW (3 times), Fabrice 14RC123, David F4BPP, Olivier 14RC206, Frédéric F4ESO, Stéphane F5LGW (2 times), Jorge Ornelas (4 times), Laurent F4AXK, Christophe Morel, Clayton W0LED, Pierre Antoine F6FWB, Jean-Claude 14FRS3306, Thierry F4GVO, Eric F1NOU, PricelessToolkit, Ady M6NYJ, Tom McGovern (4 times), Joseph Roth, Pierre-Yves Colin, Frank DJ7FG, Marcel Testaz, Brian Frobisher, Yannick F4JFO, Paolo Bussola, Dirk DL8DF, Levente Szőke (2 times), Bernard-Michel Herrera, Jérôme Saintespes, Paul Davies, RS (3 times), Johan F4WAT, Robert Wörle, Rafael Sundorf, Paul Harker, Peter Fintl, Pascal F4ICR (2 times), Mike DL2MF (3 times), Eric KI1C / F4WFS (3 times), Phil G0ELM, Jérôme Lambert, Eliot Vedel, Alfonso EA7KDF, Jean-François F1EVM, Robert DC1RDB (2 times), Ian KE2CHJ, Daryl VK3AWA, Roberto Brunelli, Robert Boardman, Stephen Oliver, Nicolas F4INE, William Bruno, Daniel OK2VLK, Tayler Chew, Peter DL7RFP, Philippe Kopp, Rune LA6YMA, Jeremy Luna, Steef Wagenaar (2 times), Zhuo BG7SGA, Jamie M0JLB, Antoine LIBERT, Vince K0DKR, Julia DF7JA, Ken 2E0UMK, Victor TI2SYS, Tobi DG9LAY, Deaglan K4DFQ, Catherine PALMER, Brian WA6JFK, Stéphane Hintzy, Roger F1HCN, Marcin Kusaj, Flavio Cottarelli, Bob N1MLZ, Carlos EA1IJ, Brian M7YLF, Giuseppe IT9LLH and 邓 月 for their [donations](https://www.paypal.com/paypalme/F4HWN). That’s so kind of them. Thanks so much 🙏🏻

### Credits

Many thanks to:

- [Muzkr](https://github.com/muzkr)
- [Mrkusypl](https://github.com/mrkusypl)
- [Andrej](https://github.com/Tunas1337)
- [Egzumer](https://github.com/egzumer)
- [OneOfEleven](https://github.com/OneOfEleven)
- [DualTachyon](https://github.com/DualTachyon)
- UV-K5-RX-JP: receive-only and wideband receiver feature ideas were used as a partial reference.
- [Mikhail / fagci](https://github.com/fagci)
- [Manuel](https://github.com/manujedi)
- @wagner
- @Lohtse Shar
- [@Matoz](https://github.com/spm81)
- @Davide
- @Ismo OH2FTG
- @d1ced95
- and the other contributors to the upstream projects.

## License

Copyright 2023 Dual Tachyon
https://github.com/DualTachyon

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
