# フォント一覧

この一覧は `tools/render_bitmap_atlas.py` が現行Cソースから生成したものです．
コードはファームウェア内部の1バイトコードであり，Unicodeコードポイントではありません．
字形の元バイト列は同じ出力ディレクトリの `bitmap_atlas_inventory.json` を参照してください．

## 配列サマリー

| 配列 | 種類 | サイズ(byte) | 要素幅 | 要素／グリフ数 | 使用中 |
| --- | --- | ---: | ---: | ---: | ---: |
| `gFontBig` | font | 1316 | 14 | 94 | 94 |
| `gFontBigDigits` | font | 220 | 20 | 11 | 11 |
| `gFontSmallDigits` | font | 77 | 7 | 11 | 11 |
| `gFontSmall` | font | 564 | 6 | 94 | 94 |
| `gFontSmallBold` | font | 564 | 6 | 94 | 94 |
| `gFont3x5` | font | 288 | 3 | 96 | 95 |
| `gFontPowerSave` | font | 12 | 6 | 2 | 2 |
| `gFontPttOnePush` | font | 12 | 6 | 2 | 2 |
| `gFontPttClassic` | font | 12 | 6 | 2 | 2 |
| `gFontF` | font | 8 | 8 | 1 | 1 |
| `gFontS` | font | 6 | 6 | 1 | 1 |
| `gFontKeyLock` | font | 9 | 9 | 1 | 1 |
| `gFontLight` | font | 9 | 9 | 1 | 1 |
| `gFontLightOff` | font | 9 | 9 | 1 | 1 |
| `gFontMute` | font | 12 | 12 | 1 | 1 |
| `gFontXB` | font | 12 | 6 | 2 | 2 |
| `gFontMO` | font | 12 | 6 | 2 | 2 |
| `gFontDWR` | font | 18 | 6 | 3 | 3 |
| `gFontRO` | font | 12 | 6 | 2 | 2 |
| `gFontHold` | font | 10 | 5 | 2 | 2 |
| `BITMAP_BatteryLevel` | bitmap | 2 | 2 | 1 | 1 |
| `BITMAP_BatteryLevel1` | bitmap | 17 | 17 | 1 | 1 |
| `BITMAP_USB_C` | bitmap | 9 | 9 | 1 | 1 |
| `gFontVox` | font | 12 | 6 | 2 | 2 |
| `BITMAP_VFO_Lock` | bitmap | 7 | 7 | 1 | 1 |
| `BITMAP_VFO_Default` | bitmap | 7 | 7 | 1 | 1 |
| `BITMAP_VFO_NotDefault` | bitmap | 7 | 7 | 1 | 1 |
| `BITMAP_VFO_Default [2]` | bitmap | 7 | 7 | 1 | 1 |
| `BITMAP_VFO_NotDefault [2]` | bitmap | 7 | 7 | 1 | 1 |
| `BITMAP_VFO_Empty` | bitmap | 7 | 7 | 1 | 0 |
| `BITMAP_compand` | bitmap | 6 | 6 | 1 | 1 |
| `BITMAP_Ready` | bitmap | 7 | 7 | 1 | 1 |
| `BITMAP_NotReady` | bitmap | 7 | 7 | 1 | 1 |
| `BITMAP_PowerUser` | bitmap | 3 | 3 | 1 | 1 |
| `BITMAP_NOAA` | bitmap | 12 | 12 | 1 | 1 |
| `BITMAP_FoxHuntSignal` | bitmap | 10 | 10 | 1 | 1 |
| `BITMAP_FoxHuntSpeaker` | bitmap | 10 | 10 | 1 | 1 |
| `BITMAP_FoxHuntUp` | bitmap | 11 | 11 | 1 | 1 |
| `BITMAP_FoxHuntDown` | bitmap | 11 | 11 | 1 | 1 |
| `BITMAP_FoxHuntFlat` | bitmap | 11 | 11 | 1 | 1 |
| `BITMAP_FoxHuntBars` | bitmap | 11 | 11 | 1 | 1 |
| `BITMAP_FoxHuntGraph` | bitmap | 15 | 15 | 1 | 1 |
| `BITMAP_FoxHuntTx` | bitmap | 16 | 16 | 1 | 1 |
| `BITMAP_CurrentIndicator` | bitmap | 8 | 8 | 1 | 1 |

## `gFontBig`

