# DondjiからK1系日本語基盤への移行計画

## 目的と結論

本書は，Dondjiで使われている外部SPI Flash上のフォントデータ構成を参考にし，PY32F071搭載のUV-K1／UV-K5 V3系で日本語チャンネル名を表示するための計画を定める．

Dondjiから参考にするのは，外部Flashへ生成済みbitmapフォントを置き，Unicode索引で参照するという構成だけである．手元のDondji BDF全体には一部の日本語文字も含まれるが，生成済みDondjiフォントは中国語中心であり，JIS第1水準の日本語フォントとして流用しない．日本語フォントは別途選定する．

最初の実装対象は，CHIRP／Webから書き込んだ1024件のUTF-8チャンネル名を外部フォントで表示する段階Aとする．段階Bの日本語UIは段階Aの安定後に再評価し，段階Cの無線機上の日本語入力は実装しない．

本書に基づく段階Aの実装は開始済みである．本書は実装状態と残る実機検証範囲を記録する．

## 対象範囲と固定方針

- 対象：PY32F071を搭載するUV-K1／UV-K5 V3共通ファームウェア
- 正規ビルド入口：`JpRxOnly`
- 利用目的：日本国内向けの受信専用運用
- 対象チャンネル：既存の1024チャンネル
- 対象文字：JIS X 0208第1水準相当の漢字，ひらがな，カタカナ，必要な日本語記号，ASCII
- フォント：bitmap-nativeを優先し，主フォントは1つにする
- フォントのgeometry：12×12を優先するが，妥当な候補が16×16などの場合はnative geometryを使う。自動縮小はしない
- ライセンス：firmwareへのembeddingとbinary再配布を確認できるもの。GPL系はembedding exceptionとNOTICE等の条件を満たす場合に限り採用する
- フォント候補が対象文字・品質・ライセンス条件を満たさない場合は，複数フォントを混在させず停止する
- 段階C（無線機上の日本語入力）：実装しない
- scroll：段階Aでは実装しない。表示欄を超える名前はhost側で拒否し，将来課題とする

送信経路，送信メニュー，PTTの送信動作は本計画で再導入しない．日本語表示とチャンネル名保存は，受信専用境界から独立した機能として扱う．

## 現時点で確認できていること

| 項目 | 確認結果 | 計画上の扱い |
|---|---|---|
| K1のチャンネル数 | `MR_CHANNELS_MAX`とCHIRP profileは1024 | 1024件を対象とする |
| 既存チャンネル名 | 外部Flashの`0x4000`–`0x8000`に1024件×16 byte。実装上の有効長は10 byteで，現状はASCII | 既存slotを壊さず，日本語名は別の拡張テーブルへ置く |
| K1外部Flash | `PY25Q16`ドライバ，4 KiB sector，256 byte page，3 byte addressを使用 | 実装部品の容量とJEDEC IDは未確認 |
| フォントデータ用空き領域 | 現行ソースから確認済みの空き領域はない | Dondjiの`0x024000`をK1の予約領域として使わない |
| Dondjiのフォント | 参照資料には12×12固定字形，6766字，約205 KBという記載がある | K1側で再利用できる実体・配置としては扱わず，容量の目安に留める |
| DondjiのBDF | BDF全体には一部日本語文字があるが，生成済みフォントは中国語中心 | 日本語フォントとしては流用しない |
| K1の既存日本語字形 | 内部1-byte字形が存在するが，JIS第1水準全体ではない | ASCIIと既存表示の互換用に残す |
| 採用フォント | Izumi Gothic-Medium 16dot。JIS X 0213:2004 Plane 1，16×16 BDF，BDF記載はPublic Domain | 段階Aの単一bitmap-nativeフォントとして採用 |
| UTF-8描画 | 外部フォント向けのUTF-8 decoder，Unicode lookup，16×16描画を実装 | 段階Aの表示経路で使用 |

Dondjiでこの規模の中国語フォントデータが収録されているため，容量上は実現可能と推定する。ただし，これはK1の外部Flash容量・既存mapを確認する前提を省略する根拠にはしない．

## 段階A：外部フォントによる1024件のチャンネル名表示

