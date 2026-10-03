# UV-K1 / UV-K5 V3 日本語・受信専用ファームウェア

[英語版README](README.md) | [操作・ビルドcheatsheet](CHEATSHEET.ja.md) | [開発ガイド](DEVELOPMENT.md) | [WebSerial host tool](docs/WEB_SERIAL_HOST.ja.md) | [チャンネルリスト形式](docs/CHANNEL_LIST_FORMAT.ja.md) | [CHIRP互換アダプタ](tools/chirp/README.ja.md) | [機能の技術詳細](docs/FEATURES_TECHNICAL.ja.md) | [フォントコード表](docs/FONT_BITMAP_ANNOTATIONS.ja.md) | [実機テスト計画](docs/HARDWARE_TEST_PLAN.ja.md) | [bitmap/font atlas](docs/BITMAP_ATLAS.ja.md) | [ドキュメントサイト](docs/index.md)

## このリポジトリの位置づけ

このリポジトリは，[krisfail/uv-k1-k5v3-firmware-custom-jp](https://github.com/krisfail/uv-k1-k5v3-firmware-custom-jp)として公開している独立したフォークです．主なupstreamは[armel/uv-k1-k5v3-firmware-custom](https://github.com/armel/uv-k1-k5v3-firmware-custom)で，F4HWN版，Egzumer版などの成果を基にしています．本リポジトリの日本語・受信専用版は，UV-K1とUV-K5 V3を日本国内向けの受信機用途へ調整した派生版であり，公式Quansheng版，公式F4HWN版，armel版そのものではありません．

ファームウェアは**現状有姿（AS IS）**で提供し，動作や特定目的への適合を保証しません．書き込み失敗，無線機の破損，校正データ・EEPROM・設定の消失，復旧不能，法令・無線規制に反する使用について，保守者は責任を負いません．書き込み前に校正データと必要なメモリーをバックアップし，機種に対応したイメージと復旧手段を用意してください．

## 初回の流れ

対象機種を確認し，「版の選択」「ビルド」「書き込み」の順に進めてください．日常の操作は[CHEATSHEET.ja.md](CHEATSHEET.ja.md)を参照してください．

### 参考資料

- 日常操作と最小限のビルド手順は[CHEATSHEET.ja.md](CHEATSHEET.ja.md)
- WebSerial host toolとPython試作GUI，CHIRP互換アダプタの位置づけは[WebSerial host toolの説明](docs/WEB_SERIAL_HOST.ja.md)，[Python host toolの説明](tools/host/README.ja.md)，[CHIRP互換アダプタの説明](tools/chirp/README.ja.md)
- ソース構成・検証・atlas生成は[DEVELOPMENT.md](DEVELOPMENT.md)
- 実装の詳細と受信専用境界は[技術詳細](docs/FEATURES_TECHNICAL.ja.md)，実機確認項目は[実機テスト計画](docs/HARDWARE_TEST_PLAN.ja.md)


## 先に版を選ぶ

このリポジトリで利用するCMakeプリセットは，日本語・受信専用の`JpRxOnly`だけです．送信可能な上流系プリセットはこのフォークから除外しています．

| プリセット | 用途 | 送信 | 主な生成物 |
| --- | --- | --- | --- |
| `JpRxOnly` | 日本語・日本国内向け受信専用 | 無効（PTTはモニター操作） | `build/JpRxOnly/wrx-jp.bin` |

このリポジトリで提供する日本語版は`JpRxOnly`です．送信を行わない受信機として使う場合は，必ずこのプリセットを選んでください．上流系の送信可能な構成は，日本語版または国内向け受信機版として提供していません．

## `JpRxOnly`の機能

- 送信処理，送信系メニュー，送信トーンを無効化
- PTTをモニター操作へ割り当て
- 表示名は`Kris v5.9.0J3`，エディション名は`JP-RX-Only`
- `MAIN ONLY`，`DUAL RX`，`SINGLE`の受信モード
- 受信帯域の選択
- メモリーバンクによるスキャン対象の絞り込み
- 航空，船舶，公共用途，アマチュア，351 MHz帯などの受信プリセット
- FM放送受信を国内向けの`76.0–95.0 MHz`に制限
- RSSI・ノイズを使う`AUTO`スケルチ
- FM受信時の急激なゲイン変化を抑えるAGCガード
- `RXExt`で追加受信機能をまとめてON/OFF（初期値ON）
- RX-onlyメニューの主要項目を短い日本語表記へ整理（受信拡張，優先，情報，反転，音声，自動，狭帯など）
- Dondji風のカテゴリランチャーからメニューを分類表示（`ALL`で従来の全項目表示へ戻せる）
- カテゴリごとの意味が分かる線画アイコンを表示し，主画面のチャンネル名は16×16／専用14×14／美咲8×8／ASCII別名から選択可能
- `F`を押しながらサイドキーを長押しして，そのキーへ割り当てる受信操作を一覧から選択
- K1のフラッシュ容量を使い，受信音声プロファイルと音声レベル履歴を有効化
- メニュー，カテゴリ，警告，操作選択は，画面領域と可読性を優先して日本語・ASCII略号・単位を使い分ける．外部フォント未書込み時にも操作に必要な情報を失わないよう，必要な箇所にはASCIIフォールバックを用意する
- カテゴリ，メニュー，警告のLCD配置を画像で確認できます
- 日本語メニュー・カテゴリとUTF-8のチャンネル名には，Izumi 16，専用14px bitmap，美咲8×8 bitmapから生成した外部フォントを使用します．詳細は[フォントの出所と生成方法](docs/FONT_SOURCES.ja.md)を参照してください．

メニューの`受信拡張`（従来表記`RXExt`）を`OFF`にすると，プリセット，受信モードの`SINGLE`，メモリーバンク絞り込み，`自動`スケルチ，AGCガード，一時スキップを停止します．受信専用・PTTモニター，外部チャンネル名表示，FM放送の`76.0–95.0 MHz`制限は変わりません．既存の保存データは互換性のためONとして扱います．

追加の受信設定は，標準の設定・チャンネル名・校正領域とは別の外部フラッシュ領域を使用します．設定領域を変更する場合も，書き込み前の校正データのバックアップは省略しないでください．CHIRP互換アダプタの校正領域保護とメモリーマップの詳細は[説明文書](tools/chirp/README.ja.md)にまとめています．

## ビルド（Windows PowerShell）

コマンドはリポジトリのルートで実行します．必要なものはCMake，Ninja，ARM GNUツールチェーン（`arm-none-eabi-gcc`）です．

### 日本語・受信専用版

初回など，`build/JpRxOnly`がない場合は，先に構成を生成します．ビルドディレクトリがない状態で`cmake --build`だけを実行すると失敗します．

```powershell
cmake --preset JpRxOnly
cmake --build --preset JpRxOnly -j2
```

主な生成物:

- `build/JpRxOnly/wrx-jp.bin`: 書き込み用バイナリ
- `build/JpRxOnly/wrx-jp.hex`: HEX形式
- `build/JpRxOnly/wrx-jp.elf`: デバッグ用ELF

UVTools2で書き込む場合は，パック済みではない`build/JpRxOnly/wrx-jp.bin`を選択してください．`*.packed.bin`はpack形式に対応したツールや配布用に保持するファイルで，UVTools2へそのまま渡すものではありません．

このリポジトリのCMakeビルドはpacked imageを自動生成しません．配布用のpacked imageが必要な場合は，署名・リリース手順に従って別途生成します．

構成生成後にソースだけを変更した場合は，次のビルドだけで構いません．

```powershell
cmake --build --preset JpRxOnly -j2
```

フォント／bitmapのatlasとinventoryは，ファームウェアとは別に更新します．atlasを更新する場合は次を実行します．

```powershell
cmake --build --preset JpRxOnly --target font-atlas
```

## host toolとCHIRP互換アダプタ

正規の操作環境は，[WebSerial host tool](tools/webui/index.html)です．ChromeまたはEdgeのHTTPSページから，ドライバーなしでUV-K1／UV-K5 V3へ接続できます．「メモリー編集」「1024件チャンネル一覧」「設定」「日本語リソース」を分け，変更したバイト数，変更したブロック数，読み戻し結果を画面に表示します．

Pythonの[Windows GUI host tool](tools/host/README.ja.md)は，デバッグ・試作・互換確認用として残しています．日常の書き込みはWebSerial版を使用してください．

CHIRPは互換・移行用アダプタです．使用する場合は[CHIRP互換アダプタの説明](tools/chirp/README.ja.md)を参照してください．日本語リソースの明示的な書込みは，WebSerial host toolまたはPython host toolで行います．

ドライバまたはフォント資産を変更した場合は，リポジトリルートで配布用モジュールを再生成します．

```powershell
python tools/build_chirp_module.py
```

### 静的テスト

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

## 基本操作

| 操作 | 動作 |
| --- | --- |
| `M`短押し | メニューを開く／項目を確定 |
| `UP` / `DOWN` | 項目・周波数・設定値を移動 |
| `EXIT` | 戻る／キャンセル |
| `F` + `2 A/B` | VFO A/B切替 |
| `F` + `3 VFO/MR` | VFO／メモリー切替 |
| `PTT` | `JpRxOnly`ではモニター切替．送信しない |
| `F` + `0 FM` | FM放送受信 |
| `* SCAN`長押し | スキャン開始 |
| スキャン中に`F1`短押し | 現在周波数を一時スキップ |

## 書き込み前後

1. UV Studioなどで校正データをバックアップする．
2. 対象機種に合う`JpRxOnly`の`.bin`を選ぶ．
3. DFUモードで書き込む．
4. 起動後，表示版，周波数入力，FM放送，受信音，PTTの動作を確認する．

`JpRxOnly`のPTTはモニター動作です．`JpRxOnly`に送信機能はありません．

メニューカテゴリ画面はDondji風のランチャーです．K1の左右キーまたは数字キー1〜9でカテゴリを切り替え，`M`でカテゴリ内の項目一覧へ入ります．10番目以降のカテゴリは左右キーで選びます．`EXIT`でランチャーへ戻り，`ALL`ではカテゴリ分け前と同じ全項目を表示します．アクション選択画面では`UP/DOWN`で操作を選び，`M`で確定，`EXIT`または`F`でキャンセルします．RX専用版では送信電力やPTTを割り当てる候補は表示しません．

## 隠しメニュー

電源OFFの状態で`PTT`と上側サイドキーを同時に押しながら電源を入れると，保守項目を表示できます．受信専用版では送信ロック・送信調整項目は表示せず，`BatCal`，`BatTyp`，`Reset`などを残しています．EEPROM初期化が必要な場合は，`Reset`を使用する前にEEPROMとcalibrationをバックアップしてください．

## 表示と利用できない操作

- 受信専用画面では送信出力の`LOW`／`HIGH`表示を出しません．
- 通常の`PTT`はモニター操作です．予期しない送信要求を拒否した場合は，ビープ音と`RX ONLY`を表示します．
- 受信拡張の条件が合わない操作は，ビープ音だけでなく`RXExt OFF`，`VFO ONLY`，`SCAN ACTIVE`，`FM ONLY`など短い理由を表示します．
- 起動画面の`MESSAGE`／`ALL`は，この版の受信専用メッセージを表示します．`LOGO+MSG`では画像と用途表示を続けて確認できます．

## 困ったとき

- `build/JpRxOnly is not a directory`: リポジトリのルートで`cmake --preset JpRxOnly`を先に実行します．
- `arm-none-eabi-gcc`が見つからない: ARM GNUツールチェーンをPATHへ追加します．
- Ninjaが見つからない: NinjaをインストールしてPATHを確認します．
- 書き込み後に表示や動作がおかしい: 機種向けイメージか，校正データのバックアップがあるかを確認します．

## 問い合わせ

報告時は，機種名，プリセット名，ファームウェア表示版，使用したファイル名，再現手順を添えてください．英語版READMEと上流版の[Wiki](https://github.com/armel/uv-k1-k5v3-firmware-custom/wiki)も参照できます．

## 謝辞

上流プロジェクトのほか，受信専用・広帯域受信機化の設計検討では`UV-K5-RX-JP`の機能の一部を参考にしました．実装・ライセンス・配布物の権利関係はそれぞれの原著作物に従います．

メニューランチャーの構成は，[Dondji](https://github.com/EthanYan6/Dondji)の公開実装を参考にしました．Dondjiのソースコードや画像資産は取り込まず，K1向けに独自実装しています．

