# UV-K1 / UV-K5 V3 開発ガイド

このリポジトリは，PY32F071搭載のUV-K1／UV-K5 V3向け`wrx-jp`派生版です．K1とK5 V3は同じファームウェア／host profileとして扱います．CHIRPは移行用互換アダプタであり，正規のhost toolではありません．旧UV-K5（DP32G030）とは対象チップ，ドライバ，メモリーマップ，ビルド系統が異なるため，コードや手順を混ぜないでください．

## 開発を始める前に

- 利用者向けの概要と書き込み手順は[README.md](README.md)または[README.ja.md](README.ja.md)を読む．
- 追加受信機能，外部フラッシュ，フォント，未検証範囲は[docs/FEATURES_TECHNICAL.ja.md](docs/FEATURES_TECHNICAL.ja.md)を正とする．チャンネルリストの列定義と保存規則は[docs/CHANNEL_LIST_FORMAT.ja.md](docs/CHANNEL_LIST_FORMAT.ja.md)に分けて記録する．上流からの受信向け取り込み範囲は[docs/UPSTREAM_INTEGRATION.ja.md](docs/UPSTREAM_INTEGRATION.ja.md)に記録する．
- フォントやビットマップを追加する前に，[docs/FONT_BITMAP_ANNOTATIONS.ja.md](docs/FONT_BITMAP_ANNOTATIONS.ja.md)とatlas inventoryを確認する．
- 実機ファームウェアのLCD描画を画像で確認するときは，[LCDエミュレータ](docs/LCD_EMULATOR.ja.md)を使う．
- 移行用CHIRP互換アダプタの機種プロファイルとcalibration境界は[tools/chirp/README.ja.md](tools/chirp/README.ja.md)を読む．

## ビルドとホストテスト

受信専用境界は[docs/FEATURES_TECHNICAL.ja.md](docs/FEATURES_TECHNICAL.ja.md)，上流からの受信向け取り込み範囲は[docs/UPSTREAM_INTEGRATION.ja.md](docs/UPSTREAM_INTEGRATION.ja.md)，実機確認の項目は[docs/HARDWARE_TEST_PLAN.ja.md](docs/HARDWARE_TEST_PLAN.ja.md)にあります．

ARM GNU Toolchain，CMake，Ninjaを用意し，リポジトリルートで実行します．

```powershell
cmake --preset JpRxOnly
cmake --build --preset JpRxOnly -j2
cmake --build --preset JpRxOnly --target font-quality
python tools/build_chirp_module.py --check
python -m unittest discover -s tests -p "test_*.py" -v
```

生成物は`build/JpRxOnly`以下の`wrx-jp.bin`，`wrx-jp.hex`，`wrx-jp.elf`です．UVTools2で書き込む対象はパック前の`build/JpRxOnly/wrx-jp.bin`です．このリポジトリのCMakeビルドはpacked imageを自動生成しないため，配布用イメージは署名・リリース手順で別途扱います．通常配布用のプリセットは`JpRxOnly`です．

変更後は少なくともホストテスト，ビルド，`git diff --check`を実行します．`test_lcd_emulator.py`はLCDデバッグ経路の通信契約と物理フレームのbit順を確認します．RF性能，実機LCDの見え方，実機書き込みの成功は保証しません．

### ファームウェア描画によるLCD監査

画面レイアウトをPythonで再実装した静的モックは使用しません．実機と同じC描画処理を呼び出す`JpLcdDebug`をビルドし，プログラミングケーブルに接続したCOMポートからフレームを取得します．

```powershell
cmake --preset JpLcdDebug
cmake --build --preset JpLcdDebug --parallel 2
python tools/lcd_emulator.py --port COMx --event menu --out tmp/lcd-menu.png
python tools/lcd_emulator.py --port COMx --all --out tmp/lcd-debug
```

`--all`の標準イベントには，メニューとK1で実際に表示されるカテゴリ，境界値を含むメニュー項目，補足説明，プリセットバンク，4種類のスキャン進捗，警告，受信画面の表示モード・フォント・単一／デュアルVFO・スキャンリスト所属なし／あり，音声スコープの8種類の入力形状，AM／USB・CTCSS／DCS・帯域幅・MONI，低電池・キーロック・DTMF・ステータスを含みます．RX-onlyで登録されないタイマーカテゴリは標準イベントから除外しています．プロトコルと検査範囲は[LCDエミュレータ](docs/LCD_EMULATOR.ja.md)に集約します．実RF受信の確認項目はデバッグ版では再現せず，[実機テスト計画](docs/HARDWARE_TEST_PLAN.ja.md)へ分離します．

## 外部日本語フォント

