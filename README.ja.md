# UV-K1 / UV-K5 V3 日本語・受信専用ファームウェア

[英語版README](README.md) | [操作・ビルドcheatsheet](CHEATSHEET.ja.md)

## このリポジトリの位置づけ

このリポジトリは、[krisfail/uv-k1-k5v3-firmware-custom-jp](https://github.com/krisfail/uv-k1-k5v3-firmware-custom-jp)として公開している独立したフォークです。主なupstreamは[armel/uv-k1-k5v3-firmware-custom](https://github.com/armel/uv-k1-k5v3-firmware-custom)で、F4HWN版、Egzumer版などの成果を基にしています。本リポジトリの日本語・受信専用版は、UV-K1とUV-K5 V3を日本国内向けの受信機用途へ調整した派生版であり、公式Quansheng版、公式F4HWN版、armel版そのものではありません。

## AI支援（AI-Assisted）開発と現状有姿での提供

コードの分析、実装、テスト補助、文書作成の一部にAI支援を使用しています。採用前にソースコード、静的テスト、ビルド、可能な範囲の実機結果を確認していますが、AI支援は保守者によるレビューや利用者の実機確認を代替しません。

ファームウェアは**現状有姿（AS IS）**で提供し、動作や特定目的への適合を保証しません。書き込み失敗、無線機の破損、校正データ・EEPROM・設定の消失、復旧不能、法令・無線規制に反する使用について、保守者は責任を負いません。書き込み前に校正データと必要なメモリーをバックアップし、機種に対応したイメージと復旧手段を用意してください。

## この文書で分かること

この文書は、PY32F071搭載のUV-K1とUV-K5 V3向けファームウェアを、日本語でビルド・書き込み・操作するための案内です。初回は「版の選択」「ビルド」「書き込み」を順に確認し、日常の操作は[CHEATSHEET.ja.md](CHEATSHEET.ja.md)を参照してください。

## 先に版を選ぶ

このリポジトリには、用途の異なるCMakeプリセットがあります。日本語・受信専用版と通常版を取り違えないでください。

| プリセット | 用途 | 送信 | 主な生成物 |
| --- | --- | --- | --- |
| `JpRxOnly` | 日本語・日本国内向け受信専用 | 無効。PTTはモニター | `build/JpRxOnly/wrx-jp.bin` |
| `Custom` | 通常のカスタム版 | 有効な構成 | `build/Custom/uv-k1-custom.bin` |

送信を行わない受信機として使う場合は、必ず`JpRxOnly`を選んでください。`Custom`は受信専用版ではありません。

## `JpRxOnly`の機能

- 送信処理、送信系メニュー、送信トーンを無効化
- PTTをモニター操作へ割り当て
- `MAIN ONLY`、`DUAL RX`、`SINGLE`の受信モード
- `WIDE`、`WIDE+`、`NARROW`の受信帯域
- メモリーバンクによるスキャン対象の絞り込み
- 航空、船舶、公共用途、アマチュア、351 MHzデジタル、FM放送などの受信プリセット
- FM放送受信を国内向けの`76.0–95.0 MHz`に制限
- RSSI・ノイズを使う`AUTO`スケルチ
- FM受信時の急激なゲイン変化を抑えるAGCガード
- 大きい文字と小さい文字に対応した日本語表示

追加の受信設定は外部フラッシュの`0x00B000`以降を使用します。標準の設定、チャンネル名、校正領域とは別の領域ですが、書き込み前の校正データのバックアップは省略しないでください。

## ビルド（Windows PowerShell）

コマンドはリポジトリのルートで実行します。必要なものはCMake、Ninja、ARM GNUツールチェーン（`arm-none-eabi-gcc`）です。

### 日本語・受信専用版

`build/JpRxOnly`がまだない初回は、必ず先に構成を生成します。`cmake --build`だけを実行すると、ビルドディレクトリがない場合に失敗します。

```powershell
cmake --preset JpRxOnly
cmake --build --preset JpRxOnly -j2
```

主な生成物:

- `build/JpRxOnly/wrx-jp.bin`: 書き込み用バイナリ
- `build/JpRxOnly/wrx-jp.hex`: HEX形式
- `build/JpRxOnly/wrx-jp.elf`: デバッグ用ELF

構成生成後にソースだけを変更した場合は、次のビルドだけで構いません。

```powershell
cmake --build --preset JpRxOnly -j2
```

### 通常版

```powershell
cmake --preset Custom
cmake --build --preset Custom -j2
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
| `PTT` | `JpRxOnly`ではモニター切替。送信しない |
| `F` + `0 FM` | FM放送受信 |
| `* SCAN`長押し | スキャン開始 |
| スキャン中に`F1`短押し | 現在周波数を一時スキップ |

## 書き込み前後

1. UV Studioなどで校正データをバックアップする。
2. 対象機種に合う`JpRxOnly`または`Custom`の`.bin`を選ぶ。
3. DFUモードで書き込む。
4. 起動後、表示版、周波数入力、FM放送、受信音、PTTの動作を確認する。

`JpRxOnly`のPTTはモニター動作です。送信機能を使う目的で`JpRxOnly`を変更・再有効化する手順は、この文書の対象外です。

## 困ったとき

- `build/JpRxOnly is not a directory`: リポジトリのルートで`cmake --preset JpRxOnly`を先に実行します。
- `arm-none-eabi-gcc`が見つからない: ARM GNUツールチェーンをPATHへ追加します。
- Ninjaが見つからない: NinjaをインストールしてPATHを確認します。
- 書き込み後に表示や動作がおかしい: 機種向けイメージか、校正データのバックアップがあるかを確認します。

## 問い合わせ

報告時は、機種名、プリセット名、ファームウェア表示版、使用したファイル名、再現手順を添えてください。英語版READMEと上流版の[Wiki](https://github.com/armel/uv-k1-k5v3-firmware-custom/wiki)も参照できます。
