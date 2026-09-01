# 日本語フォントの出所と変換方法

## `受信専用`の字形

起動画面で使う`受`，`信`，`専`，`用`の10×16特大字形と，`0x98=専`，`0x99=用`の通常大字形を，Unifoundryが公開する**Izumi 16 Plane 1，JIS X 0213:2004**の16×16 BDFから独立に変換しました．配布元は，Izumi 16をパブリックドメインのJIS X 0213フォントとして案内しています．

- 配布元: [Unifoundry Japanese Font Encodings](https://unifoundry.com/japanese/)
- ファイル: `izmg16-2004-1.bdf.gz`
- 取得元URL: `https://unifoundry.com/japanese/izmg16-2004-1.bdf.gz`
- SHA-256: `005345196615E692C54EF67286B44DD0EAA3A899D066CD407A4B3A810822C20C`
- ライセンス上の扱い: 配布元の説明に従い，該当字形はパブリックドメイン

ここでいうJIS X 0213は，入力フォントの字形を選ぶための規格です．ファームウェア内の1 byteコード体系そのものをJIS X 0213として扱う意味ではありません．ファームウェア側では，`0xA1`–`0xDF`だけをJIS X 0201半角カタカナとして扱い，その他の拡張範囲は[フォント割り当て台帳](FONT_BITMAP_ANNOTATIONS.ja.md)の定義に従います．

他の日本語字形の帰属・ライセンスは保持します．`rainy-knight/uv-k5-jp`由来部分の帰属は`NOTICE`に記載します．

## 内部フォールバック用の変換ツール

`tools/import_public_domain_bitmap_font.py`は，起動画面と内部フォールバック用の字形を更新する補助ツールです．外部Izumi 16の正本を生成する経路ではありません．BDFを入力した場合は，次の手順でC初期化子候補を生成します．

1. BDFの16×16ビットマップを読み取る．
2. ISO-2022-JPのJIS row-cell値で対象字形を選択する．
3. 通常大字形は16行の固定セルへ変換し，字形固有の点灯範囲を保持する．起動画面用の特大字形は16行すべてを使用可能にする．
4. `専`／`用`は，16×16の線の構造を7列／10列へ収める独立の低解像度再構成を使う．その他の字形は，対象列へ対応するソース列に点が一つでもあれば点灯する縮小規則で変換する．
5. OLEDのLSB-first，2ページ形式へC初期化子として出力する．

K1では通常大字形の`0x98`／`0x99`と，`ALL`／`MESSAGE`で使う10×16特大字形の4字を使用します．特大字形は通常大字形の上下配置を流用せず，起動画面で16行を使います．ビルドは取得済みBDFを必要とせず，変換後のC配列だけを使用します．

変換例:

```powershell
python -X utf8 tools/import_public_domain_bitmap_font.py `
  tmp/open-fonts/izmg16-2004-1.bdf.gz
```

ソースへ反映したら，atlasとフォント一覧を再生成します．

```powershell
python -X utf8 tools/render_bitmap_atlas.py `
  --out docs/assets/font-atlas `
  --markdown-out docs/FONT_INVENTORY.ja.md
```