CHIRPまたはWebから書き込んだUTF-8チャンネル名を，K1／K5 V3のLCDへ表示する．日本語名は既存の16 byte ASCII slotとは別に保存する．

### チャンネル名の契約

- host側の入力encodingはUTF-8とする
- 1024件を連続したチャンネル番号で扱う
- CHIRP／Webのチャンネル名契約はversion付きで管理する
- 1件のUTF-8 payloadは最大31 byteとする
- byte長と表示pixel幅を別に検査する
- 末尾でUTF-8文字を分割しない
- フォントに収録されていない文字，不正UTF-8，長さ超過，表示欄超過はhost側で拒否する
- firmware側は拡張テーブルを固定形式で読む。内部的には必要に応じて独自code setへ変換してよいが，既存1-byteコードの意味は変更しない

### 保存方法

拡張チャンネル名テーブルは，1024件×32 byteの固定領域とする。sector境界を含めて約40 KiBを予約する．

このデータは重要設定とは扱わない．A/B二重化，journal，generation管理，per-record CRCは導入しない．host PCが固定領域へ書き込み，readback比較で成功を確認する。失敗時はhost側から再実行する．

既存のASCII名slotは保持する。新firmwareは有効な日本語拡張名を優先し，拡張名がない場合は既存ASCII名を読む。旧firmwareは従来のASCII名だけを読む前提とし，日本語名の互換表示は保証しない．

### 外部フォント

フォントデータは生成済みの単一bitmap binaryを固定領域へ置く。フォントデータの形式はfirmwareと生成器の組み合わせで固定し，実行時の一般的なversion交渉やfont ID管理は導入しない．host PCは書き込み後にreadback確認を行い，失敗時は再実行する．

フォントデータには固定geometryとUnicode索引を持たせる。索引はUnicode順のcompactな表とし，対象文字のlookupに使う。フォント本体のサイズは，選定したgeometryと対象集合からhost側で計算する．

段階AではIzumi 16の16×16 native geometryを使う。対象はJIS X 0208第1水準相当の漢字，かな，記号を含む3489字で，フォントデータは約123 KiB（索引13956 byte，bitmap 111648 byte）である。ASCIIは外部フォントデータへ重複収録せず，既存のgFontBigを互換フォールバックとして使う。生成入力，SHA-256，形式，コードポイント集合はtools/japanese_font_manifest.jsonとdocs/fonts/README.ja.mdに記録する。

### UTF-8と描画

外部入力はUTF-8を基本とする。firmwareのdecoderは対象文字に必要なASCII 1 byteとBMP内の3 byte UTF-8を中心に実装し，4 byte文字や一般Unicode全体は対象外とする．内部処理で独自code setへ変換する場合も，host側のUTF-8契約と文字対応を壊さない．

表示，幅計算，中央揃え，clip，反転表示では同じdecoder／lookupを使う。`strlen()`のbyte数を表示文字数として扱わない．段階Aではscrollを実装せず，表示欄に収まらない名前をhost側で拒否する．

## 段階B：日本語UI

段階Aが安定した後に再評価する。固定メニュー文言，ヘルプ，警告，起動画面，受信状態表示を対象候補とするが，本書更新時点では実装しない．

既存の`App/japanese_font.c`による内部1-byte字形は，段階Bでも互換用のフォールバックとして保持する．日本語UIの追加によって，TX拒否，PTTモニター，受信状態，calibration，Flash書き込み，復旧操作などの安全表示の意味を変更しない．

## 実装状況

段階Aのコード実装は次の状態である。

- Izumi 16から対象3489字の外部bitmapフォント，Unicode索引，manifestを生成済み
- フォントデータを外部Flash 0x020000から配置し，1024件×32 byteの名前テーブルを0x040000から配置
- 既存16 byte ASCII名slotと既存UART読み書きは維持
- K1／K5 V3用に32 bit物理アドレスの外部Flash read/writeコマンドを追加
- CHIRPはUTF-8名を検査し，書き込み後のreadback比較と最大3回の再試行を行う
- 表示欄を超える名前，フォントに収録されていない文字，不正UTF-8はhost側で拒否
- スクロールと無線機上の日本語入力は未実装

