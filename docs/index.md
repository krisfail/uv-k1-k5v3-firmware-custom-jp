# WRX-JP ドキュメント

日本語・受信専用ファームウェアの利用案内，開発資料，フォント資料をまとめています．

利用案内，開発資料，フォント資料は，以下のリンクから参照できます．

## 利用者向け

- [日本語README](../README.ja.md)
- [英語README](../README.md)
- [操作・ビルドのチートシート](../CHEATSHEET.ja.md)

## 開発・検証

- [開発ガイド](../DEVELOPMENT.md)
- [メニュー文言の編集](MENU_TEXT_CATALOG.ja.md)
- [CHIRP互換アダプタの説明](../tools/chirp/README.ja.md)
- [チャンネルリスト形式](CHANNEL_LIST_FORMAT.ja.md)
- [新機能の技術詳細](FEATURES_TECHNICAL.ja.md)
- [機能監査](FEATURE_AUDIT.ja.md)
- [上流からの受信向け取り込み](UPSTREAM_INTEGRATION.ja.md)
- [実機テスト計画](HARDWARE_TEST_PLAN.ja.md)
- [LCDエミュレータ](LCD_EMULATOR.ja.md)

`FEATURES_TECHNICAL.ja.md`には機能の挙動，`FEATURE_AUDIT.ja.md`には有効・保留・除外の分類，`HARDWARE_TEST_PLAN.ja.md`には実機で確認する項目があります．ビルド手順やソースの見取り図は`DEVELOPMENT.md`を参照してください．

## フォント・ビットマップ

- [フォント割り当て台帳](FONT_BITMAP_ANNOTATIONS.ja.md)
- [フォント一覧](FONT_INVENTORY.ja.md)
- [フォント品質診断](FONT_QUALITY.ja.md)
- [フォントの出所と変換](FONT_SOURCES.ja.md)
- [ビットマップ／フォントatlasの説明](BITMAP_ATLAS.ja.md)
- [bitmap atlas SVG](assets/font-atlas/bitmap_atlas.svg)
- [bitmap atlas inventory JSON](assets/font-atlas/bitmap_atlas_inventory.json)

フォントのコードポイントと注釈は[フォント割り当て台帳](FONT_BITMAP_ANNOTATIONS.ja.md)で管理します．C配列はビルド入力，編集時の完全スナップショットJSONは基準値を伴う安全な受け渡し形式です．`FONT_INVENTORY.ja.md`，SVG atlas，inventory JSONはmanifestとソースから生成する成果物です．出所・ライセンスの説明は[フォントの出所と変換](FONT_SOURCES.ja.md)に集約します．

このサイトはGitHub Actionsが`docs/`とルートの利用者向け文書をHTML化して自動公開します．

