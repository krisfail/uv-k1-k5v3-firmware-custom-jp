# UV-K1 / UV-K5 V3 cheatsheet

[日本語版README](README.ja.md) | [英語版README](README.md) | [CHIRPドライバ](tools/chirp/README.ja.md)

注意事項、forkの関係、AI支援開発、免責、バックアップの要件は[README.ja.md](README.ja.md)を確認してください。

このファイルは早見表です。対象機種、メモリーマップ、CHIRPの読み書き範囲などの説明を重複して管理しません。

## 版の選択

| 版 | 用途 | 送信 |
| --- | --- | --- |
| `JpRxOnly` | 日本語・受信専用（v5.8.0J3） | 無効。PTTはモニター |

このリポジトリで提供する日本語版は`JpRxOnly`のみです。上流系の送信可能な構成は国内向け受信機版として扱わないでください。

## ビルド（リポジトリのルート）

### 日本語・受信専用版

```powershell
# 初回、またはbuild/JpRxOnlyがない場合
cmake --preset JpRxOnly

# ビルド
cmake --build --preset JpRxOnly -j2
```

出力: `build/JpRxOnly/wrx-jp.bin`

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

## CHIRP

機種選択、バックアップ、校正領域の保護範囲は[CHIRPドライバの説明](tools/chirp/README.ja.md)を確認してください。要点は、K1／K5 V3プロファイルを選び、アップロード前に全イメージを保存し、送信設定を扱わないことです。

## 受信設定

| 設定 | 値・動作 |
| --- | --- |
| `W/N` | `W` 20 kHz / `N` 12.5 kHz / `N-` 6.25 kHz |
| 受信モード | `MAIN ONLY` / `DUAL RX` / `SINGLE` |
| `Bank` | `ALL` / `B1`〜`B8` |
| スケルチ | 数値または`AUTO` |
| `RXExt` | 追加受信機能をまとめて`ON` / `OFF`（初期値`ON`） |
| プリセット | 周波数モードで`STAR`短押し |
| FM放送 | `76.0–95.0 MHz` |

RX-onlyメニューでは、`RXExt`は「受信拡張」、スケルチの`AUTO`は「自動」と表示されます。優先スキャン、情報、反転、音声、自動、狭帯、高速などの主要項目も日本語表示です。大文字の長音「ー」も専用グリフで表示します。

`RXExt=OFF`では、プリセット、SINGLE、バンク絞り込み、AUTOスケルチ、AGCガード、一時スキップが停止します。通常受信の3段階帯域幅、受信専用動作、PTTモニター、日本語表示、FM放送帯域制限は維持されます。周波数ステップは帯域幅と独立して選択できます。

## 書き込み前チェック

- 機種に合う版を選んだか
- `JpRxOnly`を選んでいるか
- 校正データをバックアップしたか
- `JpRxOnly`ではPTTが送信ではなくモニターになることを確認したか
