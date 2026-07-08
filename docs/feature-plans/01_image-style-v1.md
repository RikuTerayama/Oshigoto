# 機能仕様: 画像スタイル（枠・余白・角丸・比率）v1

## 目的（業務課題）

- 商品画像やSNS用画像に**余白・枠・角丸**を付けて、一括で体裁を揃えたい
- 既存の「縦横比統一」と組み合わせて、投稿用・一覧用の見た目を統一したい
- ブラウザ内で完結し、ファイルをサーバーに送らない方針を維持する

## 対象ツール

- **image-cleanup**（画像ユーティリティ）のみ。新ツールは作らない。

## 現状仕様の確定（Step A 結果）

### image-cleanup の maxFiles / maxFileSize（確定済み）

| 項目 | 値 | 根拠 |
|------|-----|------|
| maxFiles | 背景除去OFF: 50 / ON: 20 | `templates/tools/image-cleanup.html` 519行目 `const maxFiles = bgRemovalEnabled ? 20 : 50` |
| maxFileSize | 20 * 1024 * 1024（20MB） | 同 524行目 `maxFileSize: 20 * 1024 * 1024` |
| maxTotalSize | 背景除去OFF: 200MB / ON: 100MB | 同 521行目 `maxTotalSize` |
| allowedExtensions / MimeTypes | .png, .jpg, .jpeg, .webp | 同 526–528行目 |

minutes.html / seo.html は本v1の対象外。validateFiles の呼び出しは image-batch・pdf・image-cleanup にのみ存在し、minutes・seo は別パターンのため未確認のままとする。

---

## 追加するUI項目（デフォルト値含む）

| 項目 | 型 | デフォルト | 範囲・備考 |
|------|-----|------------|------------|
| 余白（px） | number | 0 | 0〜200。画像周りに均等パディングを追加。 |
| 枠（border）幅（px） | number | 0 | 0〜50。0のとき枠なし。 |
| 枠の色 | 選択 + 任意色 | 黒 | 白 / 黒 / 任意（カラーピッカー）。 |
| 角丸（px） | number | 0 | 0〜500。0のとき角丸なし。 |
| 背景色（余白・角丸用） | 選択 + 任意色 | 白 | 白 / 透明 / 任意。透明は角丸時の角部分；PNG出力で有効。 |

- 適用順: **余白 → 角丸 → 枠**（パイプライン内でこの順で実行）。
- 比率整形は既存の「縦横比統一」と統合済み。本機能はその**後段**で余白・角丸・枠を付与する。

---

## 出力

- 既存の zip/形式変換の流れと整合。出力形式は **PNG / JPEG / WebP** のまま。
- 複数ファイル時は従来どおり ZIP または個別ダウンロード。変更なし。

---

## 制約

- **ブラウザ処理の限界**: Canvas のピクセル上限（既存 MAX_PIXELS: 80,000,000）に準拠。余白・枠追加でキャンバスが拡大するため、元画像が極端に大きいとメモリ負荷が増す。
- **推奨**: 通常モード 50ファイル・1ファイル20MB、背景除去時 20ファイル（既存表記のまま）。
- 角丸＋透明背景で JPEG 出力する場合、角部分は白背景で出力（JPEGは透過非対応のため既存仕様どおり）。

---

## データ取扱い（アップロードなし・保存なし）

- **アップロード・保存**: 行わない。根拠は以下。
  - `app.py`: `/tools/*` は GET のみ。ファイル受信は Jobcan 用 `/upload` のみ（1250行付近の `request.files` / `file.save`）。  
  - 本機能は `static/js/image-style.js` および `image-cleanup.js` のパイプライン拡張のみで、新たにサーバーへファイルを送る処理は追加しない。

---

## 受け入れ条件（最低ライン）

1. **枠・余白・角丸の ON/OFF（値0含む）で動作が切り替わる**  
   - 0 のときは何も付与せず従来と同じ出力になること。
2. **既存の出力形式（PNG/JPEG/WebP）と共存できる**  
   - 既存の品質・ファイル名テンプレート・ZIP 出力が壊れないこと。
3. **処理はブラウザ内で完結し、サーバーにファイルを送らない**  
   - 新規の fetch/FormData 送信を追加しないこと。
4. **ガイドが更新され、FAQ と JSON-LD（FAQPage）が整合する**  
   - `templates/guide/image-cleanup.html` の faq_list を 8 件維持し、必要に応じて差し替え。FAQPage の mainEntity が正しく出力されること。

---

## 実装方針（参照）

- **新規JS**: `static/js/image-style.js`  
  - `applyPadding(canvas, paddingPx, bgColor)`  
  - `applyRoundedCorners(canvas, radiusPx, bgColor)`  
  - `applyBorder(canvas, borderWidthPx, borderColor)`  
- **パイプライン**: `ImageCleanup.runCleanupPipeline` 内、縦横比統一の**後**・書き出しの**前**に 1 段として挿入。
- **UI**: `templates/tools/image-cleanup.html` に「枠・余白・角丸」用のオプション群を追加。値は JS で読み取り、既存の `runCleanup()` → `processor` に渡す。
