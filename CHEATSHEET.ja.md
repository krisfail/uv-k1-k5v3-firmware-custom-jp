# UV-K1 / UV-K5 V3 cheatsheet

[日本語版README](README.ja.md) | [英語版README](README.md) | [開発ガイド](DEVELOPMENT.md) | [CHIRPドライバ](tools/chirp/README.ja.md)

注意事項，forkの関係，免責，バックアップの要件は[README.ja.md](README.ja.md)を確認してください．

## 版の選択

| 版 | 用途 | 送信 |
| --- | --- | --- |
| `JpRxOnly` | 日本語・受信専用 | 無効．PTTはモニター |

このリポジトリで提供する日本語版は`JpRxOnly`のみです．上流系の送信可能な構成は国内向け受信機版として扱わないでください．

## ビルド（リポジトリのルート）

### 日本語・受信専用版

```powershell
# 初回，またはbuild/JpRxOnlyがない場合
cmake --preset JpRxOnly

# ビルド
cmake --build --preset JpRxOnly -j2
```

出力: `build/JpRxOnly/wrx-jp.bin`

UVTools2で書き込むのはパック前の`build/JpRxOnly/wrx-jp.bin`です．`*.packed.bin`はpack対応ツール用です．

### テスト

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

## 実機操作

| 操作 | 動作 |
| --- | --- |
| `M`短押し | メニュー／確定 |
| `EXIT` | 戻る／キャンセル |
| `UP` / `DOWN` | 選択・周波数変更 |
| `F` + `2 A/B` | VFO A/B切替 |
| `F` + `3 VFO/MR` | VFO／メモリー切替 |
| `PTT` | `JpRxOnly`ではモニター切替 |
| `F` + `0 FM` | FM放送 |
| `* SCAN`長押し | スキャン開始 |
| スキャン中に`F1`短押し | 現在周波数を一時スキップ |

## 表示メッセージ

- 受信専用画面では送信出力の`LOW`／`HIGH`を表示しません．
- 通常の`PTT`はモニターです．予期しない送信要求があった場合だけ，`RX ONLY`とビープ音で知らせます（内部状態名は`TX DISABLE`）．
- 条件に合わない受信操作は，`RXExt OFF`，`VFO ONLY`，`SCAN ACTIVE`，`FM ONLY`などの理由を表示します．

## CHIRP

機種選択，バックアップ，校正領域の保護範囲は[CHIRPドライバの説明](tools/chirp/README.ja.md)を確認してください．要点は，K1／K5 V3プロファイルを選び，アップロード前に全イメージを保存し，送信設定を扱わないことです．

## 受信設定

| 設定 | 値・動作 |
| --- | --- |
| `W/N` | 受信帯域の切替 |
| 受信モード | `MAIN ONLY` / `DUAL RX` / `SINGLE` |
| `Bank` | `ALL` / `B1`〜`B8` |
| スケルチ | 数値または`AUTO` |
| `RXExt` | 追加受信機能をまとめて`ON` / `OFF`（初期値`ON`） |
| プリセット | 周波数モードで`STAR`短押し |
| FM放送 | `76.0–95.0 MHz` |

RX-onlyメニューは，`RXExt`，`AUTO`，`SCAN`，`INFO`，`REV`，`AUDIO`，`NARROW`，`FAST`など，短く意味を取りやすいASCII表記を使います．日本語チャンネル名は，主画面の設定に応じて外部16×16，専用14×14，美咲8×8，ASCII別名で表示します．

`RXExt=OFF`では，プリセット，SINGLE，バンク絞り込み，AUTOスケルチ，AGCガード，一時スキップが停止します．受信専用動作，PTTモニター，外部チャンネル名表示，FM放送帯域制限は維持されます．

## 書き込み前チェック

- 機種に合う版を選んだか
- `JpRxOnly`を選んでいるか
- 校正データをバックアップしたか
- `JpRxOnly`ではPTTが送信ではなくモニターになることを確認したか

## 隠しメニュー

電源OFF時に`PTT`と上側サイドキーを同時に押しながら電源を入れます．RX-only版では送信項目はなく，`BatCal`，`BatTyp`，`Reset`などの保守項目を開けます．`Reset`の前にEEPROMとcalibrationをバックアップしてください．

