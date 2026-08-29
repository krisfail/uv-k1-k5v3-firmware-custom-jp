# 外部日本語bitmapフォント

段階AのK1／K5 V3用チャンネル名表示で使う固定フォントデータです。フォントデータは外部SPI Flashへ配置し、ファームウェアの実行時にUnicode索引から16×16のbitmapを読み出します。

## 採用フォント

- 名称: Izumi Gothic-Medium 16dot
- 形式: JIS X 0213:2004 Plane 1、16×16 BDF
- 入力URL: https://unifoundry.com/japanese/izmg16-2004-1.bdf.gz
- 入力SHA-256: 005345196615E692C54EF67286B44DD0EAA3A899D066CD407A4B3A810822C20
- ライセンス: 入力BDFの記載はPublic Domain

入力BDF自体はリポジトリへ同梱しません。生成前にSHA-256を確認し、上記の値と一致した入力だけを使います。

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

    python -X utf8 tools/generate_japanese_font.py tmp/japanese-font/izmg16-2004-1.bdf

生成先はApp/japanese_font_external.h、docs/fonts/japanese_font.bin、tools/japanese_font_manifest.jsonです。これら3点は同じ入力から生成した派生物として扱い、個別に編集しません。

実機の外部Flash容量、JEDEC ID、既存領域との衝突、LCD上の視認性、書き込み速度はホストテストとビルドだけでは確認できません。
