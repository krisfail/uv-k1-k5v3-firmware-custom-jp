# 開発者向けガイド（UV-K1 / UV-K5 V3）

このリポジトリは，PY32F071搭載のUV-K1／UV-K5 V3向け`wrx-jp`派生版です．K1とK5 V3は同じファームウェア／CHIRPプロファイルとして扱います．旧UV-K5（DP32G030）とは対象チップ，ドライバ，メモリーマップ，ビルド系統が異なるため，コードや手順を混ぜないでください．

この文書は人間の開発者向けです．利用者向けの説明は[README.ja.md](README.ja.md)，[README.md](README.md)，[CHEATSHEET.ja.md](CHEATSHEET.ja.md)に置きます．実装の根拠・保存形式・未検証範囲は`docs/`の技術資料で管理します．

## 開発を始める前に

- 利用者向けの概要と書き込み手順は[README.md](README.md)または[README.ja.md](README.ja.md)を読む．
- 追加受信機能，外部フラッシュ，フォント，未検証範囲は[docs/FEATURES_TECHNICAL.ja.md](docs/FEATURES_TECHNICAL.ja.md)を正とする．上流v5.9.0からの受信向け取り込み範囲は[docs/UPSTREAM_INTEGRATION.ja.md](docs/UPSTREAM_INTEGRATION.ja.md)に分けて記録する．
- フォントやビットマップを追加する前に，[docs/FONT_BITMAP_ANNOTATIONS.ja.md](docs/FONT_BITMAP_ANNOTATIONS.ja.md)とatlas inventoryを確認する．
- CHIRPの機種プロファイルとcalibration境界は[tools/chirp/README.ja.md](tools/chirp/README.ja.md)を読む．

## ビルドとホストテスト

現行の機能採否と受信専用境界は[docs/FEATURE_AUDIT.ja.md](docs/FEATURE_AUDIT.ja.md)を正とします．追加順の経過は[docs/FEATURE_PRIORITY.ja.md](docs/FEATURE_PRIORITY.ja.md)，上流からの変更を加えた部分のレビュー結果は[docs/CODE_REVIEW_UPSTREAM_DELTA.ja.md](docs/CODE_REVIEW_UPSTREAM_DELTA.ja.md)に残しています．実機確認は[docs/HARDWARE_TEST_PLAN.ja.md](docs/HARDWARE_TEST_PLAN.ja.md)を使います．

ARM GNU Toolchain，CMake，Ninjaを用意し，リポジトリルートで実行します．

```powershell
cmake --preset JpRxOnly
cmake --build --preset JpRxOnly -j2
cmake --build --preset JpRxOnly --target font-quality
python -m unittest discover -s tests -p "test_*.py" -v
```

生成物は`build/JpRxOnly`以下の`wrx-jp.bin`，`wrx-jp.hex`，`wrx-jp.elf`です．UVTools2で書き込む対象はパック前の`build/JpRxOnly/wrx-jp.bin`です．このリポジトリのCMakeビルドはpacked imageを自動生成しないため，配布用イメージは署名・リリース手順で別途扱います．`JpRxOnly`が唯一のサポート対象プリセットです．

変更後は少なくともホストテスト，ビルド，`git diff --check`を実行します．テストはソース構造や境界を確認するもので，RF性能，LCDの見え方，実機書き込みの成功を保証しません．

## 受信専用ビルド境界

利用可能なCMakeプリセットは`JpRxOnly`だけです．ルートのCMake設定で`ENABLE_RX_ONLY`を強制し，AirCopy，VOX，アラーム，送信トーン，送信タイマー，RFログなどの送信系モジュールを登録しません．PTTはモニター操作として維持します．UART，USB，SPI，I2Cの制御通信はRF送信ではないため，必要な保守経路として区別します．

## ソースの見取り図

| 場所 | 役割 |
| --- | --- |
| `CMakePresets.json` | `JpRxOnly`の定義，機種・機能フラグ，出力名 |
| `App/driver/` | BK4829，BK1080，外部フラッシュなどのドライバ |
| `App/app/` | スキャン，受信拡張，メニュー操作，アプリケーション状態 |
| `App/ui/` | メイン画面，メニュー，起動画面，フォント表示 |
| `App/font.c` / `App/japanese_font.c` / `App/bitmaps.c` | 文字グリフと画面ビットマップ |
| `tests/` | ホスト側の回帰テスト |
| `tools/chirp/` | K1／K5 V3用RX-only CHIRPドライバと境界説明 |

