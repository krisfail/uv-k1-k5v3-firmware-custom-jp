# チャンネルリスト形式

WRX-JP専用host toolが読み書きする，K1／K5 V3用チャンネルリストの仕様を定めます。ファイルはUTF-8のTSV（タブ区切り）で，通常チャンネル1024件を1行ずつ保持します。

## 目的と範囲

この形式は，通常チャンネルの編集・バックアップ・復元に使います。firmware本体，calibration，外部Flashの任意領域は含みません。

書込み時には受信専用の不変条件を適用します。

- 送信周波数領域はゼロ化する
- 送信トーンは保持しない
- calibration領域は書き込まない
- 周波数，mode，tone，step，scan list，表示名を検査してから書き込む

## ファイル形式

```text
# WRX-JP channel list v2
channel\tfrequency_hz\tmode\ttone_mode\ttone\tdtcs\tdtcs_polarity\ttuning_step_khz\tscan_lists\tname\tascii_name
```

先頭の`#`で始まる行はコメントとして扱います。データ行は必ず1024行で，`channel`は1から1024まで連番でなければなりません。列の順序と列名は固定です。

## 列

| 列 | 内容 |
| --- | --- |
| `channel` | チャンネル番号。1–1024。 |
| `frequency_hz` | 受信周波数（Hz）。空欄は未登録。10 Hz単位で指定する。 |
| `mode` | `FM`，`NFM`，`AM`，`NAM`，`USB`のいずれか。 |
| `tone_mode` | 空欄，`Tone`，`TSQL`，`DTCS`のいずれか。 |
| `tone` | CTCSS周波数（Hz）。CTCSS使用時だけ指定する。 |
| `dtcs` | DCSコード。DTCS使用時だけ指定する。 |
| `dtcs_polarity` | `N`または`R`。 |
| `tuning_step_khz` | 対応するチューニングステップ（kHz）。 |
| `scan_lists` | スキャンリストのビットマスク。0–255。 |
| `name` | 通常表示名。日本語またはASCIIを指定する。UTF-8で最大31 byte。ASCIIだけの場合は最大10 byte。 |
| `ascii_name` | 日本語名をcompact ASCII表示へ切り替えるときの別名。ASCII printable文字で最大10 byte。 |

`frequency_hz`が空欄の行は未登録チャンネルです。未登録行の他の値と名前は書込み時に消去されます。

## 表示名と保存領域

`name`の内容により，次の領域へ保存します。

| `name` | 通常表示用の保存先 | `ascii_name`の保存先 |
| --- | --- | --- |
| 日本語を含む | 外部Flashの日本語名前テーブル（1件32 byte） | 通常チャンネル領域のASCII slot（1件16 byte、実使用10 byte） |
| ASCIIだけ | 通常チャンネル領域のASCII slot | `name`と同じ内容を通常表示名として扱う |
| 空欄 | 両方を消去 | 両方を消去 |

日本語名とASCII別名を同時に指定できるのはv2の追加仕様です。firmwareの通常表示では日本語名を優先し，compact ASCII表示ではASCII別名を使います。ASCII別名が空の場合はチャンネル番号表示へフォールバックします。

ASCII別名は自動的にローマ字化しません。日本語名に対応する別名が必要な場合は，利用者が`ascii_name`へ明示的に記載してください。

## v1との互換性

旧形式v1の列は次の10列です。

```text
channel\tfrequency_hz\tmode\ttone_mode\ttone\tdtcs\tdtcs_polarity\ttuning_step_khz\tscan_lists\tname
```

hostはv1を読み込めます。v1のASCII名はその行の通常表示名として扱い，日本語名にはASCII別名を自動付与しません。v1を読み込んで保存すると，v2として出力されます。

CHIRP互換アダプタはCHIRPの単一`name`フィールドに合わせるため，v2の`ascii_name`を編集する機能は持ちません。日本語名とASCII別名を併用する場合は専用host toolを使用してください。

## 検証

専用host toolは，読込時と書込時に次を検査します。

- 列名，列順，データ行数，チャンネル番号の連番
- mode，tone，DCS，stepの対応値
- 日本語名のUTF-8 byte数，manifest収録文字，表示幅
- ASCII別名の文字種と最大10 byte
- RX-only書込み範囲と外部Flashのallowlist

検査を通過したデータも，書込み後のreadback比較が完了するまで適用済みとは扱いません。
