# Phase 4（GA4）現状棚卸しレポート

**目的**: 改善と無効トラ検知のため、GA4 に最低限入れたいイベント群の「現状カバレッジ」を事実で確定し、差し込みポイントと不足分をバックログ化する。**本ターンは分析のみ（実装禁止）。**  
**証跡**: file:line および grep 結果。本番 GA_MEASUREMENT_ID の有無は未確認のため、コード上の「送信有無」のみを事実とする。

---

## A. GA4 ロード設定（事実）

| 項目 | 根拠（file:line） | 内容 |
|------|-------------------|------|
| GA4 読み込み条件 | templates/includes/head_meta.html:2 | `{% if GA_MEASUREMENT_ID %}` が真のときのみ、3–13 行目の gtag ブロックがレンダーされる。 |
| script URL | head_meta.html:4 | `<script async src="https://www.googletagmanager.com/gtag/js?id={{ GA_MEASUREMENT_ID }}"></script>` |
| dataLayer / gtag 定義 | head_meta.html:6–8 | `window.dataLayer = window.dataLayer || [];`、`function gtag(){dataLayer.push(arguments);}`、`gtag('js', new Date());` |
| config（page_view の元） | head_meta.html:10–12 | `gtag('config', '{{ GA_MEASUREMENT_ID }}', { anonymize_ip: true });`。GA が自動送信する page_view はこの config に紐づく。 |
| GA_MEASUREMENT_ID 注入 | app.py:308–348, 348–368 | `inject_env_vars()`（context_processor）の return 辞書に `'GA_MEASUREMENT_ID': os.getenv('GA_MEASUREMENT_ID', '')`（342行目）。例外時は 364 行目で `''`。 |
| ID 未設定時の挙動 | head_meta.html:2 | `GA_MEASUREMENT_ID` が空なら 3–13 行は出力されない。`window.gtag` は未定義。 |

**結論（事実）**: GA4 は「GA_MEASUREMENT_ID が設定されているときのみ」head に gtag.js と config が出力される。ID 未設定時は gtag も dataLayer も存在しない。既存のイベント送信コードはすべて `if (typeof window !== 'undefined' && window.gtag)` でガードしているため、ID 未設定時は送信されず、ReferenceError も発生しない。

---

## B. イベント送信の全件一覧（事実）

**検索**: `rg -n "gtag\(|dataLayer|GA_MEASUREMENT_ID|G-" templates static/js app.py` 相当の結果を整理。

| event_name | parameters | 発火箇所（file:line） | 対象ページ |
|------------|------------|------------------------|------------|
| （config による page_view） | — | head_meta.html:10 | GA_MEASUREMENT_ID が設定されている全ページ（head_meta を include するすべて） |
| tool_run_start | tool_id, file_count | static/js/tool-runner.js:112–117 | tool-runner.js を読み込むツールページ（下記） |
| tool_download | tool_id, file_type, download_type: 'single' | static/js/tool-runner.js:420–427 | 同上（単体ダウンロード時） |
| tool_download | tool_id, file_type: 'zip', download_type: 'zip', file_count | static/js/tool-runner.js:455–461 | 同上（ZIP 一括ダウンロード時） |
| autofill_start | なし | templates/autofill.html:1073–1075 | /autofill（フォーム送信開始時） |
| autofill_error | error_type | templates/autofill.html:1106–1108（result.error 時）, 1117–1120（catch 時） | /autofill |
| autofill_success | なし | templates/autofill.html:1154–1156 | /autofill（処理成功時） |

**tool-runner.js を読み込むテンプレート（事実）**  
- templates/tools/pdf.html:531  
- templates/tools/image-batch.html:517  
- templates/tools/image-cleanup.html:525  

**tool-runner.js を読み込まないツール**  
- templates/tools/csv.html: script に tool-runner.js なし（grep で 0 件）。  
- templates/tools/seo.html: script に tool-runner.js なし（seo-*.js 等のみ）。

---

## C. 要件イベントへのマッピング表（事実）

| 要件イベント | 対応状況 | 根拠（事実） |
|--------------|----------|----------------|
| page_view | 対応済み | head_meta.html:10 の gtag('config', ...) により、GA が自動送信。ID 設定時のみ。 |
| tool_open | 未対応 | ツールページ到達時に発火する gtag 呼び出しはコード上に存在しない。 |
| tool_action_start | 名称違いで一部対応 | tool_run_start（tool-runner.js:114）＝実行開始。autofill_start（autofill.html:1074）＝AutoFill 処理開始。**/tools/csv は独自実装のため tool_run_start なし。** |
| tool_action_success | 名称違いで一部対応 | autofill_success（autofill.html:1155）のみ。tool-runner 使用ツール（pdf, image-batch, image-cleanup）では成功時の gtag 呼び出しなし（onComplete にイベント送信なし）。 |
| tool_action_fail | 名称違いで一部対応 | autofill_error（autofill.html:1108, 1118）のみ。tool-runner では onError 時に gtag 呼び出しなし。 |
| download_click | 名称違いで対応済み（ツール一部） | tool_download（tool-runner.js:423, 457）。pdf / image-batch / image-cleanup では発火。**/tools/csv は FileUtils.downloadBlob を直接呼んでおり gtag なし。** /tools/seo は tool-runner 未使用のため要別確認。 |
| contact_open | 未対応 | /contact 到達時の gtag 呼び出しなし（contact.html に gtag の記述なし）。 |
| contact_submit | 未対応 | お問い合わせは Google Form 埋め込み（iframe）のため、同一オリジンから送信完了を検知するコードは存在しない。 |

