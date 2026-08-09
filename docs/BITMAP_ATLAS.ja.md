# ビットマップ／フォント atlas

`tools/render_bitmap_atlas.py` は、ファームウェアのビルドには参加せず、Cソース内の`uint8_t` bitmap／font配列を読み取ってOLED向けのatlasを生成するオフライン補助ツールです。bit 0を画面上端として描画します。

この文書は人間の開発者向けです。利用者向けの表示・操作案内は[README.ja.md](../README.ja.md)、AIエージェント向けの規則は[AGENTS.md](../AGENTS.md)を参照してください。

## 実行

リポジトリのルートで実行します。引数を省略すると、`App/bitmaps.c`、`App/font.c`、`App/japanese_font.c`を読み取ります。K1/K5 V3の条件分岐にある同名配列も、ソース上の出現順にすべて収録します。

```powershell
python -X utf8 tools/render_bitmap_atlas.py --out tmp/uv-k1-bitmap-atlas
```

生成物:

- `bitmap_atlas.svg`: ブラウザで開けるatlas
- `bitmap_atlas_inventory.json`: 配列名、条件分岐を含む出現順、サイズ、元バイト列
- `--markdown-out`を指定した場合の`FONT_INVENTORY.ja.md`: コード、注釈、空き／使用中を確認する人間向け一覧

現行ソースから生成した確認用成果物は、[font-atlas](assets/font-atlas/)に保存しています。SVGとJSONは表示確認・差分確認用であり、ファームウェアのビルドには含まれません。

ドットを対話的に編集する場合は、[../tools/font_editor.html](../tools/font_editor.html)を開いて`bitmap_atlas_inventory.json`を読み込んでください。編集結果はC初期化子またはJSONパッチとして出力され、ソースへは自動反映されません。

フォント配列には、コードポイント、ソースコメント、占有／空き状態、グリフ単位の元バイト列も収録します。新しい文字を追加する前は、[FONT_BITMAP_ANNOTATIONS.ja.md](FONT_BITMAP_ANNOTATIONS.ja.md)の台帳とこのinventoryを突き合わせてください。

`gFontBig`は14 bytes/glyph（7列×2 OLEDページ）として認識し、連続した長いbyte列ではなくglyphごとのグリッドに配置します。`gFontBigDigits`と`gFontBigJapanese`も同じ2ページ形式として表示します。`gFontJapaneseExtraLarge`は20 bytes/glyph（10列×2 OLEDページ）の特大字形として表示します。K1/K5 V3では、K5と同じ4コードの疎な予約表を使います。`gFontBig`のglyphラベルは`0x21`（`!`）からのコード値です。指定初期化子を含む日本語配列は、ソース上の出現順で表示します。

## 大字形の縦位置契約

大字形は16行（2ページ）を1セルとし、欧文・日本語で同じ表示座標を使います。bit 0が上側で、標準の表示領域は次のとおりです。

- 上余白: 2行（表示行0–1）
- 字形領域: 10行（表示行2–11）
- 下余白: 4行（表示行12–15）

日本語大字形は、描画時に個別の上下シフトを行いません。ソース配列自体をこの座標系へ正規化しているため、atlasと実機描画の行番号が一致します。長音「ー」も欧文ハイフンと同じ行に固定しています。編集画面では上下余白を色分けし、現在の字形の点灯範囲を表示します。

特大字形は同じ16行契約で横幅を10列へ拡張しています。`UI_PrintStringJapaneseExtraLarge`は、特大表へ登録された日本語コードだけを指定位置へ描画する専用APIです。現在の4スロットは、通常大字形の「受・信・専・用」をセル中央へ再配置した実データです。受信専用の起動画面では日本語行に使用し、その他の場所では通常大字形と使い分けます。

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
  --out tmp/uv-k1-bitmap-atlas `
  --markdown-out docs\FONT_INVENTORY.ja.md
```

同名配列の`[2]`などの表示は、条件コンパイル上の別候補を区別するためのものです。全配列が同一ビルドに同時に入ることや、K1とK5 V3の機種差を解決済みであることを意味しません。

このツールはソースや生成済みファームウェアを書き換えません。表示の意味や実機LCD上の見え方を自動判定するものでもありません。フォントの帰属・ライセンス表示は既存の`NOTICE`やソースコメントから削除しないでください。
