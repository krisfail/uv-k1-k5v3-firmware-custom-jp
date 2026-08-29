# ビットマップ／フォントatlas

`tools/render_bitmap_atlas.py` は，ファームウェアのビルドには参加せず，Cソース内の`uint8_t` bitmap／font配列を読み取ってOLED向けのatlasを生成するオフライン補助ツールです．bit 0を画面上端として描画します．

この文書は開発者向けの説明です．利用者向けの表示・操作案内は[README.ja.md](../README.ja.md)を参照してください．

## 実行

リポジトリのルートで実行します．フォントの意味・用途・コードポイントは`tools/font_inventory.json`で管理し，C配列はビルド入力です．バイト列を編集するときは`tools/font_source_json.py`で完全スナップショットJSONを作り，基準バイト列を検証してからCへ戻します．追跡済みatlasを更新する場合は，明示的なターゲットを使います．

```powershell
cmake --build --preset JpRxOnly --target font-atlas
cmake --build --preset JpRxOnly --target font-quality
```

一時ディレクトリへ出力する場合は，manifestを明示します．

```powershell
python -X utf8 tools/render_bitmap_atlas.py `
  --manifest tools/font_inventory.json `
  --out tmp/uv-k1-bitmap-atlas `
  --markdown-out tmp/uv-k1-bitmap-atlas/font_inventory.generated.ja.md
