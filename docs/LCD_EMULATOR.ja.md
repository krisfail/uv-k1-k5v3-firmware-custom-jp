# LCDエミュレータ

`tools/lcd_emulator.py`は、K1／K5 V3のST7565互換LCDへ渡す128×64ドットのフレームバッファを画像として表示します。ファームウェアの実行結果ではなく、UIの配置、文字の重なり、アイコンの欠けを確認するための静的な表示です。

## 使い方

リポジトリのルートで実行します。PNG出力にはPillowが必要です。

```powershell
python tools/lcd_emulator.py --screen categories --out tmp/lcd-categories.png
python tools/lcd_emulator.py --screen menu --out tmp/lcd-menu.png
python tools/lcd_emulator.py --screen popup --out tmp/lcd-popup.png
python tools/lcd_emulator.py --screen receive --out tmp/lcd-receive.png
```

`categories`はカテゴリ画面を一覧にし、`menu`は通常の項目一覧と値表示中の2状態を並べます。`popup`は受信専用の警告表示、`receive`はメイン画面の単一VFO・デュアルVFO・外部16×16名・外部8×8名・ASCIIフォールバックを確認します。個別のカテゴリは次のように指定できます。番号は0始まりです。

```powershell
python tools/lcd_emulator.py --screen category --category 0 --out tmp/lcd-category.png
```

実機やログから1024 bytesのST7565フレームバッファを取得できる場合は、そのまま画像化できます。

```powershell
python tools/lcd_emulator.py --screen raw --raw frame.bin --out tmp/lcd-raw.png
```

## 再現範囲と限界

- ページあたり128 bytes、8 pages、各byteの下位bitが上側のドットという、現在のフレームバッファ配置を再現します。
- `App/font.c`から内蔵ASCIIフォントを読み取り、外部16×16フォントを使うチャンネル名表示では`docs/fonts/japanese_font.bin`も読み取ります。
- カテゴリの線画アイコンと、カテゴリ名・件数・位置の配置は`App/ui/menu.c`の現在の描画位置に合わせています。
- 受信画面は、チャンネル番号、RX表示、名前、周波数、補助情報、Sメーター、単一／デュアルVFOの配置を静的に確認します。現行ファームウェアの描画順に合わせ、単一VFOの16×16名・大字形周波数、ASCII名の大字形フォールバック、8×8名の小字形周波数、デュアルVFOの小型名称・小字形周波数、6×8の補助情報とRSSI専用ページを再現します。画像が乱れた場合は、ファームウェアとエミュレーターのページ所有権が一致しているか確認してください。
- 受信画面の検証用名称は、外部16×16／8×8経路を`東京`、ASCIIフォールバックを`TOKYO`としています。FM音声プロファイルの代表表示は`FLAT`です。これは実機のチャンネル名や固定UIを意味しません。
- F4HWNの微小な受信／音声状態表示は物理座標`y=1/33`へ、チャンネル番号はその次のLCDページへ描きます。ページ番号をそのまま状態表示のY座標として使わないようにします。単一VFOの大字形周波数は呼び出し側の`line+2`から2ページを使い、8×8名の単一VFOでは名前と大字形周波数を保ったまま表示します。補助情報は6×8の一行へまとめ、単一VFOはページ4、デュアルVFOはページ2／6、RSSIは単一VFOがページ5、デュアルVFOがページ3を所有します。デュアルVFOの名前と周波数は、設定にかかわらず小字形で描かれます。
- カテゴリ件数には代表値を使用しています。ロック状態やビルド機能によって実機の表示件数は変わります。
- Cの条件分岐、実行時状態、LCDコントローラーの電気的な挙動、実機での視認性までは検証しません。画像が正常でも、実機表示やフォント転送の成功を保証するものではありません。
