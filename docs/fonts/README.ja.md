# 外部日本語bitmapフォント

このディレクトリには，K1／K5 V3の日本語チャンネル名と，固定UIの一部で使う生成済みフォント資産を置きます．実行時には外部SPI FlashからUnicode索引を読み，16×16，14×14または8×8のbitmapを選びます．

フォントの出所，ライセンス，入力ファイルのSHA-256，変換規則は[フォントの出所と生成方法](../FONT_SOURCES.ja.md)を正本とします．コードポイントと字形の割り当ては[フォント割り当て台帳](../FONT_BITMAP_ANNOTATIONS.ja.md)，生成時の件数・サイズ・ハッシュは`tools/japanese_font_manifest.json`と[フォント一覧](../FONT_INVENTORY.ja.md)を参照してください．このREADMEでは，同じ内容を重複して管理しません．

## 生成物

- `japanese_font.bin`: Unicode索引と16×16／14×14／美咲8×8 bitmapをまとめた外部Flash用データ
- `../../App/japanese_font_external.h`: 生成形式と外部Flash配置の定義
- `../../tools/japanese_font_manifest.json`: 入力ハッシュ，収録字形，領域サイズのmanifest

ASCIIは外部フォントへ収録せず，既存のF4HWN系内蔵フォントを使います．外部フォントが未書込み，未収録，幅超過，またはASCII表示モードの場合は，保存済みASCII名へフォールバックします．名前が空の場合はチャンネル番号を表示します．

入力BDFアーカイブはリポジトリへ同梱しません．生成器は入力ファイルのSHA-256と固定セル形式を検査し，正本と一致しない入力や，表示欄を超える名前を拒否します．4 byte UTF-8やmanifestにない文字も書き込み対象にしません．

## 再生成

リポジトリルートで，入力フォントの出所とハッシュを確認してから実行します．

```powershell
python -X utf8 tools/generate_japanese_font.py `
  tmp/japanese-font/izmg16-2004-1.bdf.gz `
  --bdf14 ../other_sources/Dondji/App/bdf/wenquanyi_13px.bdf `
  --bdf8 tmp/japanese-font/misaki-2021-05-05/misaki_gothic.bdf
```

生成後は`cmake --build --preset JpRxOnly --target font-atlas`，`python tools/font_quality.py`，フォント転送テストを実行します．生成物は同じ入力から再生成し，個別に編集しません．CHIRPの配布用モジュールを更新する場合は，続けて`python tools/build_chirp_module.py`を実行します．

フォントを無線機へ転送するには，先に`JpRxOnly`ファームウェアを書き込む必要があります．実機の外部Flash容量，JEDEC ID，既存領域との衝突，LCD上の視認性，書き込み速度は，ホストテストとビルドだけでは確認できません．