K1／K5 V3のチャンネル名は，外部Flash上の固定フォントデータと1024件のUTF-8名前テーブルを使います。ここでの1024件はチャンネル／名前slot数であり，fontの収録glyph数や評価文字数ではありません。フォントデータの入力，SHA-256，生成形式は[外部日本語フォントREADME](docs/fonts/README.ja.md)と生成manifestに記録します。WebSerial host toolには1024件チャンネル一覧のTSV読出し・編集・書込みもあります。保存形式とUART境界は[機能の技術詳細](docs/FEATURES_TECHNICAL.ja.md)，ブラウザーからの操作は[WebSerial host toolの説明](docs/WEB_SERIAL_HOST.ja.md)，Python試作GUIの操作は[Python host toolの説明](tools/host/README.ja.md)を参照します。

チャンネル一覧のTSV列定義，v1互換，ASCII別名の保存規則は[チャンネルリスト形式](docs/CHANNEL_LIST_FORMAT.ja.md)に集約します。

確認済みBDFから派生物を再生成する場合は，リポジトリルートで次を実行します。

    python -X utf8 tools/generate_japanese_font.py `
      tmp/japanese-font/izmg16-2004-1.bdf.gz `
      --bdf14 ../other_sources/Dondji/App/bdf/wenquanyi_13px.bdf `
      --bdf8 tmp/japanese-font/misaki-2021-05-05/misaki_gothic.bdf

生成物の外部配置はフォントデータ`0x020000`，名前テーブル`0x060000`です。WebSerial host toolは`tools/webui/`で，フォントと名前テーブルを個別に選択して書き込めます。Pythonの`tools/host/wrx_jp_host.py`はWindows向けの試作・デバッグ用GUIです。各操作は128 byte以下のブロック単位でreadbackを行います。チャンネル一覧は通常論理領域`0x0000–0x886F`と名前テーブルだけを差分書込みし，calibration論理窓`0xB000–0xB1FF`に対応するsector`0x010000–0x010FFF`は，GUIとfirmwareの日本語書込みallowlistから除外します。CHIRPアダプタの外部Flash転送は移行用の暫定実装です。ホストテストとビルドは，実機の外部Flash容量，LCD表示，書き込み，または再起動後の動作を保証しません。

CHIRPの互換経路には，フォントとmanifestを内蔵した`tools/chirp/wrx_jp_standalone.py`を使います。WebSerial host toolとPython host toolは日本語リソースの個別書込みに対応し，CHIRPは互換・移行用です。ドライバソースやフォント生成物を変更した場合は，次を実行して配布用モジュールを更新します。

    python tools/build_chirp_module.py

生成物が最新かどうかは`python tools/build_chirp_module.py --check`で確認できます。CHIRPの外部モジュール読み込みはこの単一ファイルを対象にし、フォントファイルの相対パスに依存させません。

### 主フォントと主画面の表示

16×16の見た目が大きい場合は、設定値`3`の14×14表示を使います。14×14は専用の外部bitmapを読み出すため、16×16字形を実機上で縮小しません。

混在表示の位置合わせは、内蔵ASCII字形を変更せず、和文側の固定セルをサイズごとに実測して行います。16×16はIzumiの16×16セルをそのまま使い、14×14は16pxの名前枠内へ1px下げます。デュアルVFOの8×8名前では、和文とASCIIを同じ8pxセル基準に置き、下方突出を持つASCII字形の形状は変更しません。ASCIIと和文の実インク間隔は、1px未満になる境界だけレイアウト側で補います。デュアルVFOの8×8名前＋周波数では、名前を上段へ収め、周波数を1px下げて名前との間に1pxの空白を確保し、ステータス行も1px下げて周波数との間に1pxの空白を確保します。

日本語フォント生成器は，Izumi 16の16×16 BDF，14px専用BDF，美咲ゴシック8dot BDFから固定bitmapを生成する`tools/generate_japanese_font.py`です。16×16は1字32 byte，14×14は1字28 byte，8×8は1字8 byteで，同じUnicode索引を共有します。主操作画面のチャンネル名はメニューの「主画面チャンネル名」で，16×16，14×14専用bitmap，美咲8×8，ASCII別名のいずれかを選べます。14px BDFにない記号だけは生成時にIzumi 16から補完し，実機上の縮小処理は行いません。8×8も美咲のネイティブbitmapを使い，16×16からのオンザフライ縮小は行いません。ASCII表示は外部字形を使わず，単一VFOでは収まる限り大字形，デュアルVFOでは小字形で表示します。Dondji風メニューで16×16に収まらない選択項目は，8×8で16px枠の中央へ置き，左ペインの反転で選択状態を示します。

### 全字形の実機LCD確認

外部Flashへ転送したJapanese fontの全字形をLCDで確認するため，`JpRxOnlyFontTest` presetを使用します．起動後は通常のradio／application initializationへ進まず，外部FlashのUnicode indexを読み，1画面32字（8列×4行）を表示します．対象は全3,489字で，Unicode index順に約110ページです．`UP`／`DOWN`で前後ページ，`0`で先頭，`9`で末尾へ移動します．PTTを含む送信処理は呼び出しません．

    cmake --preset JpRxOnlyFontTest
    cmake --build --preset JpRxOnlyFontTest -j 2

出力は`build/JpRxOnlyFontTest/wrx-jp-font-test.bin`です．先に通常の日本語リソース書込み手順で`docs/fonts/japanese_font.bin`を外部Flashへ書き込んでください．このpresetと`ENABLE_FONT_GLYPH_TEST`は通常の`JpRxOnly`配布ビルドでは無効です．静的ビルド成功は，実機の外部Flash接続やLCD表示を保証しません．

Izumi 16による日本語表示は実機表示テストの対象です．全対象字形のLCD表示，外部Flash書込み，再起動後の動作は個別に確認します．ホストテスト，画像生成成功，静的チェックを実機表示の保証として扱いません．

## 受信専用ビルド境界

通常配布用のCMakeプリセットは`JpRxOnly`です．`JpRxOnlyFontTest`は外部フォントのLCD確認用，`JpLcdDebug`はUIフレーム取得用で，いずれも通常運用の配布イメージではありません．ルートのCMake設定で`ENABLE_RX_ONLY`を強制し，AirCopy，VOX，アラーム，送信トーン，送信タイマー，RFログなどの送信系モジュールを登録しません．PTTはモニター操作として維持します．UART，USB，SPI，I2Cの制御通信はRF送信ではないため，必要な保守経路として区別します．LCDデバッグ版はUART初期化後にRF初期化を行わず，画面要求の処理だけを継続します．

## ソースの見取り図

| 場所 | 役割 |
| --- | --- |
| `CMakePresets.json` | `JpRxOnly`の定義，機種・機能フラグ，出力名 |
| `App/driver/` | BK4829，BK1080，外部フラッシュなどのドライバ |
| `App/app/` | スキャン，受信拡張，メニュー操作，アプリケーション状態 |
| `App/ui/` | メイン画面，メニュー，起動画面，フォント表示 |
| `App/font.c` / `App/bitmaps.c` | 内蔵ASCIIグリフと画面ビットマップ |
| `tests/` | ホスト側の回帰テスト |
| `tools/chirp/` | K1／K5 V3用RX-only CHIRP互換アダプタと境界説明 |
| `tools/host/` | Python製のデバッグ・試作GUI，通信契約，RX-safe設定モデル |
| `tools/webui/` | 依存ライブラリなしのWebSerial host tool。GitHub Pagesへ静的配置する |
| `tools/lcd_emulator.py` | 実機フレームの取得，検証，PNG変換 |
| `App/app/lcd_debug.c` | UIイベント要求の受付，C描画，物理フレーム転送 |
| `App/ui/menu_icons.c` | カテゴリ別1bitアイコン |

## 変更時の境界

- この版は日本国内向け受信専用です．送信経路，送信メニュー，送信を誘発する操作を再導入しません．PTTはモニターとして維持します．
- `RXExt`は追加受信機能の一括スイッチです．受信専用制約，日本語表示，PTTモニター，FM放送帯域の制約を解除するスイッチにしてはいけません．
- K1／K5 V3の標準設定，チャンネル，calibration，受信拡張用の外部フラッシュ領域を混同しません．新しい永続データを追加する場合は，物理アドレス，復旧手順，CHIRPの境界を確認します．
- calibrationは利用者設定ではありません．通常のCHIRPアップロード範囲へ含めず，低レベルUARTまで絶対保護されるとは仮定しません．
- 実機未検証の動作は，READMEやリリース説明で未検証と明示します．

## フォントとatlas

### 文字コードと再構成方針

内蔵フォントの正規範囲は`0x21`–`0x7E`のASCIIです．メニュー，カテゴリ，設定値，操作選択は，外部フォントへ渡せる日本語を主表示とし，画面領域と可読性に応じて日本語・ASCII略号・単位を使い分けます．日本語のラベル・設定値・操作名は`App/ui/menu_text_ja.h`へ分離し，外部フォント未書込み時は項目ごとに用意したASCII表記へ戻します．ASCIIは既存のF4HWN系内蔵フォントを使います．

大字形と小字形は別配列で管理するため，異なる配列のバイト列をそのまま移植せず，配列ごとのコード範囲と幅を確認してください．K1の固定UIは，日本語ラベルを外部16×16字形で描画し，項目欄に収まらないラベルは外部の美咲8×8字形へ切り替えます．外部字形が使えない場合だけ，対応するASCIIフォールバックへ戻します．

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

内蔵ASCII字形を変更するときは，表示幅，空き要素，RAM使用量を確認します．外部フォントの文字追加・再生成は，入力フォントのライセンスと生成手順を[外部日本語フォントREADME](docs/fonts/README.ja.md)で確認します．

大字形は16行の固定セルで，固定の上下空白は前提にしません．字形ごとに実際の点灯範囲が異なるため，編集画面の動的な上／字形／下区分と「点灯範囲」を確認し，atlasを再生成してください．異なるサイズのbitmapを混在させる描画経路では，ASCIIを動かさず，和文側だけ各サイズの実測結果に基づく補正を行います．

### C配列とJSONの安全な往復

`tools/font_source_json.py`は，コードポイント付きの完全スナップショットJSONをC配列と相互変換します．JSONの各要素には抽出時の`base_bytes_hex`と編集後の`bytes_hex`があり，適用時にC側の基準値が変わっていれば停止します．K1の指定初期化子はコードポイント式をそのまま保持し，K5のASCII配列や別配列を行番号で置換しません．

```powershell
python -X utf8 tools/font_source_json.py extract `
  --source App\font.c --array gFontSmall --start-code 0x21 `
  --output tmp/gFontSmall.source.json