```

生成されるファイル:

- `bitmap_atlas.svg`: ブラウザで開ける軽量atlas．空白セルは共有パターン，点灯セルは`path`として出力する
- `bitmap_atlas_inventory.json`: 配列名，条件分岐を含む出現順，サイズ，元バイト列，編集可能な要素の範囲
- `--markdown-out`を指定した場合の`font_inventory.generated.ja.md`: コード，注釈，空き／使用中を確認する生成一覧

生成後は，[フォント品質診断](FONT_QUALITY.ja.md)で空字形，バイト長，`occupied`メタデータ，コードポイント注釈の整合性を確認します．予約された空きスロットはmanifestに明記され，誤って空になった字形とは区別されます．

現行ソースから生成した確認用成果物は，[font-atlas](assets/font-atlas/)に保存しています．SVGとJSONは表示確認・差分確認用であり，ファームウェアのビルドには含まれません．

ドットを対話的に編集する場合は，[../tools/font_editor.html](../tools/font_editor.html)を開いて`bitmap_atlas_inventory.json`を読み込んでください．フォントの全字形に加え，通常フォント配列の他の要素と`BITMAP_*`配列も選択できます．注釈欄ではソースコメントも編集できます．編集対象を切り替えても変更は保持され，C初期化子または配列名・バイトオフセット・注釈付きの全変更JSONパッチとして出力されます．ソースへは自動反映されません．

編集画面の「元データ」は，選択した字形を台帳から読み込んだ直後のバイト列です．現在の点灯状態が元データに対して追加されたドットは赤枠，消去されたドットは青枠で表示し，変更ビット数と変更バイト数を画面下部に表示します．「読込時に戻す」で元データへ戻せます．これは外部の原本を自動取得する機能ではなく，読み込んだinventoryに含まれる元バイト列との差分です．

編集画面の「文字列プレビュー」では，入力した文字列を選択中の配列の字形で横並びに描画します．表示幅に応じて改行し，字形を縮小せず配列本来のセル幅を維持します．「日本語例」ボタンでは，選択中の配列に関係なくJIS X 0201相当の文字列を設定できます．現在編集中の字形はその場の編集内容を使い，配列に登録されていない文字は赤枠で示します．また，出力したWRX-JP JSONパッチは台帳読込後に画面上で再読込できます．

フォント配列には，コードポイント，ソースコメント，占有／空き状態，グリフ単位の元バイト列を収録します．注釈がない通常フォントも，要素幅に従って1字形ずつatlasと編集画面へ分割します．グリフでない配列には，`editable_chunks`として要素のオフセットと長さを収録します．新しい文字を追加する前は，[FONT_BITMAP_ANNOTATIONS.ja.md](FONT_BITMAP_ANNOTATIONS.ja.md)の台帳とこのinventoryを突き合わせてください．

フォント配列とJSONの往復は次のように行います．JSONには`base_bytes_hex`と`bytes_hex`が保存され，抽出後にC配列が変わっている場合は適用を拒否します．既定では一時Cファイルへ出力し，`--in-place`の明示なしにソースを上書きしません．

```powershell
python -X utf8 tools/font_source_json.py extract --source App\japanese_font.c --array gFontBigJapanese --output tmp/gFontBigJapanese.source.json
python -X utf8 tools/font_source_json.py apply --source App\japanese_font.c --input tmp/gFontBigJapanese.source.json --output tmp/japanese_font.c
```

宣言長がマクロで解決できない1次元の`uint8_t`配列も，1バイトを1要素として分割します．これにより，字形コード表なども編集画面から個別に確認できます．

`gFontBig`は14 bytes/glyph（7列×2 OLEDページ）として認識し，連続した長いbyte列ではなくglyphごとのグリッドに配置します．`gFontBigDigits`と`gFontBigJapanese`も同じ2ページ形式として表示します．`gFontJapaneseExtraLarge`は20 bytes/glyph（10列×2 OLEDページ）の起動画面用字形として表示します．K1では`0x80`（受），`0x81`（信），`0x98`（専），`0x99`（用）の4スロットを持ちます．`gFontBig`のglyphラベルは`0x21`（`!`）からのコード値です．指定初期化子を含む日本語配列は，ソース上の出現順で表示します．

`0xA1`–`0xDF`の文字名は，現行atlasの注釈ではなく[フォント割り当て台帳](FONT_BITMAP_ANNOTATIONS.ja.md)の正規表を参照してください．rainy由来の基準配列にはコードポイントと行のずれ，空白化，重複があるため，atlasは現行バイト列の監査結果を示しますが，正しい字形割り当てを保証しません．K1の`gFontBigJapanese`と`gFontSmallJapanese`は別配列なので，配列位置の一致だけで同じ文字と判断してはいけません．

## 大字形の格納形式と表示範囲

通常大字形は16行（2ページ）を1セルとして固定長で格納します．bit 0が上側で，14 bytesはST7565の2ページへそのままコピーされます．これは上下の空白を別フィールドで持つ形式ではありません．字形ごとに実際の点灯範囲が異なるため，atlasと編集画面では点灯範囲を正本の情報として扱います．

- 表示行0–15: 固定セルの全範囲
- 表示行2–11: 既存フォントで多く使われる参考範囲
- 表示行0–1／12–15: 文字によって点灯する場合があるため，必須の余白ではない

日本語大字形は，欧文と同じ固定セル形式へ格納し，描画時の個別シフトは行いません．長音「ー」も欧文ハイフンと同じ字形データを共有します．編集画面の色分けは選択中の字形の実際の点灯範囲に追従する参考表示であり，書き込み禁止領域を意味しません．

現行の6 bytes小字形はカタカナの主表示には小さすぎるため，medium字形を追加する場合は，atlas側にも幅・高さ・ページ数を明示した配列として登録します．既存の14 bytes大字形を単に拡大表示するだけでは，文字列の幅計算と中央寄せの検証になりません．

特大字形は通常大字形とは別の起動画面専用形式です．K1では10列×2ページの4スロットを持ち，16行すべてを字形領域として使用します．`UI_PrintStringJapaneseExtraLarge`は登録コードを指定位置へ描画し，受信専用の起動画面にだけ使います．出所と変換規則は[FONT_SOURCES.ja.md](FONT_SOURCES.ja.md)を参照してください．

PNGが必要なら，ImageMagickで変換できます．

```powershell
magick -background white bitmap_atlas.svg bitmap_atlas.png
```

manifestを使わず読み取るソースを限定する場合は，`--source`を繰り返し指定します．通常の更新ではmanifestを使用してください．

```powershell
python -X utf8 tools/render_bitmap_atlas.py `
  --source App/bitmaps.c `
  --source App/font.c `
  --source App/japanese_font.c `
  --out tmp/uv-k1-bitmap-atlas `
  --markdown-out docs\FONT_INVENTORY.ja.md
```

同名配列の`[2]`などの表示は，条件コンパイル上の別候補を区別するためのものです．全配列が同一ビルドに同時に入ることや，K1とK5 V3の機種差を解決済みであることを意味しません．

atlas生成ツールはソースや生成済みファームウェアを書き換えません．相互変換ツールも，既定では一時出力へ書き出し，`--in-place`の明示なしにソースを上書きしません．表示の意味や実機LCD上の見え方を自動判定するものでもありません．フォントの帰属・ライセンス表示は既存の`NOTICE`やソースコメントから削除しないでください．
