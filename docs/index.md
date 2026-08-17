# WRX-JP ドキュメント

日本語・受信専用ファームウェアの利用案内，開発資料，フォント資料をまとめています．

文書の役割を分けています．利用者はREADMEとCHEATSHEET，開発者はDEVELOPMENT，AIエージェントはリポジトリ直下のAGENTS.mdを参照してください．このサイトの文書は実装の説明と検証記録に限定します．

## 利用者向け

- [日本語README](../README.ja.md)
- [英語README](../README.md)
- [操作・ビルドのチートシート](../CHEATSHEET.ja.md)

## 開発者向け

- [開発者向けガイド](../DEVELOPMENT.md)
- [メニュー文言の編集](MENU_TEXT_CATALOG.ja.md)
- [CHIRPドライバの説明](../tools/chirp/README.ja.md)
- [新機能の技術詳細](FEATURES_TECHNICAL.ja.md)
- [機能監査](FEATURE_AUDIT.ja.md)
- [実機テスト計画](HARDWARE_TEST_PLAN.ja.md)

`FEATURES_TECHNICAL.ja.md`は現行機能の挙動，`FEATURE_AUDIT.ja.md`は採用・保留・除外の判断，`HARDWARE_TEST_PLAN.ja.md`は実機で確認する項目を扱います．ビルド手順やソースの見取り図はDEVELOPMENT.mdを正本とします．

## フォント・ビットマップ

- [フォント割り当て台帳](FONT_BITMAP_ANNOTATIONS.ja.md)
- [フォント一覧](FONT_INVENTORY.ja.md)
- [フォントの出所と変換](FONT_SOURCES.ja.md)
- [rainy版との日本語大字形比較](FONT_RAINY_COMPARISON.ja.md)
- [rainy版との全コードポイント比較（K1 Markdown）](assets/font-comparison/rainy-k1/font_diff.md)
- [rainy版との全コードポイント比較（K1 PNG）](assets/font-comparison/rainy-k1/font_diff.png)
- [ビットマップ／フォントatlasの説明](BITMAP_ATLAS.ja.md)
- [bitmap atlas SVG](assets/font-atlas/bitmap_atlas.svg)
- [bitmap atlas inventory JSON](assets/font-atlas/bitmap_atlas_inventory.json)

フォントのコードポイントと注釈は[フォント割り当て台帳](FONT_BITMAP_ANNOTATIONS.ja.md)で管理します．C配列はビルド入力，編集時の完全スナップショットJSONは基準値を伴う安全な受け渡し形式です．`FONT_INVENTORY.ja.md`，SVG atlas，inventory JSONはmanifestとソースから生成する成果物です．出所・ライセンスの説明は[フォントの出所と変換](FONT_SOURCES.ja.md)に集約します．

このサイトはGitHub Actionsが`docs/`とルートの利用者向け文書をHTML化して自動公開します．

