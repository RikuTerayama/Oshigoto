# AutoFill 503 表示の「待機」化と Playwright 軽量化 — 調査レポート

**日付**: 2026-02-10  
**前提**: Render Starter 512MB/0.5CPU、MAX_ACTIVE_SESSIONS=1。2人目以降は /upload が 503 で「失敗」に見えるのを「待機」表示にしたい。

---

## A. /upload が 503 を返す条件とレスポンス形式

### 条件（根拠: コード）

| 項目 | 根拠 |
|------|------|
| **判定** | `running_count >= MAX_ACTIVE_SESSIONS` のとき 503 を返す。 |
| **箇所** | **app.py 1289–1297 行**。`count_running_jobs()` で running ジョブ数を取得（1289 行）、`if running_count >= MAX_ACTIVE_SESSIONS:`（1290 行）で `return jsonify({...}), 503`。 |
| **同一ロジック** | `check_resource_limits()`（434–438 行）も `running_count >= MAX_ACTIVE_SESSIONS` で `RuntimeError` を投げるが、/upload はその**前**に 1289–1297 で 503 を返すため、通常は 503 が先に返る。 |

### レスポンス形式

- **形式**: **JSON**。HTML ではない。
- **根拠**: **app.py 1291–1297 行**で `return jsonify({ ... }), 503` を直接返している。Flask の `@app.errorhandler(503)`（238–255 行）は、`abort(503)` や未処理の 503 のときのみ呼ばれ、**明示的に return jsonify(…), 503 している場合は呼ばれない**。
- **body の例**:
  ```json
  {
    "error": "同時処理数の上限に達しています。",
    "error_code": "BUSY",
    "message": "現在の実行中ジョブ: 1件（上限: 1）。しばらく待ってから再試行してください。",
    "retry_after_sec": 30,
    "status_code": 503
  }
  ```
- **HTTP status**: 503。

---

## B. templates/autofill.html での /upload エラー扱い

### fetch / submit の実装箇所

| 項目 | 根拠（ファイル・行） |
|------|----------------------|
| **送信** | **templates/autofill.html 1022–1025 行**: `const response = await fetch('/upload', { method: 'POST', body: formData });` |
| **解釈** | **1027 行**: `const result = await response.json();` — **response.ok / response.status は見ていない**。常に body を JSON として読む。 |
| **分岐** | **1029–1042 行**: `if (result.job_id)` ならポーリング開始。**else** なら「エラー」として扱い、1040–1041 で `updateProgressStatus('error', ...)` と `showErrorDetails(result.error)` を実行。 |

### 503 時に表示される UI の決定ロジック

- 503 時は `result.job_id` が無いため **else に入る**。
- **1040 行**: `updateProgressStatus('error', 'エラーが発生しました', result.error || '不明なエラーが発生しました');`
  - **type = 'error'** → **1077–1089 行**で `statusDiv.classList.add('status-error')`、`titleElement.innerHTML = '❌ ' + title` → **赤系・❌**。
- **1041 行**: `showErrorDetails(result.error)` → エラー詳細ブロック表示（1147–1173 行）、「考えられる原因」等の強いエラー文言。
- **色・アイコン**: `.status-error`（627–629 行）で `border-left-color: rgba(220, 53, 69, 0.5)`（赤）。タイトルは ❌。

### 変更提案（目標: 503＝待機表示）

- **条件**: `response.status === 503` かつ `result.error_code === 'BUSY'` のときは「待機」扱いにする。
- **表示**:
  - **updateProgressStatus**: type を **'error' ではなく 'processing'（または else に入る任意の値）** にし、**title**「少々お待ちください」、**message**「現在他ユーザーが実行中。少々お待ちください」とする（または `result.message` をそのまま使う）。
  - **showErrorDetails**: BUSY のときは **呼ばない**。必要なら「○秒後に再試行できます」を progress メッセージか別の控えめな文言で表示（`result.retry_after_sec` を利用）。
- **GA4**: 503/BUSY は `autofill_error` ではなく、別イベント（例: `autofill_busy`）にするか、送らないようにする。

**具体的な差分案（autofill.html）**  
1027 行の直後〜1029 行の前で、`response.status === 503 && result.error_code === 'BUSY'` なら:

