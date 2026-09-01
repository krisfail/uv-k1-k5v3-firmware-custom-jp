# WRX-JP 専用 host tool

`wrx_jp_host.py` は，PY32F071搭載のUV-K1／UV-K5 V3へ接続する小規模Windows GUIである。対象ファームウェアはこのリポジトリの`JpRxOnly`だけとし，CHIRPの代替となる正規操作入口として使用する。

## 起動

リポジトリルートで次を実行する。

```powershell
python -m pip install -r tools/host/requirements.txt
python tools/host/wrx_jp_host.py
```

Pythonを含むWindows packageは提供していない。現行版は実機未検証の開発用ツールである。

## 操作範囲

- **メモリー**：K1の論理メモリーを読出し／通常領域だけ書込みする。
- **チャンネル一覧**：1024件を既存のK1/K5 V3配置からTSVへ読出し、周波数、mode、tone、step、scan list、名前を編集して通常チャンネル領域へ書き戻す。変更ブロックだけを転送する。
- **設定**：`0xA000–0xA16F`の設定・FM領域を読出し，hex編集後に書き込む。
- **日本語リソース**：同梱の固定Izumi 16 bitmap fontと，UTF-8で1024行の名前ファイルを一つの操作で書き込む。

日本語リソースは任意BDFを受け付けない。名前はUTF-8 31 byte以内，manifest収録文字のみ，表示幅95 pixel以内でなければ拒否する。scrollと無線機上の日本語入力は実装しない。

## calibrationの安全境界

calibrationの論理領域`0xB000–0xB1FF`は読出しだけ許可し，host toolの通常書込みから除外する。対応する外部Flash上のcalibration sector`0x010000–0x010FFF`へ書く経路は設けない。

日本語fontは`0x020000–0x03EAA3`，1024件名前テーブルは`0x040000–0x047FFF`に固定する。firmware側もこの二つのallowlistだけを外部Flash書込み対象とする。各128 byte以下のブロックは書込み後にreadbackを比較し，不一致時は最大3回再試行する。二重化，journal，firmware側rollbackは行わない。

接続時にはversion応答と日本語外部Flashコマンドを確認し，確認できない場合は書込みを開始しない。長いUART処理はGUIのworker threadで実行するため，転送中も画面操作は固まらない（同時通信は一件に制限する）。純正firmwareへのfont転送は成立しない。

チャンネル一覧のTSVは`WRX-JP channel list v1`形式で、1024行を連番で保持する。日本語名は外部名前テーブルへ、ASCII名は既存16 byte slotへ保存し、書込み時に受信専用の送信周波数・送信toneをゼロ化する。font binary自体はチャンネル一覧書込みでは更新しないため、先に「日本語リソース」タブで書き込む。

実機のFlash容量，固定領域衝突，LCD表示，電源断後の再実行は別途確認が必要である。buildやhostテストの成功を実機動作の保証とは扱わない。