## ビルド基盤の共通境界

旧UV-K5は`Makefile`を正規入口とし，K5向けCMakeは移行検証用の併行入口です．このリポジトリは`CMakePresets.json`の`JpRxOnly`を正規入口とします．両方で`JpRxOnly`，`font-atlas`，`atlas`，`inventory`，`docs`という操作契約と`tools/font_inventory.json`のmanifest形式を揃えています．

一方，ファームウェアのC／ASM，ドライバ，startup，リンカースクリプトは共有しません．DP32G030とPY32F071では，BK4819／BK4829，EEPROM／外部フラッシュ，メモリーマップ，送信禁止境界が異なるためです．共通のホストツールをsubmodule化する場合は，両リポジトリから参照できる正式な共通リポジトリと固定コミットを先に用意し，親作業フォルダへの相対依存は作らないでください．

## 変更時の境界

- この版は日本国内向け受信専用です．送信経路，送信メニュー，送信を誘発する操作を再導入しません．PTTはモニターとして維持します．
- `RXExt`は追加受信機能の一括スイッチです．受信専用制約，日本語表示，PTTモニター，FM放送帯域の制約を解除するスイッチにしてはいけません．
- K1／K5 V3の標準設定，チャンネル，calibration，受信拡張用の外部フラッシュ領域を混同しません．新しい永続データを追加する場合は，物理アドレス，復旧手順，CHIRPの境界を確認します．
- calibrationは利用者設定ではありません．通常のCHIRPアップロード範囲へ含めず，低レベルUARTまで絶対保護されるとは仮定しません．
- 実機未検証の動作は，READMEやリリース説明で未検証と明示します．

## フォントとatlas

### 文字コードと再構成方針

正規の文字対応は[フォント割り当て台帳](docs/FONT_BITMAP_ANNOTATIONS.ja.md)に従います．`0x21`–`0x7E`はASCII，`0xA1`–`0xDF`はJIS X 0201半角カタカナです．`0x80`–`0xA0`と`0xE0`–`0xFF`はJIS文字ではなく，プロジェクト固有の拡張領域または予約領域です．`0x5C`と`0x7E`の扱いは，JIS X 0201へ再解釈せず，現行ASCIIフォントの実装を維持します．

rainy由来の基準大字形には，`0x9A`–`0xA5`と`0xB0`の空白，`0xA6`／`0xDD`と`0xA7`／`0xB1`の重複，`0xA1`注釈以降の行ずれがあります．K1は大／小フォントが別配列なので，K5の配列をバイト列として移植せず，コードポイントごとに再構成してください．現行のsmall字形はカタカナの主表示には小さすぎるため，将来medium字形を導入する場合は，固定幅，文字列幅，中央寄せ，RAM，容量を同時に検証します．

フォントの意味・用途・コードポイントは`tools/font_inventory.json`で管理し，C配列はビルド入力です．編集用の完全スナップショットJSONはC配列から生成し，基準バイト列との一致を検証してからCへ戻します．追跡済みatlasとinventoryを更新するには，次を実行します．この処理はファームウェアの通常ビルドには含めていません．

```powershell
cmake --build --preset JpRxOnly --target font-atlas
```

一時ディレクトリへ出力する場合は，例えば次を実行します．

```powershell
python -X utf8 tools/render_bitmap_atlas.py `
  --manifest tools/font_inventory.json `
  --out tmp/uv-k1-bitmap-atlas `
  --markdown-out tmp/uv-k1-bitmap-atlas/font_inventory.generated.ja.md
```

rainy版との14-byte大字形のソース比較と差分表示は，[比較記録](docs/FONT_RAINY_COMPARISON.ja.md)を参照します．出力先は公開パスを含めない`tmp`配下にします．

```powershell
python -X utf8 tools/compare_japanese_font.py `
  --reference-source <rainy-repo>\font.c `
  --current-source App\japanese_font.c `
  --out tmp\rainy-font-comparison-k1
```

新しい文字は既存コードや字形の重複を確認してから追加します．コードポイント，意味，元バイト列は台帳とソースコメントの両方に残してください．K1はK5よりフラッシュに余裕がありますが，表示幅とRAM使用量を確認してから拡張します．