- `updateProgressStatus('processing', '少々お待ちください', result.message || '現在他ユーザーが実行中。少々お待ちください');`
- `showErrorDetails` は呼ばない（エラー詳細を出さない）。
- 必要なら「○秒後に再試行」を `progressMessage` や小さな注釈で表示。
- 上記以外（他エラー）は従来どおり `else` で `updateProgressStatus('error', ...)` と `showErrorDetails`。

---

## C. Playwright の route ハンドラ

### 実装箇所と現状

| 項目 | 根拠 |
|------|------|
| **登録** | **automation.py 1675 行**: `page.route("**/*", handle_request)` |
| **ハンドラ** | **1672–1673 行**: `def handle_request(route):` のなかで **`route.continue_()` のみ**。abort や resource_type による分岐はなし。 |

→ **現状は「すべて continue」で、画像/フォント/メディア/analytics のブロックはしていない。**

### 画像/フォント/メディア/analytics を abort する場合の実装案

- **環境変数**: 例 `BLOCK_PW_RESOURCES=1` のときだけブロックする（既存挙動を変えない）。
- **abort 対象**: `request.resource_type in ('image', 'font', 'media')` のとき `route.abort()` または `route.fulfill(status=204)`。  
  analytics は URL パターンで判定（例: `google-analytics.com`, `googletagmanager.com`, `analytics`, `gtag` 等を含む URL を abort）。
- **例外（許可）**:
  - **ドメイン**: `id.jobcan.jp`, `ssl.jobcan.jp`, `jobcan.jp` など Jobcan 本番ドメインは **document / xhr / fetch / script** は許可。必要なら **image** もログイン/CAPTCHA 用は許可（パスで例外を足す）。
  - **CAPTCHA**: URL に `captcha` / `recaptcha` / `cloudflare` 等が含まれる場合は **abort しない**（許可）。
- **実装イメージ**（handle_request 内）:
  - `BLOCK_PW_RESOURCES` が未設定/0 なら従来どおり `route.continue_()` のみ。
  - 1 のとき: `req = route.request` → `resource_type = req.resource_type`、`url = req.url`。
  - 許可: `url` が jobcan ドメインかつ（必要なら document/script/xhr のみ）、または captcha/recaptcha 等を含む → `route.continue_()`。
  - ブロック: `resource_type in ('image','font','media')` または analytics 用 URL → `route.abort()`（または `route.fulfill(status=204)`）。
  - それ以外 → `route.continue_()`。

**リスク**: ログイン/CAPTCHA で画像が必須の場合は、その URL を許可リストに含めないと失敗する可能性がある。まずは image をブロックせず、font/media と analytics だけブロックする段階的導入が安全。

---

## D. viewport と wait_for_load_state('networkidle') の箇所・置き換え案

### viewport

| 箇所 | 内容 |
|------|------|
| **automation.py 1649 行** | `context_options = { 'viewport': {'width': 1920, 'height': 1080}, ... }` — ブラウザコンテキスト作成時に 1920x1080 を指定。 |
| **1814–1816 行** | `viewport = page.viewport_size` のフォールバックで `{'width': 1920, 'height': 1080}` を使用。 |

**置き換え案**: 軽量化時は `viewport` を **1280x720** や **1366x768** に縮小（環境変数 `AUTOFILL_VIEWPORT_WIDTH` / `AUTOFILL_VIEWPORT_HEIGHT` で切り替え可能にすると安全）。

### wait_for_load_state('networkidle') の列挙と置き換え候補

すべて **automation.py** 内。

| 行 | タイムアウト | 付近の処理 | 置き換え候補 |
|----|--------------|------------|--------------|
| 433 | 45000 | 初回 goto 後 | `domcontentloaded` または ログインフォームの selector 待ち |
| 644 | 45000 | ログインボタンクリック後 | 既に 646–649 で networkidle 失敗時は domcontentloaded にフォールバック済み。最初から domcontentloaded に統一可能 |
| 674 | 30000 | 遷移後 | domcontentloaded + 必要なら主要 selector |
| 724 | 30000 | 遷移後 | 同左 |
| 766 | 30000 | 勤怠入力フロー内 | domcontentloaded または 入力欄 selector |
| 811, 820, 829, 838, 847 | 10000 | 入力/ナビ内 | 主要要素の selector 待ちに置き換え可能 |
| 882, 891, 900, 909, 918 | 10000 | 同様 | 同左 |
| 934 | 30000 | 入力フロー | domcontentloaded または selector |
| 1008 | 30000 | 同様 | 同左 |
| 1050, 1059, 1068, 1077, 1086 | 10000 | 同様 | 同左 |
| 1121, 1130, 1139, 1148, 1157 | 10000 | 同様 | 同左 |
| 1173 | 30000 | 同様 | 同左 |
| 1924 | 30000 | 他処理内 | domcontentloaded または selector |

