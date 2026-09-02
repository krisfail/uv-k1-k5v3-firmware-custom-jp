# フォント一覧

現行の内蔵フォントと画面ビットマップの生成一覧です。詳細な元バイト列と編集可能範囲は、同じ内容を自動生成した[atlas inventory](assets/font-atlas/bitmap_atlas_inventory.json)を参照してください。

## 現行配列

| 配列 | 用途 | 要素幅 | 要素数 |
| --- | --- | ---: | ---: |
| `gFontBig` | ASCII大字 | 14 bytes | 94 |
| `gFontBigDigits` | 大きい数字 | 20 bytes | 11 |
| `gFontSmall` | ASCII小字 | 6 bytes | 94 |
| `gFontSmallBold` | 選択中のASCII小字 | 6 bytes | 94 |
| `gFontSmallDigits` | 小さい数字 | 7 bytes | 11 |
| `gFont3x5` | 最小表示 | 3 bytes | 96 |
| `BITMAP_*` | VFOマーカー、アイコン、状態記号 | 配列ごとに異なる | — |

固定UIの文言は`gFontBig`、`gFontSmall`、`gFontSmallBold`を使い、フォント未書込みでも読めるASCII表記を基本とします。UTF-8のチャンネル名に使うIzumi 16×16フォントはC配列ではなく、外部資産`docs/fonts/japanese_font.bin`として管理します。

## 生成

```powershell
cmake --build --preset JpRxOnly --target font-atlas
cmake --build --preset JpRxOnly --target font-quality
```

この文書と`docs/assets/font-atlas/font_inventory.generated.ja.md`は、生成時点の確認用一覧です。ソース配列の変更後はatlas、inventory、品質診断をまとめて更新し、実機表示は別途確認します。