大字形は欧文・日本語とも16行の固定セルですが，固定の上下空白は前提にしません．字形ごとに実際の点灯範囲が異なるため，編集画面の動的な上／字形／下区分と「点灯範囲」を確認し，atlasを再生成してください．描画側に日本語専用の位置補正を追加してはいけません．

### C配列とJSONの安全な往復

`tools/font_source_json.py`は，コードポイント付きの完全スナップショットJSONをC配列と相互変換します．JSONの各要素には抽出時の`base_bytes_hex`と編集後の`bytes_hex`があり，適用時にC側の基準値が変わっていれば停止します．K1の指定初期化子はコードポイント式をそのまま保持し，K5のASCII配列や別配列を行番号で置換しません．

```powershell
python -X utf8 tools/font_source_json.py extract `
  --source App\japanese_font.c --array gFontBigJapanese `
  --output tmp/gFontBigJapanese.source.json
python -X utf8 tools/font_source_json.py apply `
  --source App\japanese_font.c --input tmp/gFontBigJapanese.source.json `
  --output tmp/japanese_font.c
```

一時Cファイルのatlas，`git diff --no-index`，ビルドを確認してから，必要な場合だけ`--in-place`で反映します．既存の`wrx-jp-font-patch-v1`は簡易UIパッチであり，完全スナップショットより検証情報が少ないため，適用時は`--legacy-patch`を明示します．
注釈のない連続配列（例：`App/font.c`の`gFontSmall`）は，先頭コードを明示して抽出します（例：`--start-code 0x21`）．

### インタラクティブ編集

`tools/font_editor.html`をブラウザで開き，`docs/assets/font-atlas/bitmap_atlas_inventory.json`を読み込むと，字形のドットを編集できます．左ドラッグは連続点灯／消灯，右ドラッグは消去，描画モードでは点灯・消灯を固定できます．マウス移動が速くてもセル間を補間し，1回のドラッグを1回のUndo単位として扱います．Space/Enterによるキーボード編集，注釈の編集，C初期化子のコピーに対応します．字形を切り替えても編集内容と注釈は保持され，最後に全字形・Bitmapの変更を1つのJSONパッチとしてコピー／保存できます．HTTP経由で標準台帳を自動読込する場合は，リポジトリルートで次を実行してから表示します．

「文字列プレビュー」に文字列を入力すると，選択中の配列に登録された字形を入力順に横並びで確認できます．表示幅に応じて自動改行し，各字形は配列本来のセル幅のまま描画します．現在編集中の字形は編集内容を即時反映し，未登録の文字は赤枠で示します．「日本語例」では，配列に関係なくJIS X 0201相当の句読点・カタカナ・濁点・半濁点を設定します．「例を入れる」は配列に応じた短い確認用文字列です．JSONパッチは台帳を読み込んだ後，「JSONパッチ」から選択して読み込めます．

```powershell
python -m http.server 8765
```

WebUIのJSONパッチは編集内容の確認・受け渡し用です．C配列へ反映する場合は，まず`font_source_json.py extract`で完全スナップショットを作り，編集値を移してから一時Cファイルへ`apply`します．コードポイント，コメント，ソース配列，atlasを確認してからソースへ反映してください．

### GitHub Pages

`.github/workflows/pages.yml`は，`docs/`とルートの利用者向け文書をJekyllでHTML化し，GitHub Pagesへ公開します．ローカルでPages用の入力を確認する場合は次を実行します．

```powershell
python tools/prepare_github_pages.py --source docs --destination .pages-source
```

リポジトリのSettings → PagesでSourceを`GitHub Actions`に設定してください．`.pages-source/`と`_site/`は生成物であり，コミットしません．

## コミット，署名，実機確認

既存の未コミット変更を確認してから編集し，意図しない生成物や改行変換を取り込まないでください．コミット，タグ，署名，リリース用バイナリの作成は，リポジトリ管理者の手順に従います．署名が必要な場合は，対話的な署名者の手順を変更しません．

実機へ書き込む前に，個体のcalibrationと必要なメモリーをバックアップし，機種に一致するイメージを使います．新機能の静的テストやビルド成功を，実機動作の保証として扱わないでください．