**提案**:  
- ログイン直後・重要なナビ直後だけ `networkidle` を残し、それ以外は **`domcontentloaded`** に変更。  
- または「次の操作対象要素」が分かっている箇所は **`page.wait_for_selector(..., state='visible')`** に置き換え。  
- 一括置き換えはレイアウト/タイミング依存で失敗する可能性があるため、**段階的**（まず 10000ms の networkidle を短くする or domcontentloaded に変更）が無難。

---

## E. ファイル別の最小修正プラン（差分の粒度）

### (1) 最小修正プラン — 503 を「待機」表示にする

| ファイル | 変更内容（粒度） |
|----------|------------------|
| **templates/autofill.html** | 1) fetch の直後、`const result = await response.json();` のあと、`if (response.status === 503 && result.error_code === 'BUSY')` の分岐を追加。2) その中で `updateProgressStatus('processing', '少々お待ちください', result.message || '現在他ユーザーが実行中。少々お待ちください');` を呼び、**showErrorDetails は呼ばない**。3) 既存の `if (result.job_id) { ... } else { ... }` は、上記 BUSY でないときだけ通す（BUSY のときは return または else に入れない）。4) 必要なら BUSY 時に「○秒後に再試行できます」を message に含める（`result.retry_after_sec` 利用）。 |
| **app.py** | 任意。503/BUSY 時の `message` を「現在他ユーザーが実行中。少々お待ちください」に寄せたい場合は、1294 行付近の `message` 文言を微調整可能。現状の「現在の実行中ジョブ: …」でもフロントで上書きできるので必須ではない。 |

**影響**: 503+BUSY のときだけ、❌赤ではなくスピナー＋中立文言になる。他エラーは従来どおり。

---

### (2) 追加の軽量化プラン（安全度・リスク付き）

| ファイル | 変更内容 | 安全度 | リスク |
|----------|----------|--------|--------|
| **automation.py** | **route**: `BLOCK_PW_RESOURCES=1` のとき、`resource_type in ('font','media')` または analytics 系 URL を abort。**image は最初はブロックしない**（CAPTCHA 等に影響しうるため）。 | 中 | font/media ブロックでレイアウトが崩れる可能性は低いが、一部サイトでフォント依存表示がある場合は要確認。 |
| **automation.py** | **route**: 上に加え、**image** もブロックするが、`url` が jobcan ドメインかつ `captcha`/`recaptcha` 等を含む場合は continue。 | 低〜中 | ログイン/CAPTCHA の画像がブロックされると失敗する可能性。許可リストの調整が必要。 |
| **automation.py** | **viewport**: 1649 行を環境変数で 1280x720 等に変更可能にする。 | 高 | 小。一部レイアウトが変わる可能性のみ。 |
| **automation.py** | **networkidle 削減**: 上記 D の表のうち、タイムアウト 10000 の箇所を先に `domcontentloaded` に変更。その後、30000/45000 の箇所を必要に応じて selector 待ちに変更。 | 中 | 画面によっては要素出現が遅れ、selector が取れずタイムアウトする可能性。段階的導入とログ確認が望ましい。 |

---

## 参照したファイル・行一覧

| ファイル | 行 | 内容 |
|----------|-----|------|
| app.py | 49, 423–444, 1289–1297, 1304–1309 | MAX_ACTIVE_SESSIONS, check_resource_limits, /upload 503, メモリガード 503 |
| app.py | 238–255, 157–162 | errorhandler(503), _render_error_page |
| templates/autofill.html | 1022–1042, 1071–1097, 1147–1173, 623–633 | fetch /upload, updateProgressStatus, showErrorDetails, status-success/error/warning |
| automation.py | 1649, 1671–1675 | viewport, handle_request, page.route |
| automation.py | 433, 440, 644, 649, 674, 724, 766, 811, 820, 829, 838, 847, 882, 891, 900, 909, 918, 934, 1008, 1050, 1059, 1068, 1077, 1086, 1121, 1130, 1139, 1148, 1157, 1173, 1924 | wait_for_load_state('networkidle') または domcontentloaded |

---

*以上、実装は行わず調査と修正案の提示のみ。*