python -X utf8 tools/font_source_json.py apply `
  --source App\font.c --input tmp/gFontSmall.source.json `
  --output tmp/font.c
```

一時Cファイルのatlas，`git diff --no-index`，ビルドを確認してから，必要な場合だけ`--in-place`で反映します．既存の`wrx-jp-font-patch-v1`は簡易UIパッチであり，完全スナップショットより検証情報が少ないため，適用時は`--legacy-patch`を明示します．
注釈のない連続配列（例：`App/font.c`の`gFontSmall`）は，先頭コードを明示して抽出します（例：`--start-code 0x21`）．

### インタラクティブ編集

`tools/font_editor.html`をブラウザで開き，`docs/assets/font-atlas/bitmap_atlas_inventory.json`を読み込むと，字形のドットを編集できます．左ドラッグは連続点灯／消灯，右ドラッグは消去，描画モードでは点灯・消灯を固定できます．マウス移動が速くてもセル間を補間し，1回のドラッグを1回のUndo単位として扱います．Space/Enterによるキーボード編集，注釈の編集，C初期化子のコピーに対応します．字形を切り替えても編集内容と注釈は保持され，最後に全字形・Bitmapの変更を1つのJSONパッチとしてコピー／保存できます．HTTP経由で標準台帳を自動読込する場合は，リポジトリルートで次を実行してから表示します．

「文字列プレビュー」に文字列を入力すると，選択中の配列に登録された字形を入力順に横並びで確認できます．表示幅に応じて自動改行し，各字形は配列本来のセル幅のまま描画します．現在編集中の字形は編集内容を即時反映し，未登録の文字は赤枠で示します．「例を入れる」は配列に応じた短いASCII確認用文字列です．JSONパッチは台帳を読み込んだ後，「JSONパッチ」から選択して読み込めます．

```powershell
python -m http.server 8765
```

WebUIのJSONパッチは編集内容の確認・受け渡し用です．C配列へ反映する場合は，まず`font_source_json.py extract`で完全スナップショットを作り，編集値を移してから一時Cファイルへ`apply`します．コードポイント，コメント，ソース配列，atlasを確認してからソースへ反映してください．

### GitHub Pages

`.github/workflows/pages.yml`は，`docs/`とルートの利用者向け文書をJekyllでHTML化し，GitHub Pagesへ公開します．ローカルでPages用の入力を確認する場合は次を実行します．

WebSerial版host toolは`tools/webui/`で管理し，Pages公開時は`/host/`へコピーします．`https`で配信されるGitHub Pagesではブラウザーからシリアルポートを選択できます．ローカルで確認する場合も，ファイルを直接開かず，リポジトリルートをHTTPサーバーで配信してください．WebSerialに対応しないブラウザーや，実機のファームウェア・外部Flashとの互換性は，静的Pages生成だけでは検証できません．

```powershell
python tools/prepare_github_pages.py --source docs --destination .pages-source
```

リポジトリのSettings → PagesでSourceを`GitHub Actions`に設定してください．`.pages-source/`と`_site/`はサイト公開用の生成物です．

## コミット，署名，実機確認

既存の未コミット変更を確認してから編集し，意図しない生成物や改行変換を取り込まないでください．コミット，タグ，署名，リリース用バイナリの作成は，リポジトリ管理者の手順に従います．署名が必要な場合は，対話的な署名者の手順を変更しません．

実機へ書き込む前に，個体のcalibrationと必要なメモリーをバックアップし，機種に一致するイメージを使います．静的テストやビルド成功を，実機動作の保証として扱わないでください．

