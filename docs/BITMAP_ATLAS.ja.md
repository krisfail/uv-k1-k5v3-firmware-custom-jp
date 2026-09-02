# ビットマップ／フォントatlas

`tools/render_bitmap_atlas.py` は、ファームウェアのビルドには参加せず、Cソース内の`uint8_t` bitmap／font配列を読み取ってatlasを生成するオフライン補助ツールです。bit 0を画面上端として描画します。

## 実行

リポジトリのルートで実行します。現行のmanifestは内蔵ASCIIフォントと画面ビットマップだけを対象にします。

```powershell
cmake --build --preset JpRxOnly --target font-atlas
cmake --build --preset JpRxOnly --target font-quality
```

一時ディレクトリへ出力する場合は、manifestを明示します。

```powershell
python -X utf8 tools/render_bitmap_atlas.py `
  --manifest tools/font_inventory.json `
  --out tmp/uv-k1-bitmap-atlas `
  --markdown-out tmp/uv-k1-bitmap-atlas/font_inventory.generated.ja.md
```

生成されるファイル:

- `bitmap_atlas.svg`: ブラウザで開けるatlas。空白セルは共有パターン、点灯セルは`path`として出力する
- `bitmap_atlas_inventory.json`: 配列名、条件分岐を含む出現順、サイズ、元バイト列、編集可能な要素の範囲
- `--markdown-out`を指定した場合の`font_inventory.generated.ja.md`: 要素、注釈、空き／使用中を確認する生成一覧

生成後は、[フォント品質診断](FONT_QUALITY.ja.md)で空字形、バイト長、`occupied`メタデータの整合性を確認します。外部Izumiフォントの16×16字形はC配列ではなく、`docs/fonts/japanese_font.bin`の独立したバイナリ資産です。

## 配列の見方

`gFontBig`は14 bytes/glyph（7列×2 OLEDページ）、`gFontSmall`と`gFontSmallBold`は6 bytes/glyphのASCIIフォントです。`gFontBigDigits`などの専用配列と`BITMAP_*`配列も、同じatlasで形状とバイト列を確認できます。

大字形は16行（2ページ）の固定セルです。字形ごとの点灯範囲は一致しないため、上下の空白を前提にして描画位置を補正しません。長い表示は実際のLCD幅に収まるかを確認し、文字列を短くする場合は意味を変えないようにします。

## C配列の編集

`tools/font_source_json.py`は、コード範囲を指定したC配列を完全スナップショットJSONへ変換します。JSONには抽出時の`base_bytes_hex`が含まれ、適用時にC側が変更されていれば停止します。

```powershell
python -X utf8 tools/font_source_json.py extract `
  --source App/font.c --array gFontSmall --start-code 0x21 `
  --output tmp/gFontSmall.source.json
python -X utf8 tools/font_source_json.py apply `
  --source App/font.c --input tmp/gFontSmall.source.json `
  --output tmp/font.c
```

既定では一時Cファイルへ出力します。atlas、`git diff --no-index`、ビルドを確認してから、必要な場合だけ`--in-place`を使用します。フォントの出所と外部バイナリの生成方法は[FONT_SOURCES.ja.md](FONT_SOURCES.ja.md)を参照してください。

## 対話編集と限界

`tools/font_editor.html`をブラウザで開き、`bitmap_atlas_inventory.json`を読み込むと、内蔵ASCII字形と`BITMAP_*`配列のドットを編集できます。表示幅に応じてプレビューを改行し、配列本来のセル幅を維持します。外部Izumiフォントの編集・生成機能はこのツールの対象外です。

atlasは形状と配置の静的確認用であり、ファームウェアの実行状態、LCDコントローラーの電気的な挙動、実機での視認性、外部フォント転送の成功を保証しません。フォントの帰属・ライセンス表示は`NOTICE`やソースコメントから削除しないでください。
