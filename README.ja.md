# UV-K1 / UV-K5 V3 日本語・受信専用ファームウェア

[英語版README](README.md) | [操作・ビルドcheatsheet](CHEATSHEET.ja.md) | [開発者向けガイド](DEVELOPMENT.md) | [CHIRPドライバ](tools/chirp/README.ja.md) | [新機能の技術詳細](docs/FEATURES_TECHNICAL.ja.md) | [フォントコード表](docs/FONT_BITMAP_ANNOTATIONS.ja.md) | [機能監査](docs/FEATURE_AUDIT.ja.md) | [実機テスト計画](docs/HARDWARE_TEST_PLAN.ja.md) | [bitmap/font atlas](docs/BITMAP_ATLAS.ja.md) | [ドキュメントサイト](docs/index.md)

## このリポジトリの位置づけ

このリポジトリは，[krisfail/uv-k1-k5v3-firmware-custom-jp](https://github.com/krisfail/uv-k1-k5v3-firmware-custom-jp)として公開している独立したフォークです．主なupstreamは[armel/uv-k1-k5v3-firmware-custom](https://github.com/armel/uv-k1-k5v3-firmware-custom)で，F4HWN版，Egzumer版などの成果を基にしています．本リポジトリの日本語・受信専用版は，UV-K1とUV-K5 V3を日本国内向けの受信機用途へ調整した派生版であり，公式Quansheng版，公式F4HWN版，armel版そのものではありません．

## AI支援（AI-Assisted）開発と現状有姿での提供

コードの分析，実装，テスト補助，文書作成の一部にAI支援を使用しています．公開前に保守者が確認していますが，AI支援は保守者によるレビューや利用者の実機確認を代替しません．

ファームウェアは**現状有姿（AS IS）**で提供し，動作や特定目的への適合を保証しません．書き込み失敗，無線機の破損，校正データ・EEPROM・設定の消失，復旧不能，法令・無線規制に反する使用について，保守者は責任を負いません．書き込み前に校正データと必要なメモリーをバックアップし，機種に対応したイメージと復旧手段を用意してください．

## この文書で分かること

この文書は，PY32F071搭載のUV-K1とUV-K5 V3向けファームウェアを，日本語でビルド・書き込み・操作するための案内です．初回は「版の選択」「ビルド」「書き込み」を順に確認し，日常の操作は[CHEATSHEET.ja.md](CHEATSHEET.ja.md)を参照してください．

### 詳しい情報

- 日常操作と最小限のビルド手順は[CHEATSHEET.ja.md](CHEATSHEET.ja.md)
- CHIRPの機種選択・読み書き範囲・校正領域は[CHIRPドライバの説明](tools/chirp/README.ja.md)
- 開発者向けのソース構成・検証・atlas生成は[DEVELOPMENT.md](DEVELOPMENT.md)
- 実装の詳細は[技術詳細](docs/FEATURES_TECHNICAL.ja.md)，採否と除外機能は[機能監査](docs/FEATURE_AUDIT.ja.md)，実機確認項目は[実機テスト計画](docs/HARDWARE_TEST_PLAN.ja.md)

このREADMEは利用者向けの案内です．実装の詳細や開発手順は，上記の開発者向け文書にまとめています．

## 先に版を選ぶ

このリポジトリで利用するCMakeプリセットは，日本語・受信専用の`JpRxOnly`だけです．送信可能な上流系プリセットはこのフォークから除外しています．

| プリセット | 用途 | 送信 | 主な生成物 |
| --- | --- | --- | --- |
| `JpRxOnly` | 日本語・日本国内向け受信専用 | 無効．PTTはモニター | `build/JpRxOnly/wrx-jp.bin` |

このリポジトリで提供する日本語版は`JpRxOnly`です．送信を行わない受信機として使う場合は，必ずこのプリセットを選んでください．上流系の送信可能な構成は，日本語版または国内向け受信機版として提供していません．

## `JpRxOnly`の機能

- 送信処理，送信系メニュー，送信トーンを無効化
- PTTをモニター操作へ割り当て
- 表示名は`Kris v5.9.0J1`，エディション名は`JP-RX-Only`
- `MAIN ONLY`，`DUAL RX`，`SINGLE`の受信モード
- `W+` 25 kHz，`W` 20 kHz，`N` 12.5 kHz，`N-` 6.25 kHzの受信帯域
- メモリーバンクによるスキャン対象の絞り込み
- 航空，船舶，公共用途，アマチュア，351 MHzデジタル，FM放送などの受信プリセット
- FM放送受信を国内向けの`76.0–95.0 MHz`に制限
- RSSI・ノイズを使う`AUTO`スケルチ
- FM受信時の急激なゲイン変化を抑えるAGCガード
- `RXExt`で追加受信機能をまとめてON/OFF（初期値ON）
- RX-onlyメニューの主要項目を日本語化（受信拡張，優先，情報，反転，音声，自動，狭帯，高速など）
- メニューをカテゴリ別に表示（`ALL`で従来の全項目表示へ戻せる）
- `F`を押しながらサイドキーを長押しして，そのキーへ割り当てる受信操作を一覧から選択
- K1のフラッシュ容量を使い，受信音声プロファイルと音声レベル履歴を有効化
- 大きい文字と小さい文字に対応した日本語表示．小字形は数値・補助表示を中心とし，カタカナを含む通常の日本語表示にはmedium字形の導入を検討中
- 起動画面の`受信専用`に使う大字形は，パブリックドメインのIzumi 16から独立変換しています．詳細は[フォントの出所と変換](docs/FONT_SOURCES.ja.md)を参照してください．

メニューの`受信拡張`（従来表記`RXExt`）を`OFF`にすると，プリセット，受信モードの`SINGLE`，メモリーバンク絞り込み，`自動`スケルチ，AGCガード，一時スキップを停止します．通常受信の4段階帯域幅，受信専用・PTTモニター，日本語表示，FM放送の`76.0–95.0 MHz`制限は変わりません．周波数ステップは帯域幅と独立して選べます．既存の保存データは互換性のためONとして扱います．

追加の受信設定は，標準の設定・チャンネル名・校正領域とは別の外部フラッシュ領域を使用します．設定領域を変更する場合も，書き込み前の校正データのバックアップは省略しないでください．CHIRPの校正領域保護とメモリーマップの詳細は[CHIRPドライバの説明](tools/chirp/README.ja.md)にまとめています．

## ビルド（Windows PowerShell）

コマンドはリポジトリのルートで実行します．必要なものはCMake，Ninja，ARM GNUツールチェーン（`arm-none-eabi-gcc`）です．

### 日本語・受信専用版

`build/JpRxOnly`がまだない初回は，必ず先に構成を生成します．`cmake --build`だけを実行すると，ビルドディレクトリがない場合に失敗します．

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

フォント／bitmapのatlasとinventoryはファームウェアとは別の明示的なターゲットです．追跡済み成果物を更新する場合は次を実行します．

```powershell
cmake --build --preset JpRxOnly --target font-atlas
```

## CHIRPドライバ

受信メモリーの読み書きには，[wrx-jp CHIRPドライバ](tools/chirp/README.ja.md)を使用します．K1とK5 V3は同じドライバプロファイル，旧UV-K5は別プロファイルです．K1／K5 V3では，日本語チャンネル名のフォントデータと名前テーブルもアップロード時に扱います．ドライバを単独配置する場合は，[外部日本語フォント](docs/fonts/README.ja.md)の生成物をドライバと同じディレクトリへ置いてください．アップロード前に対象機種の全イメージを保存してください．ドライバも受信専用で，送信設定は扱いません．

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

`JpRxOnly`のPTTはモニター動作です．送信機能を使う目的で`JpRxOnly`を変更・再有効化する手順は，この文書の対象外です．

メニューカテゴリ画面では`UP/DOWN`でカテゴリを選び，`M`で項目一覧へ入ります．`EXIT`でカテゴリ一覧へ戻り，`ALL`ではカテゴリ分け前と同じ全項目を表示します．アクション選択画面では`UP/DOWN`で操作を選び，`M`で確定，`EXIT`または`F`でキャンセルします．RX専用版では送信電力やPTTを割り当てる候補は表示しません．

## 隠しメニュー

電源OFFの状態で`PTT`と上側サイドキーを同時に押しながら電源を入れると，隠しメニューを開けます．受信専用版では送信ロック・送信調整項目は表示せず，`BatCal`，`BatTyp`，`Reset`などの保守項目を残しています．EEPROM初期化が必要な場合は`Reset`を使用する前に，EEPROMとcalibrationのバックアップを確認してください．

## 表示と利用できない操作

- 受信専用画面では送信出力の`LOW`／`HIGH`表示を出しません．
- 通常の`PTT`はモニター操作です．予期しないTX要求が最終的な安全ゲートへ到達した場合だけ，ビープ音と`TX DISABLE`を表示します．
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

