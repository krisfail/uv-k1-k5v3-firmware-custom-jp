# 外部日本語フォントの出所と生成方法

K1／K5 V3の日本語チャンネル名に使用する外部bitmapフォントの出所と生成条件を記録します。固定UIのメニュー、警告、操作選択はASCII表記を基本とし、この外部フォントへ依存しません。

## 採用フォント

- 名称: Izumi Gothic-Medium 16dot
- 形式: JIS X 0213:2004 Plane 1、16×16 BDF
- 配布元: [Unifoundry Japanese Font Encodings](https://unifoundry.com/japanese/)
- 入力ファイル: `izmg16-2004-1.bdf.gz`
- 入力アーカイブSHA-256: `005345196615E692C54EF67286B44DD0EAA3A899D066CD407A4B3A810822C20C`
- ライセンス: 入力BDFの記載はPublic Domain

入力BDFアーカイブ自体はリポジトリへ同梱しません。生成器は入力ファイルのSHA-256と、フォント全体・各字形の16×16形式を検査します。帰属・ライセンス表示は、入力元の条件に従って保持します。

## 生成物と形式

- `docs/fonts/japanese_font.bin`: Unicode索引と16×16 bitmapをまとめた外部フォント資産
- `App/japanese_font_external.h`: 生成形式と外部Flash配置の定義
- `tools/japanese_font_manifest.json`: 生成条件と入力ハッシュのmanifest

ASCIIは外部フォントへ重複収録せず、ファームウェア内蔵の`App/font.c`を使用します。外部フォントが未書込み、未収録、幅超過、またはASCII表示モードの場合は、保存済みASCII名へフォールバックし、名前が空ならチャンネル番号を表示します。

## 再生成

確認済みのBDFを指定して実行します。

```powershell
python -X utf8 tools/generate_japanese_font.py `
  tmp/japanese-font/izmg16-2004-1.bdf.gz
```

生成先は`docs/fonts/japanese_font.bin`、`App/japanese_font_external.h`、`tools/japanese_font_manifest.json`です。これらは同じ入力から生成した派生物として扱い、個別に編集しません。

生成後は、外部フォントREADME、manifest、atlas、ホスト側の転送テストを確認します。実機の外部Flash容量、JEDEC ID、既存領域との衝突、LCD上の視認性、書き込み速度は、ホストテストとビルドだけでは確認できません。
