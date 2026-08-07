# UV-K1 / UV-K5 V3 cheatsheet

[日本語版README](README.ja.md) | [英語版README](README.md)

注意事項、forkの関係、AI支援開発、免責、バックアップの要件は[README.ja.md](README.ja.md)を確認してください。

## 版の選択

| 版 | 用途 | 送信 |
| --- | --- | --- |
| `JpRxOnly` | 日本語・受信専用 | 無効。PTTはモニター |
| `Custom` | 通常版 | 送信可能な構成 |

## ビルド（リポジトリのルート）

### 日本語・受信専用版

```powershell
# 初回、またはbuild/JpRxOnlyがない場合
cmake --preset JpRxOnly

# ビルド
cmake --build --preset JpRxOnly -j2
```

出力: `build/JpRxOnly/wrx-jp.bin`

### 通常版

```powershell
cmake --preset Custom
cmake --build --preset Custom -j2
```

出力: `build/Custom/uv-k1-custom.bin`

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

## 受信設定

| 設定 | 値・動作 |
| --- | --- |
| `W/N` | `WIDE` / `WIDE+` / `NARROW` |
| 受信モード | `MAIN ONLY` / `DUAL RX` / `SINGLE` |
| `Bank` | `ALL` / `B1`〜`B8` |
| スケルチ | 数値または`AUTO` |
| プリセット | 周波数モードで`STAR`短押し |
| FM放送 | `76.0–95.0 MHz` |

## 書き込み前チェック

- 機種に合う版を選んだか
- `JpRxOnly`と`Custom`を取り違えていないか
- 校正データをバックアップしたか
- `JpRxOnly`ではPTTが送信ではなくモニターになることを確認したか