---

## D. 欠けている点と差し込み候補（候補。根拠は file:line）

### D1. tool_open

- **欠けている点**: ツールページ（/tools/pdf, /tools/csv, /tools/seo 等）に到達したときのイベントがない。
- **差し込み候補**:  
  - **共通化できる場合**: 各ツールテンプレの body 末尾や、ツール用の共通 include がもしあればその中に「1 回だけ gtag('event', 'tool_open', { tool_id: 'pdf' }) 等」を送るスクリプトを追加。  
  - **現状**: 共通 include はないため、**各ファイルごと**。  
  - **候補箇所**:  
    - templates/tools/pdf.html: 最終 script ブロックまたは body 末尾（531 行付近の script の前）。  
    - templates/tools/image-batch.html: 同様（517 行付近の前）。  
    - templates/tools/image-cleanup.html: 同様（525 行付近の前）。  
    - templates/tools/csv.html: インライン script の先頭（例: 112 行付近の IIFE 内）。  
    - templates/tools/seo.html: 同様に script ブロック内。  
  - tool_id は URL パスから取得するか、テンプレで変数として渡す。

### D2. tool_action_success / tool_action_fail（tool-runner 使用ツール）

- **欠けている点**: tool-runner.js の run() / runBatch() の onComplete（337–340 行付近）と catch 内 onError（137, 337 行付近）に gtag 呼び出しがない。
- **差し込み候補**:  
  - static/js/tool-runner.js:  
    - run() の try 内で処理成功後に `gtag('event', 'tool_action_success', { tool_id, file_count })` を送る箇所を追加する場合、**140 行付近の onComplete の直前**。  
    - run() の catch（137 行付近）および runBatch() の catch（337 行付近）で `gtag('event', 'tool_action_fail', { tool_id, error_message })` を送る。  
  - いずれも `window.gtag` の存在チェックを維持する。

### D3. download_click（/tools/csv）

- **欠けている点**: Phase 2 で /tools/csv は ToolRunner 未使用。FileUtils.downloadBlob を直接呼んでいるため、tool_download に相当するイベントが送られていない。
- **差し込み候補**:  
  - templates/tools/csv.html 内の、FileUtils.downloadBlob を呼んでいる箇所の直前に gtag を 1 行追加。  
  - 該当: 単体ダウンロード（1 件）は **420 行** `FileUtils.downloadBlob(outputs[0].blob, ...)` の前。ZIP は **424 行** `FileUtils.downloadBlob(zipBlob, ...)` の前。  
  - 共通化はしない前提なら、csv.html のこの 2 箇所のみ。イベント名は download_click または既存に合わせて tool_download のどちらかに統一する設計が必要。

### D4. contact_open

- **欠けている点**: /contact を表示したときのイベントがない。
- **差し込み候補**:  
  - templates/contact.html: body 末尾または既存の script ブロック内で、ページロード時に 1 回 `gtag('event', 'contact_open')` を送る。  
  - 該当: contact.html に専用の script ブロックが少ないため、**新規で script を追加する位置**（例: footer include の直前）に 1 ブロック追加する形が最小差分。

### D5. contact_submit

- **難所**: お問い合わせは Google Form の iframe 埋め込み（contact.html 内で iframe の src を参照）。同一オリジンではないため、フォーム送信完了を自ページの JS で検知する標準的な方法はない。
- **代替案（推測として分離）**:  
  - Google Form の「送信後のリダイレクト URL」を自サイトの「サンキューページ」にし、そのサンキューページで contact_submit を 1 回送る。  
  - または Form の送信完了メッセージを iframe 内で表示する運用のまま、送信完了を検知しない（contact_submit は送らない）。  
  - 実装は行わず、要件側で「送信完了を計測するか／諦めるか」を決める必要あり。

---

## E. 次ターンの実装バックログ TSV（最重要）

**ファイル**: `docs/phase4_ga4_backlog.tsv` に同じ内容を格納（コピペ用）。

