# 外部日本語bitmapフォント

K1／K5 V3の日本語チャンネル名と，条件を満たす大字タイトル／カテゴリで使う固定フォントデータです。フォントデータは外部SPI Flashへ配置し，ファームウェアの実行時にUnicode索引から16×16のbitmapを読み出します。

## 採用フォント

- 名称: Izumi Gothic-Medium 16dot
- 形式: JIS X 0213:2004 Plane 1、16×16 BDF
- 入力URL: https://unifoundry.com/japanese/izmg16-2004-1.bdf.gz
- 入力アーカイブSHA-256: 005345196615E692C54EF67286B44DD0EAA3A899D066CD407A4B3A810822C20C
- ライセンス: 入力BDFの記載はPublic Domain

入力BDFアーカイブ自体はリポジトリへ同梱しません。生成器は入力ファイルのSHA-256を検査し、上記の正本と一致しない入力を拒否します。生成器はフォント全体の`FONTBOUNDINGBOX`と各字形の`BBX`が`16 16 0 -2`であることも検査し、幅・高さ・基線の異なる入力を拒否します。

## 生成物と形式

- japanese_font.bin: 125604 byte
- 対象glyph: 3489字
- Unicode索引: 13956 byte（Unicode codepoint、glyph indexの各uint16）
- bitmap: 111648 byte（1 glyphあたり16行×uint16）
- 外部Flashフォントデータ領域: 0x020000から
- 外部Flash名前テーブル: 0x040000から、1024件×32 byte
- ASCII: フォントデータには収録せず、既存のgFontBigを使う

対象はJIS X 0208第1水準相当の漢字、かな、記号です。4 byte UTF-8、フォントに収録されていない文字、表示欄を超える名前は段階Aの対象外です。

## 再生成

リポジトリルートで、確認済みのBDFを指定して実行します。

    python -X utf8 tools/generate_japanese_font.py tmp/japanese-font/izmg16-2004-1.bdf.gz

生成先はApp/japanese_font_external.h、docs/fonts/japanese_font.bin、tools/japanese_font_manifest.jsonです。これら3点は同じ入力から生成した派生物として扱い、個別に編集しません。

CHIRPで使用する場合は、これらの生成物を個別にコピーせず、リポジトリルートで`python tools/build_chirp_module.py`を実行して`tools/chirp/wrx_jp_standalone.py`を再生成します。配布用モジュールにはフォントとmanifestが内蔵されるため、CHIRPの`File → Load Module`ではこの単一ファイルを読み込みます。

フォントを無線機へ転送するには、先に`JpRxOnly`ファームウェアを書き込む必要があります。CHIRPのモジュール読み込みだけでは、純正ファームウェアの外部Flashへ書き込めません。

実機の外部Flash容量、JEDEC ID、既存領域との衝突、LCD上の視認性、書き込み速度はホストテストとビルドだけでは確認できません。