外部Flashの実容量，JEDEC ID，固定領域の実機衝突確認，LCD視認性，書き込み・再起動後の実機動作は未検証である。A/B二重化，journal，generation，per-record CRCは実装していない。

## 作業パッケージ

| WP | 内容 | 完了条件 |
|---|---|---|
| WP0 | 日本語bitmap fontの候補，対象文字，ライセンスの確認 | 単一フォントの採用可否が決まる。候補がなければ停止する |
| WP1 | 採用フォントからbitmap binaryとUnicode索引を生成 | 同じ入力からbinaryとatlasを再生成できる |
| WP2 | K1外部Flashの容量，JEDEC ID，既存map，固定領域を確認 | フォントデータ領域と1024件名テーブル領域が既存領域と衝突しない |
| WP3 | UTF-8／内部code setの変換，Unicode lookup，native geometry描画 | host framebufferで対象文字とASCII混在を確認できる |
| WP4 | CHIRP／Webの1024件チャンネル名契約とhost書き込み | 31 byte境界，文字境界，未登録文字，表示幅，readbackを検証できる |
| WP5 | 実機検証と公開文書 | LCD視認性，Flash書き込み，再起動，受信専用境界への影響を記録する |
| WP6 | 日本語UI（段階B）の再評価 | 段階Aの結果を踏まえて別途判断する |

## 検証計画

### host側

- JIS X 0208第1水準相当，かな，記号の対象集合を明示する
- 採用フォントのglyph存在，重複，空字形，license条件を確認する
- BDFを使う場合はBBXのwidth／height／x／yとbaselineを確認する
- native geometryのbitmap長，索引，対象文字数，総payloadを計算する
- UTF-8の正常系・異常系と，必要なら内部code set変換を検証する
- 1024件×31 byte境界，途中byte切断，未登録文字を検証する
- 表示pixel幅とLCD欄超過を検証する
- 外部Flashへの書き込み後にreadback比較を行う

### 実機側

hostテストとbuild成功は，LCDの視認性，SPI Flashの実配線，起動時間，描画速度を保証しない．実機では少なくとも次を確認する．

- 外部Flashの実容量とJEDEC ID
- フォントデータと1024件名テーブルの固定領域が既存設定・calibration・logo等と重ならないこと
- host書き込み後の再起動・再読出し
- かな，JIS第1水準漢字，記号，ASCII混在の視認性
- 採用した16×16 native geometryでのbaselineと表示速度
- 受信，scan，priority／dual watch中の表示
- PTTモニター，TX拒否，受信専用動作に影響がないこと

## 採用しない方法

- Dondjiの`ENABLE_CHINESE`を`ENABLE_JAPANESE`へ機械的に置換する
- `IsChineseChar()`の範囲だけを拡張する
- DondjiのBDFを日本語フォントとして扱う
- BDFの行番号やglyph出現順に依存する
- 既存の16 byte ASCII slotへUTF-8を無理に押し込む
- 1024件の名前テーブルにA/B，journal，generation，per-record CRCを導入する
- 無線機上の日本語入力を実装する
- 旧UV-K5（DP32G030・内蔵EEPROM）のコードやmemory mapをK1へ流用する
- hostテストやbuild成功を実機LCD・Flash・受信動作の保証として記載する

## 実装Go／No-Go判断

段階Aのホスト／ファームウェア実装へ進む判断は，次の条件を満たしたため確定した．物理Flash容量，領域衝突，LCD視認性は実機側の別のNo-Go確認として残す．

- 単一のbitmap-native日本語フォントが見つかる
- JIS X 0208第1水準相当，かな，記号，ASCIIの対象集合を満たす
- embeddingとbinary再配布のlicense条件が確定する
- 採用geometryを16×16 nativeとして固定できる
- 1024件×32 byteの名前テーブルとフォントデータの予約候補を定義できる
- host PCのwrite／readback検証が成立する
- `JpRxOnly`の受信専用境界へ影響しない

単一フォントが見つからない場合は，複数フォントを混在させず停止する．

残る段階Aの作業は，**実機での外部Flash容量・固定領域・LCD表示・CHIRP書き込みの確認**である。段階Bは段階Aの結果を見て別途判断し，段階Cは実装しない。