| 優先度 | 要件イベント | 現状 | 追加方針（候補） | 変更箇所候補(file:line) | 受け入れ基準 | 証跡 |
|--------|--------------|------|------------------|--------------------------|--------------|------|
| P1 | page_view | config で自動送信（ID 設定時） | 変更不要 | — | ID 設定時は全ページで page_view が送られる | GA デバッグまたはネットワークで gtag/js と config を確認 |
| P1 | tool_open | なし | 各ツールページで 1 回発火する script を追加 | templates/tools/pdf.html（body 末尾付近）, image-batch.html, image-cleanup.html, csv.html（112 行付近 IIFE 内）, seo.html | ツール URL 表示時に tool_open が 1 回送られる | 同上 |
| P1 | tool_action_start | tool_run_start / autofill_start あり。csv はなし | csv のみ「実行」クリック時に 1 回送る | templates/tools/csv.html:353 runBtn.addEventListener 内、処理開始直後（357 行付近） | csv でも変換開始イベントが送られる | コンソールまたは GA デバッグでイベント名確認 |
| P2 | tool_action_success | autofill_success のみ。tool-runner はなし | tool-runner の onComplete で送る | static/js/tool-runner.js（340 行付近 onComplete の直前） | pdf/image-batch/image-cleanup で成功時に 1 回送られる | 同上 |
| P2 | tool_action_fail | autofill_error のみ。tool-runner はなし | tool-runner の catch で送る | static/js/tool-runner.js:137, 337（onError 呼び出しの前後） | 同上ツールで失敗時に 1 回送られる | 同上 |
| P2 | download_click | tool_download あり（pdf/image-batch/image-cleanup）。csv はなし | csv の FileUtils.downloadBlob 直前に gtag 追加 | templates/tools/csv.html:420 の前、424 の前 | csv でダウンロード時に 1 回送られる | 同上 |
| P2 | contact_open | なし | /contact 表示時に 1 回送る | templates/contact.html（footer 直前などに script 追加） | /contact 表示で contact_open が 1 回送られる | 同上 |
| P2 | contact_submit | なし（Form iframe） | 要検討（サンキューページ or 未計測） | — | 要件で方針決定後に実装 | 推測セクション参照 |

---

## ページ別イベント発火ポイント（事実）

| ページ | テンプレ | 読み込む JS（ツール関連） | 発火イベント（事実） |
|--------|----------|----------------------------|----------------------|
| / | landing.html | head_meta のみ（gtag は ID 次第） | page_view（config のみ） |
| /autofill | autofill.html | インライン + 各種 | page_view、autofill_start、autofill_error、autofill_success |
| /tools/pdf | tools/pdf.html | tool-runner.js 等 | page_view、tool_run_start、tool_download（単体/zip） |
| /tools/image-batch | tools/image-batch.html | tool-runner.js 等 | 同上 |
| /tools/image-cleanup | tools/image-cleanup.html | tool-runner.js 等 | 同上 |
| /tools/csv | tools/csv.html | file-validation, file-utils, zip-utils, csv-ops 等。tool-runner なし | page_view のみ（カスタムイベントなし） |
| /tools/seo | tools/seo.html | seo-*.js のみ。tool-runner なし | page_view のみ（カスタムイベントなし） |
| /contact | contact.html | head_meta のみ | page_view のみ |

**依存関係（簡易）**  
`app.py (inject_env_vars → GA_MEASUREMENT_ID)` → 全テンプレで `include head_meta` → `GA_MEASUREMENT_ID` ありなら gtag/config 出力 → page_view 送信。  
イベント送信は (1) tool-runner.js（pdf, image-batch, image-cleanup）、(2) autofill.html インライン、(3) その他ツール（csv, seo）は現状なし。

---

## 推測・注意（事実と分離）

- **本番で GA_MEASUREMENT_ID が設定されているか**: 未確認。コード上は未設定なら gtag が存在せず、イベントは送信されない。
- **contact_submit**: Google Form iframe のため、同一オリジンから送信完了を検知する実装はできない。サンキューページへのリダイレクトや、計測しない選択は「推測・要件」の範囲。
- **/tools/seo**: tool-runner 未使用のため、ツール内での「実行開始・成功・失敗・ダウンロード」がどう定義されるか（どの JS のどの処理に紐づけるか）は、seo 用 JS の処理フローを確認したうえで差し込み箇所を決める必要あり。
- **実測証跡**: 本番 ID が不明なため、ローカルで GA_MEASUREMENT_ID をダミー（例: G-XXXXXXXXXX）にしても、GA には送信されないだけで「gtag が呼ばれているか」は DevTools → Console（gtag 呼び出し前で break またはログ追加）や Network で gtag/js および collect リクエストの有無を確認すればよい。Playwright で console/network を収集するスクリプトは、本レポートでは「案」として提示のみ（作成はしない）。  
  - **手順案**: (1) /tools/csv を開く、(2) コンソールで `typeof gtag` を実行（ID 未設定なら `'undefined'`）、(3) ファイル選択→実行し、ネットワークで `google-analytics.com/g/collect` 等が呼ばれているか確認。
- **Playwright で証跡を取る場合のスクリプト案（作成はしない）**: (1) `page.goto('/tools/csv')` 等で対象ページを開く。(2) `page.on('request', req => ...)` で URL に `google-analytics.com` または `googletagmanager.com` を含むリクエストを記録し、collect の有無を確認。(3) `page.on('console', msg => ...)` で `console.log` を記録する代わりに、対象ボタンクリック前に `page.evaluate(() => window.__ga4_events = [])` 等で配列を用意し、各 gtag 呼び出しをラップして `__ga4_events.push(...)` する改修を一時的に入れて e2e で回す方法もある（実装は次ターン）。本分析では「どこを確認すればよいか」の案の提示までとする。

---

**以上、Phase 4 GA4 現状棚卸しの記録とする。**