| コード | 注釈 | 状態 | ソース順 |
| --- | --- | --- | ---: |
| `0x21` | ! | 使用中 | 0 |
| `0x22` | " | 使用中 | 1 |
| `0x23` | # | 使用中 | 2 |
| `0x24` | $ | 使用中 | 3 |
| `0x25` | % | 使用中 | 4 |
| `0x26` | & | 使用中 | 5 |
| `0x27` | ' | 使用中 | 6 |
| `0x28` | ( | 使用中 | 7 |
| `0x29` | ) | 使用中 | 8 |
| `0x2A` | * | 使用中 | 9 |
| `0x2B` | + | 使用中 | 10 |
| `0x2C` | , | 使用中 | 11 |
| `0x2D` | - | 使用中 | 12 |
| `0x2E` | . | 使用中 | 13 |
| `0x2F` | / | 使用中 | 14 |
| `0x30` | 0 | 使用中 | 15 |
| `0x31` | 1 | 使用中 | 16 |
| `0x32` | 2 | 使用中 | 17 |
| `0x33` | 3 | 使用中 | 18 |
| `0x34` | 4 | 使用中 | 19 |
| `0x35` | 5 | 使用中 | 20 |
| `0x36` | 6 | 使用中 | 21 |
| `0x37` | 7 | 使用中 | 22 |
| `0x38` | 8 | 使用中 | 23 |
| `0x39` | 9 | 使用中 | 24 |
| `0x3A` | : | 使用中 | 25 |
| `0x3B` | ; | 使用中 | 26 |
| `0x3C` | < | 使用中 | 27 |
| `0x3D` | = | 使用中 | 28 |
| `0x3E` | > | 使用中 | 29 |
| `0x3F` | ? | 使用中 | 30 |
| `0x40` | @ | 使用中 | 31 |
| `0x41` | A | 使用中 | 32 |
| `0x42` | B | 使用中 | 33 |
| `0x43` | C | 使用中 | 34 |
| `0x44` | D | 使用中 | 35 |
| `0x45` | E | 使用中 | 36 |
| `0x46` | F | 使用中 | 37 |
| `0x47` | G | 使用中 | 38 |
| `0x48` | H | 使用中 | 39 |
| `0x49` | I | 使用中 | 40 |
| `0x4A` | J | 使用中 | 41 |
| `0x4B` | K | 使用中 | 42 |
| `0x4C` | L | 使用中 | 43 |
| `0x4D` | M | 使用中 | 44 |
| `0x4E` | N | 使用中 | 45 |
| `0x4F` | O | 使用中 | 46 |
| `0x50` | P | 使用中 | 47 |
| `0x51` | Q | 使用中 | 48 |
| `0x52` | R | 使用中 | 49 |
| `0x53` | S | 使用中 | 50 |
| `0x54` | T | 使用中 | 51 |
| `0x55` | U | 使用中 | 52 |
| `0x56` | V | 使用中 | 53 |
| `0x57` | W | 使用中 | 54 |
| `0x58` | X | 使用中 | 55 |
| `0x59` | Y | 使用中 | 56 |
| `0x5A` | Z | 使用中 | 57 |
| `0x5B` | [ | 使用中 | 58 |
| `0x5C` | "\ | 使用中 | 59 |
| `0x5D` | ] | 使用中 | 60 |
| `0x5E` | ^ | 使用中 | 61 |
| `0x5F` | _ | 使用中 | 62 |
| `0x60` | ` | 使用中 | 63 |
| `0x61` | a | 使用中 | 64 |
| `0x62` | b | 使用中 | 65 |
| `0x63` | c | 使用中 | 66 |
| `0x64` | d | 使用中 | 67 |
| `0x65` | e | 使用中 | 68 |
| `0x66` | f | 使用中 | 69 |
| `0x67` | g | 使用中 | 70 |
| `0x68` | h | 使用中 | 71 |
| `0x69` | i | 使用中 | 72 |
| `0x6A` | j | 使用中 | 73 |
| `0x6B` | k | 使用中 | 74 |
| `0x6C` | l | 使用中 | 75 |
| `0x6D` | m | 使用中 | 76 |
| `0x6E` | n | 使用中 | 77 |
| `0x6F` | o | 使用中 | 78 |
| `0x70` | p | 使用中 | 79 |
| `0x71` | q | 使用中 | 80 |
| `0x72` | r | 使用中 | 81 |
| `0x73` | s | 使用中 | 82 |
| `0x74` | t | 使用中 | 83 |
| `0x75` | u | 使用中 | 84 |
| `0x76` | v | 使用中 | 85 |
| `0x77` | w | 使用中 | 86 |
| `0x78` | x | 使用中 | 87 |
| `0x79` | y | 使用中 | 88 |
| `0x7A` | z | 使用中 | 89 |
| `0x7B` | { | 使用中 | 90 |
| `0x7C` | \| | 使用中 | 91 |
| `0x7D` | } | 使用中 | 92 |
| `0x7E` | -> | 使用中 | 93 |
