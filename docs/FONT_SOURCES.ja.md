# 外部日本語フォントの出所と生成方法

K1／K5 V3の日本語メニュー、カテゴリ、チャンネル名に使用する外部bitmapフォントの出所と生成条件を記録します。固定UIは日本語を主表示とし、外部フォント未書込み時は項目ごとのASCIIフォールバックを使います。

## 採用フォント

- 名称: Izumi Gothic-Medium 16dot
- 形式: JIS X 0213:2004 Plane 1、16×16 BDF
- 配布元: [Unifoundry Japanese Font Encodings](https://unifoundry.com/japanese/)
- 入力ファイル: `izmg16-2004-1.bdf.gz`
- 入力アーカイブSHA-256: `005345196615E692C54EF67286B44DD0EAA3A899D066CD407A4B3A810822C20C`
- ライセンス: 入力BDFの記載はPublic Domain

### 14px専用bitmap

- 名称: WenQuanYi Bitmap Song 10.5pt
- 形式: 14px BDF（14×14セルへ固定化）
- 配布元: [Dondji](https://github.com/EthanYan6/Dondji)に含まれる入力BDF
- 入力ファイル: `App/bdf/wenquanyi_13px.bdf`
- 入力SHA-256: `926AE3E16560F1719C34217E5A9FFAFC81DF18ED1732A5302313DA8359294226`
- ライセンス: 入力BDFの記載はGPL v2（font embedding exception）

この14px bitmapは16px字形の縮小結果ではありません。BDFの字形ごとのBBXとbaselineを14pxセルへ変換して保存します。入力BDFにない記号だけは、Izumi 16をビルド時に面積平均して補完します。補完分も14×14 bitmapとして保存し、実機上では縮小しません。

入力BDFアーカイブ自体はリポジトリへ同梱しません。生成器は入力ファイルのSHA-256と、フォント全体・各字形の固定セル形式を検査します。帰属・ライセンス表示は、入力元の条件に従って保持します。

### 美咲8×8 bitmap

- 名称: 美咲ゴシック BDF版（Misaki Gothic 8dot）
- 形式: 8×8ドット日本語bitmap BDF
- 配布元: [美咲フォント公式ページ](https://littlelimit.net/misaki.htm)
- 入力ファイル: `misaki_gothic.bdf`
- 入力アーカイブ: `misaki_bdf_2021-05-05.zip`
- 入力SHA-256: `28A8745552C844F7C73F11BDF4470225F5E08645A98C5404B2E25BB326A5CABD`
- ライセンス: 同梱`misaki.txt`の記載どおり、改変の有無・商用非商用を問わず使用、複製、再配布を許可。ただし無保証

美咲の8×8 BDFを固定8行・1行1 byteのbitmapへ変換します。字形ごとのBBXと基線を8×8セルへ配置し、実機上で16×16から縮小しません。ASCIIはこのbitmapへ収録せず、既存のF4HWN系内蔵フォントを使います。

## 生成物と形式

- `docs/fonts/japanese_font.bin`: Unicode索引と16×16／14×14／美咲8×8 bitmapをまとめた外部フォント資産
- `App/japanese_font_external.h`: 生成形式と外部Flash配置の定義
- `tools/japanese_font_manifest.json`: 生成条件と入力ハッシュのmanifest

ASCIIは外部フォントへ重複収録せず、ファームウェア内蔵の`App/font.c`を使用します。外部フォントが未書込み、未収録、幅超過、またはASCII表示モードの場合は、保存済みASCII名へフォールバックし、名前が空ならチャンネル番号を表示します。

## 再生成

確認済みのBDFを指定して実行します。

```powershell
python -X utf8 tools/generate_japanese_font.py `
  tmp/japanese-font/izmg16-2004-1.bdf.gz `
  --bdf14 ../other_sources/Dondji/App/bdf/wenquanyi_13px.bdf `
  --bdf8 tmp/japanese-font/misaki-2021-05-05/misaki_gothic.bdf
```

生成先は`docs/fonts/japanese_font.bin`、`App/japanese_font_external.h`、`tools/japanese_font_manifest.json`です。これらは同じ入力から生成した派生物として扱い、個別に編集しません。

生成後は、外部フォントREADME、manifest、atlas、ホスト側の転送テストを確認します。実機の外部Flash容量、JEDEC ID、既存領域との衝突、LCD上の視認性、書き込み速度は、ホストテストとビルドだけでは確認できません。
