# フォント品質診断

`tools/font_quality.py`は，生成済み`bitmap_atlas_inventory.json`の構造を検査し，字形表の破損を早期に検出する開発者向けツールです．フォントの好みや視認性を自動判定するものではなく，台帳とバイト列の整合性を確認します．

## 実行方法

リポジトリのルートで次を実行します．

```powershell
python -X utf8 tools/render_bitmap_atlas.py `
  --manifest tools/font_inventory.json `
  --out docs/assets/font-atlas `
  --markdown-out docs/assets/font-atlas/font_inventory.generated.ja.md
python -X utf8 tools/font_quality.py `
  --inventory docs/assets/font-atlas/bitmap_atlas_inventory.json `
  --manifest tools/font_inventory.json
```

`error`が出た場合は，フォントをファームウェアへ反映する前に原因を確認します．`warning`は注釈不足などの要確認事項，`info`はmanifestで明示した意図的な空きスロットです．

## 検査内容

- 字形のバイト長，配列全体の`size`，`element_width`の整合性
- コードポイントの重複
- `occupied`フラグと実際のバイト列の一致
- 意図した空きスロット以外の空字形
- `codepoint_labels`で定義したコードポイントと注釈の一致
- 点灯ビットがあるのに注釈がない字形

予約領域や，別サイズのフォントだけに置く字形を空のまま保持する場合は，`tools/font_inventory.json`の対象配列へ次のように記録します．

```json
"quality": { "expected_empty": ["0x98-0xA0"] }
```

この指定は空字形を無条件に許可するものではありません．指定されたスロットにビットが入った場合，または指定されたスロット自体が台帳に存在しない場合は`error`になります．

## 現行台帳の基準状態

現行のK1/K5 V3台帳では，予約空きスロットだけが`info`として報告され，`error`は発生しないことを基準にします．この診断で問題がなくても，線の太さ，字形の読みやすさ，LCD上の配置までは保証されません．変更後はatlas画像と実機表示を併せて確認してください．
