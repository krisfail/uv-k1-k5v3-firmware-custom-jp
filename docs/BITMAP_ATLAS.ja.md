# ビットマップ／フォント atlas

`tools/render_bitmap_atlas.py` は、ファームウェアのビルドには参加せず、Cソース内の`uint8_t` bitmap／font配列を読み取ってOLED向けのatlasを生成するオフライン補助ツールです。bit 0を画面上端として描画します。

## 実行

リポジトリのルートで実行します。引数を省略すると、`App/bitmaps.c`、`App/font.c`、`App/japanese_font.c`を読み取ります。K1/K5 V3の条件分岐にある同名配列も、ソース上の出現順にすべて収録します。

```powershell
python -X utf8 tools/render_bitmap_atlas.py --out C:\Users\yukim\uv-kx-jp\tmp\uv-k1-bitmap-atlas
```

生成物:

- `bitmap_atlas.svg`: ブラウザで開けるatlas
- `bitmap_atlas_inventory.json`: 配列名、条件分岐を含む出現順、サイズ、元バイト列

フォント配列には、コードポイント、ソースコメント、占有／空き状態、グリフ単位の元バイト列も収録します。新しい文字を追加する前は、[FONT_BITMAP_ANNOTATIONS.ja.md](FONT_BITMAP_ANNOTATIONS.ja.md)の台帳とこのinventoryを突き合わせてください。

`gFontBig`は14 bytes/glyph（7列×2 OLEDページ）として認識し、連続した長いbyte列ではなくglyphごとのグリッドに配置します。`gFontBigDigits`と`gFontBigJapanese`も同じ2ページ形式として表示します。`gFontBig`のglyphラベルは`0x21`（`!`）からのコード値です。指定初期化子を含む日本語配列は、ソース上の出現順で表示します。

PNGが必要な場合はImageMagickで変換できます。

```powershell
magick -background white bitmap_atlas.svg bitmap_atlas.png
```

対象を限定する場合は`--source`を繰り返します。

```powershell
python -X utf8 tools/render_bitmap_atlas.py `
  --source App/bitmaps.c `
  --source App/font.c `
  --source App/japanese_font.c `
  --out C:\Users\yukim\uv-kx-jp\tmp\uv-k1-bitmap-atlas
```

同名配列の`[2]`などの表示は、条件コンパイル上の別候補を区別するためのものです。全配列が同一ビルドに同時に入ることや、K1とK5 V3の機種差を解決済みであることを意味しません。

このツールはソースや生成済みファームウェアを書き換えません。表示の意味や実機LCD上の見え方を自動判定するものでもありません。フォントの帰属・ライセンス表示は既存の`NOTICE`やソースコメントから削除しないでください。
