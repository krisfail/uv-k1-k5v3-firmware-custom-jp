# 開発者向けガイド（UV-K1 / UV-K5 V3）

このリポジトリは、PY32F071搭載のUV-K1／UV-K5 V3向け`wrx-jp`派生版です。K1とK5 V3は同じファームウェア／CHIRPプロファイルとして扱います。旧UV-K5（DP32G030）とは対象チップ、ドライバ、メモリーマップ、ビルド系統が異なるため、コードや手順を混ぜないでください。

## 開発を始める前に

- 利用者向けの概要と書き込み手順は[README.md](README.md)または[README.ja.md](README.ja.md)を読む。
- 追加受信機能、外部フラッシュ、フォント、未検証範囲は[docs/FEATURES_TECHNICAL.ja.md](docs/FEATURES_TECHNICAL.ja.md)を正とする。
- フォントやビットマップを追加する前に、[docs/FONT_BITMAP_ANNOTATIONS.ja.md](docs/FONT_BITMAP_ANNOTATIONS.ja.md)とatlas inventoryを確認する。
- CHIRPの機種プロファイルとcalibration境界は[tools/chirp/README.ja.md](tools/chirp/README.ja.md)を読む。

## ビルドとホストテスト

ARM GNU Toolchain、CMake、Ninjaを用意し、リポジトリルートで実行します。

```powershell
cmake --preset JpRxOnly
cmake --build --preset JpRxOnly -j2
python -m unittest discover -s tests -p "test_*.py" -v
```

生成物は`build/JpRxOnly`以下の`wrx-jp.bin`、`wrx-jp.hex`、`wrx-jp.elf`です。`JpRxOnly`以外のCMakeプリセットは上流系の機能比較用であり、日本語・国内向け受信専用版ではありません。

変更後は少なくともホストテスト、ビルド、`git diff --check`を実行します。テストはソース構造や境界を確認するもので、RF性能、LCDの見え方、実機書き込みの成功を保証しません。

## ソースの見取り図

| 場所 | 役割 |
| --- | --- |
| `CMakePresets.json` | `JpRxOnly`の定義、機種・機能フラグ、出力名 |
| `App/driver/` | BK4829、BK1080、外部フラッシュなどのドライバ |
| `App/app/` | スキャン、受信拡張、メニュー操作、アプリケーション状態 |
| `App/ui/` | メイン画面、メニュー、起動画面、フォント表示 |
| `App/font.c` / `App/japanese_font.c` / `App/bitmaps.c` | 文字グリフと画面ビットマップ |
| `tests/` | ホスト側の回帰テスト |
| `tools/chirp/` | K1／K5 V3用RX-only CHIRPドライバと境界説明 |

## 変更時の境界

- この版は日本国内向け受信専用です。送信経路、送信メニュー、送信を誘発する操作を再導入しません。PTTはモニターとして維持します。
- `RXExt`は追加受信機能の一括スイッチです。受信専用制約、日本語表示、PTTモニター、FM放送帯域の制約を解除するスイッチにしてはいけません。
- K1／K5 V3の標準設定、チャンネル、calibration、受信拡張用の外部フラッシュ領域を混同しません。新しい永続データを追加する場合は、物理アドレス、復旧手順、CHIRPの境界を確認します。
- calibrationは利用者設定ではありません。通常のCHIRPアップロード範囲へ含めず、低レベルUARTまで絶対保護されるとは仮定しません。
- 実機未検証の動作は、READMEやリリース説明で未検証と明示します。

## フォントとatlas

注釈付きatlasを生成するには、例えば次を実行します。

```powershell
python -X utf8 tools/render_bitmap_atlas.py `
  --source App/font.c `
  --source App/japanese_font.c `
  --source App/bitmaps.c `
  --out C:\Users\yukim\uv-kx-jp\tmp\uv-k1-bitmap-atlas
```

新しい文字は既存コードや字形の重複を確認してから追加します。コードポイント、意味、元バイト列は台帳とソースコメントの両方に残してください。K1はK5よりフラッシュに余裕がありますが、表示幅とRAM使用量を確認してから拡張します。

## コミット、署名、実機確認

既存の未コミット変更を確認してから編集し、意図しない生成物や改行変換を取り込まないでください。コミット、タグ、署名、リリース用バイナリの作成は、リポジトリ管理者の手順に従います。署名が必要な場合は、対話的な署名者の手順を変更しません。

実機へ書き込む前に、個体のcalibrationと必要なメモリーをバックアップし、機種に一致するイメージを使います。新機能の静的テストやビルド成功を、実機動作の保証として扱わないでください。
