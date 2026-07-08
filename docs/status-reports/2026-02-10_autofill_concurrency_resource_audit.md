# AutoFill 同時実行・リソース監査レポート（Render 512MB/0.5CPU 前提）

**作成日**: 2026-02-10  
**対象**: 複数ユーザー同時実行時にも止まらない設計に向けた現状分析と設計案  
**本番**: https://jobcan-automation.onrender.com/  
**実装は行わない（分析・提案のみ）**

---

## ChatGPTに渡す要約ブロック（300〜600字）

Jobcan AutoFill の同時実行・リソース監査。本番は Render 512MB/0.5CPU。現状: 同時実行上限は `MAX_ACTIVE_SESSIONS`（既定20）。`/upload` と `readyz` は **running ジョブ数**（`count_running_jobs()`）で 503 判定。`check_resource_limits` は **セッション数**で判定しており定義が二系統。jobs は `status`/`logs`(deque 500件)/`start_time` 等を保持。prune は `completed`/`error` のみで **timeout は削除対象外**。実行は `/upload` 後に `threading.Thread(target=run_automation)` で 1 本立ち、`process_jobcan_automation` で Playwright 同期実行。launch は headless と多数の `--disable-*` あり。画像/フォントの route abort はなし（`route.continue_()` のみ）。page/context/browser の close は finally で実施。ジョブ全体のハードタイムアウト（JOB_TIMEOUT_SEC=300）と set_default_timeout あり。networkidle 待機が多数あり最大 45 秒までブロックしうる。推奨: 同時実行 1（MAX_ACTIVE_SESSIONS=1）＋既存の軽量化・タイムアウト維持。最小パッチ: prune に timeout 追加、上限判定の統一、elapsed_sec/ステップログの観測追加。

---

## 0. 結論（最短で現実的な推奨）

- **推奨**: **同時実行を 1 に制限（MAX_ACTIVE_SESSIONS=1）＋ 既存の軽量化・タイムアウト・メモリガードを維持**
- 根拠: 現状は「running ジョブ数」で上限判定しており、Render では既に `MAX_ACTIVE_SESSIONS=1` の設定例がある（README/render.yaml/SRE_RUNBOOK）。512MB/0.5CPU で Playwright を 1 本動かしてもピーク時にメモリが張り付く事象があるため、**複数同時は成立条件から外し、直列化で「落ちない」ことを優先する**のが現実的。
- 追加で入れるとよい最小パッチ: `prune_jobs` に `timeout` を削除対象に含める、`check_resource_limits` の「上限」判定を running ジョブ数に統一、観測用の elapsed_sec/ステップ別ログの追加。

---

## 1. 現状の同時実行・リソース設計（根拠付き）

### A. 同時実行制御の現状

#### A.1 同時実行上限の定義

| 項目 | 根拠（ファイル・行・内容） |
|------|----------------------------|
| **定義場所・値** | `app.py` 47–48 行: `MAX_ACTIVE_SESSIONS = int(os.getenv("MAX_ACTIVE_SESSIONS", "20"))`。コメントで「Render 等では環境変数で 1 に設定推奨」と記載。 |
| **参照箇所** | `app.py`: 432, 437–438（`check_resource_limits`）、1062–1065（`readyz`）、1170（`get_status` のレスポンス）、1284–1290（`/upload`）。`render.yaml` 44 行付近で環境変数として定義。`diagnostics/runtime_metrics.py` 93, 106 行でログ用に参照。 |
| **上限判定** | **二系統ある**。（1）**running ジョブ数**: `count_running_jobs()`（414–417 行）が `status == 'running'` の件数を返し、`/upload`（1284–1290）と `readyz`（1062–1065）で `running_count >= MAX_ACTIVE_SESSIONS` のときに 503。（2）**セッション数**: `check_resource_limits()`（418–439 行）は `resources['active_sessions']`（= `len(session_manager['active_sessions'])`）で判定し、`>= MAX_ACTIVE_SESSIONS` で `RuntimeError`。 |
| **“active”の定義** | **running**: `count_running_jobs()` は `j.get('status') == 'running'` のみカウント（416 行）。ジョブの `status` は `running` / `completed` / `error` / `timeout` 等。**セッション**: `session_manager['active_sessions']` は `register_session` で増え `unregister_session` で減る（465–480 行）。登録は `/upload` 内で `register_session(session_id, job_id)`（1328 行）、解除は `run_automation` の `finally` で `unregister_session(session_id)`（1399 行）。 |

#### A.2 セッション/ジョブ管理

| 項目 | 根拠 |
|------|------|
| **jobs 辞書の構造** | `app.py` 1338–1358 行: `jobs[job_id]` に `status`, `logs`（`deque(maxlen=MAX_JOB_LOGS)`）, `progress`, `step_name`, `current_data`, `total_data`, `start_time`, `end_time`, `login_status`, `login_message`, `session_id`, `session_dir`, `file_path`, `email_hash`, `company_id`, `resource_warnings`, `last_updated` を保持。`logs` は 500 件上限（373–374 行、`utils.MAX_JOB_LOGS` と同期）。 |
| **prune/cleanup** | **prune_jobs**: `app.py` 482–540 行。`status in ('completed', 'error')` かつ `end_time` から `retention_sec`（既定 1800 秒、370 行）経過したエントリを削除。**`timeout` は対象外**のため、タイムアウトしたジョブは 30 分経過後も **残る**（削除されない）。呼び出し: `before_request` で 5 分間隔（101–119 行）、`get_status` 冒頭（1440 行）、`run_automation` の `finally`（1405, 1412, 1417 行）。 |
| **session_registry 解除漏れ** | 解除は `run_automation` の `finally`（1398–1399 行）で `cleanup_user_session(session_id)` と `unregister_session(session_id)` を実行。例外時も `finally` が走る設計。ただし `process_jobcan_automation` 内でプロセスが kill された場合など、スレッドが突然終了すると `finally` が実行されない可能性は理論上ある（未確認）。 |

#### A.3 リクエスト処理とスレッド

| 項目 | 根拠 |
|------|------|
| **/upload のスレッド起動** | `app.py` 1253 行で `@app.route('/upload', methods=['POST'])`。ファイル保存・ジョブ初期化・`register_session` の後、1362–1424 行で `run_automation` を定義し、1421 行で `thread = threading.Thread(target=run_automation)`、1422 行で `thread.daemon = True`、1423 行で `thread.start()`。HTTP レスポンスは 1426–1433 行で即座に返す。 |
| **スレッド数の制限** | 新規ジョブ開始前に `count_running_jobs() >= MAX_ACTIVE_SESSIONS` で 503 を返すため、**running ジョブ数は MAX_ACTIVE_SESSIONS を超えない**。スレッド自体の排他ロック（例: 1 本だけ起動するセマフォ）はなく、「上限超なら 503」で制御。 |
| **例外・タイムアウト時のスレッド** | `run_automation` は `try` で `process_jobcan_automation` を呼び、`except` で `jobs[job_id]` を error に更新し、`finally` でファイル削除・`cleanup_user_session`・`unregister_session`・`prune_jobs` を実行（1392–1419 行）。スレッドは 1 本で終了する設計。`process_jobcan_automation` 内の `_check_job_timeout` で `status=timeout` にした場合は `return` するだけで、スレッドは正常終了し `finally` が実行される。 |

---

### B. リソース消費に効く要因の棚卸し

#### B.1 Playwright 実行コスト

| 項目 | 根拠 |
|------|------|
| **launch オプション** | `automation.py` 1633–1636 行: `p.chromium.launch(headless=True, args=browser_args, timeout=60000)`。`browser_args` は 1588–1626 行で定義（`--no-sandbox`, `--disable-gpu`, `--disable-dev-shm-usage`, `--no-zygote`, 各種 `--disable-*`。画像/フォント/動画の明示的無効化はなし）。 |
| **context** | 1643–1659 行: `viewport={'width': 1920, 'height': 1080}`、`user_agent`、`ignore_https_errors`、`java_script_enabled=True`、`accept_downloads=True` 等。 |
| **route** | 1668–1671 行: `page.route("**/*", handle_request)` で `route.continue_()` のみ。**画像/フォント/動画の abort やブロックは行っていない**（すべて continue）。 |
| **close の確実性** | 1742–1794 行: `process_jobcan_automation` の **finally** で `page.close()` → `context.close()` → `browser.close()` を順に実行。各 close を try/except で囲み、失敗時は `cleanup_errors` に追加してログ。その後に `gc.collect()` と `log_memory("browser_cleanup_after", ...)`。 |

#### B.2 待機・タイムアウト設計

| 項目 | 根拠 |
|------|------|
| **個別 timeout** | `automation.py`: `page.set_default_timeout(30000)` と `page.set_default_navigation_timeout(30000)`（1666–1667 行）。各 `wait_for_selector` / `wait_for_load_state` / `goto` には個別に timeout が付与されている（例: 430 行 45000ms、641 行 45000ms、多数の `networkidle` が 10000–45000ms）。 |
| **ジョブ全体のハードタイムアウト** | あり。`app.py` 49–50 行で `JOB_TIMEOUT_SEC`（既定 300 秒）、1371 行で `process_jobcan_automation(..., job_timeout_sec=JOB_TIMEOUT_SEC)`。`automation.py` の `_check_job_timeout`（1470–1483 行）で経過時間をチェックし、超過時は `status=timeout` にして `return`。主要ステップ前（1488, 1540, 1550, 1680 行付近）で呼ばれている。 |
| **networkidle の長時間ブロック** | `automation.py` 内に `wait_for_load_state('networkidle', timeout=...)` が多数ある（430, 641, 671, 721, 763, 808, 817, 826, 835, 844, 879, 888, 897, 906, 915, 931, 1005, 1047, 1056, 1065, 1074, 1083, 1118, 1127, 1136, 1145, 1154, 1170, 1915 行等）。タイムアウト値は 10000–45000ms。**networkidle はネットワークが 500ms 以上アイドルになるまで待つため、遅いページでは最大 timeout までブロックしうる**。 |

#### B.3 jobs ログ肥大

| 項目 | 根拠 |
|------|------|
| **蓄積上限** | `utils.py` 330–331 行: `MAX_JOB_LOGS = 500`、`MAX_LOG_CHARS = 2000`、`MAX_JOB_LOG_BYTES = 200 * 1024`。`add_job_log`（335–377 行）で `deque(maxlen=MAX_JOB_LOGS)` を使用し、バイト数が `MAX_JOB_LOG_BYTES` を超えた場合は古いログから削除。**無限増殖はしない**。 |
| **UI ポーリング** | `templates/autofill.html`: ポーリングは 2 秒間隔（1246 行付近）。`/status/<job_id>` で取得した `result.logs` を **置換**で `progressLog` に反映（1219–1224 行: `logDiv.textContent = result.logs.join('\n')`）。同一行の増殖は防止されている。 |

#### B.4 ファイル処理

| 項目 | 根拠 |
|------|------|
| **保存場所・削除** | `app.py` 1316–1324 行: `session_dir = get_user_session_dir(session_id)`（`tempfile.gettempdir()` 配下の `jobcan_session_{session_id}`）、`file_path = os.path.join(session_dir, filename)` に保存。削除は `run_automation` の `finally`（1395–1396 行）で `os.remove(file_path)`。 |
| **例外時の残留** | `finally` が実行されれば削除される。スレッドが強制終了した場合は `os.remove` が走らず、`session_dir` も `cleanup_user_session` が呼ばれないため、一時ディレクトリが残る可能性は理論上ある（未確認）。 |

---

## 2. ボトルネック仮説（優先度順・根拠付き）

| 優先度 | 仮説 | 根拠 |
|--------|------|------|
| 1 | **同時実行数が Render リソースを超える** | デフォルト `MAX_ACTIVE_SESSIONS=20`。本番では `MAX_ACTIVE_SESSIONS=1` の設定例があるが、未設定なら 2 件目以降も受け付けてスレッドが複数立ち、Playwright が複数起動すると 512MB を容易に超える可能性が高い。 |
| 2 | **1 ジョブでも Chromium + ページでメモリが 512MB に張り付く** | launch は `headless=True` と多数の `--disable-*` で軽量化しているが、画像/フォント/動画のブロックはしていない（`route.continue_()` のみ）。viewport は 1920x1080。Jobcan のページ負荷と合わせて、1 本でもピーク時に上限近くまで使う可能性がある。 |
| 3 | **networkidle の連発でスレッドが長時間ブロック** | `automation.py` に `wait_for_load_state('networkidle', timeout=10000~45000)` が多数ある。遅延の大きい画面で最大 timeout までブロックし、その間メモリを占有し続ける。 |
| 4 | **timeout ジョブが prune されず jobs に残る** | `prune_jobs`（482–495 行）は `status in ('completed', 'error')` のみ削除対象。`timeout` は含まれていないため、タイムアウトしたジョブが辞書に残り続ける（メモリは logs 上限があるため限定的だが、件数が増えると無視できない可能性）。 |
| 5 | **check_resource_limits がセッション数で判定している** | `/upload` の「開始可否」は `count_running_jobs()` で正しく running 数を見ているが、`check_resource_limits()` は `active_sessions`（セッション数）で判定。通常は 1 ジョブ 1 セッションで一致するが、解除遅れや別経路でセッションだけ残った場合に挙動が一致しない可能性。 |

---

## 3. 設計案（案1〜4・比較表）

### 案1: 同時実行を 1 に制限（直列化）

- **内容**: `MAX_ACTIVE_SESSIONS=1` を本番の既定または強制。2 件目は 503 で拒否するか、キューに入れて「待機中」「順番待ち」を UI で表示。
- **実装コスト**: 低（環境変数設定＋既存 503 の文言整備。キュー導入するなら中）。
- **期待効果**: 同時に動く Playwright は常に 1 本。メモリ・CPU のピークを 1 ジョブ分に抑えられる。
- **リスク**: 2 人目は「しばらく待ってから」となる。キューを入れると待ち時間の見える化やキャンセルが必要になる。
- **Render 適合性**: 高。512MB/0.5CPU で「複数同時」を諦め、直列で「止まらない」ことを優先する前提に合う。

### 案2: 同時実行を 2 程度にし、徹底的に軽量化

- **内容**: Playwright の画像/フォント/メディアを route で abort、viewport 縮小、可能なら browser/context の再利用。jobs ログ上限・タイムアウト・メモリガードの強化。
- **実装コスト**: 中〜高。route の変更は CAPTCHA/レイアウトに影響する可能性があり要検証。
- **期待効果**: 1 ジョブあたりのメモリ・CPU を下げ、2 並列でも 512MB に収まる可能性がある。
- **リスク**: 軽量化によりログインや画面認識が失敗する可能性。CAPTCHA 対策とトレードオフ。
- **Render 適合性**: 中。見積もりが甘いと 2 並列で依然 OOM の可能性あり。

### 案3: ジョブ実行を別プロセス/ワーカーへ

- **内容**: Web は受付と `/status` ポーリングのみ。実行は別ワーカー（別 Render サービスや Celery 等）に渡し、キュー（Redis 等）で制御。
- **実装コスト**: 高。キュー・ワーカー・デプロイの二重化、監視の整備が必要。
- **期待効果**: Web プロセスは軽量に保てる。ワーカー側のリソースを独立してスケールできる。
- **リスク**: Redis 等のコスト・運用、Render のワーカー構成の制約（要確認）。
- **Render 適合性**: 要調査。Render でワーカー＋キューをどう組むかによる。

### 案4: AutoFill を簡易化して重い部分を削る

- **内容**: 操作手順の削減、段階的実行、ブラウザ操作の最小化（例: 必要最小のページのみ開く、networkidle を domcontentloaded に変更するなど）。
- **実装コスト**: 中。機能要件と相談が必要。
- **期待効果**: 1 ジョブの実行時間とメモリ占有時間が短くなり、直列でもスループットが上がる。
- **リスク**: 機能縮小や安定性（要素待ちの甘さ）とのトレードオフ。
- **Render 適合性**: 高。負荷を下げる方向なので 512MB に収まりやすい。

### 比較表

| 観点 | 案1 直列化 | 案2 軽量化 | 案3 ワーカー | 案4 簡易化 |
|------|------------|------------|--------------|------------|
| 実装コスト | 低 | 中〜高 | 高 | 中 |
| 期待効果 | 同時負荷を確実に 1 に | 1 ジョブあたり削減 | Web と実行の分離 | 1 ジョブの負荷・時間削減 |
| リスク | 待ち時間・UX | CAPTCHA/認識 | 運用・コスト | 機能・安定性 |
| Render 適合性 | 高 | 中 | 要調査 | 高 |

---

## 4. まず入れるべき最小パッチ候補（変更点のみ・実装はしない）

- **prune_jobs**: 削除対象の `status` に `'timeout'` を追加する（`app.py` 494 行付近の `('completed', 'error')` を `('completed', 'error', 'timeout')` に）。
- **check_resource_limits**: 「上限」の判定を、`active_sessions` ではなく `count_running_jobs()` に合わせる（または両方見て、running と session のどちらかが上限超でエラーにする）。現状は session 数のみで、`/upload` の 503 は running 数なので定義をそろえる。
- **観測**: ジョブ開始時・主要ステップ・完了/エラー/タイムアウト時に `elapsed_sec`（と必要なら `step_name`）をログに含める。既存の `log_memory` タグ（`browser_after`, `job_completed`, `browser_cleanup_after` 等）を維持し、「止まった原因」が browser launch 後か login 後かで切り分けられるようにする。
- **Render 本番**: `MAX_ACTIVE_SESSIONS=1` を明示的に設定し、README や runbook に「512MB では同時 1 推奨」と記載する。

---

## 5. 追加計測（最小）

- **ジョブごと**: `start_time` は既存。レスポンスまたはログに `elapsed_sec = now - start_time` を出す（`get_status` の返却に含めてもよい）。
- **ステップ別**: 既存の `add_job_log` のタイムスタンプで「いつどのステップにいたか」は分かる。必要なら `update_progress` や主要処理の前後で `log_memory(tag="step_5_login", ...)` のようにタグを分けると、「browser launch 後で止まった」「login 完了後で止まった」の切り分けがしやすい。
- **メモリサンプリング**: 既存の `log_memory` を、ジョブ開始前・ブラウザ起動後・ジョブ完了/クリーンアップ後の三点に限定して負荷を抑えつつ、Render のログでピーク傾向を追う。
- **止まった原因の切り分け**: 上記のタグ（例: `browser_after`, `step_5_login`, `job_completed`, `browser_cleanup_after`）と、最後の `add_job_log` メッセージがログに残っていれば、「最後にどこまで進んだか」で原因を狭り込める。

---

## 6. 参照ファイル一覧（grep 結果を反映）

| パス | 参照した主な箇所 |
|------|------------------|
| `app.py` | 47–50, 365–440, 455–480, 482–540, 98–126, 1253–1434, 1062–1069, 1284–1290, 1336–1358, 1392–1423, 1440 |
| `automation.py` | 77, 137, 430, 437, 641–646, 671, 721, 763, 808, 817, 826, 835, 844, 879, 888, 897, 906, 915, 931, 1005, 1047, 1056, 1065, 1074, 1083, 1118, 1127, 1136, 1145, 1154, 1170, 1211, 1470–1483, 1588–1671, 1742–1794, 1915 |
| `utils.py` | 328–385（MAX_JOB_LOGS, add_job_log, deque） |
| `templates/autofill.html` | 1219–1224（ログ置換）、ポーリング間隔 |
| `render.yaml` | 44（MAX_ACTIVE_SESSIONS） |
| `diagnostics/runtime_metrics.py` | 93, 106 |
| `README.md` | 456, 469 |
| `SRE_RUNBOOK.md` | 16, 192, 209, 540 |
| `docs/memory-mitigation.md` | 101, 159 |
| `docs/memory-incident-report_2026-02-03.md` | 233, 243, 400, 512, 622, 793 |

---

## 補足: ripgrep による横断検索の要約

- **Playwright**: `automation.py` の `sync_playwright`, `chromium.launch`, `new_context`, `new_page`, `route`, `wait_for_*`, `goto`。`browser_utils/browser_utils.py`, `jobcan_automation.py` にも launch/wait_for あり（本番 AutoFill は `automation.py` 経由）。
- **threading**: `app.py` 364（`jobs_lock`）, 421–423（`threading.Thread`, `run_automation`, `daemon=True`）。
- **MAX_ACTIVE_SESSIONS**: 上記「参照箇所」のとおり。
- **jobs**: `app.py` 366, 489–518（prune）, 1325–1358（初期化）, 1392–1393（error 更新）等。
- **prune_jobs**: `app.py` 482–540（定義）, 119, 1440, 1405, 1412, 1417（呼び出し）。
- **cleanup**: `app.py` 455–464（cleanup_user_session）, 1395–1399（file_path remove, cleanup_user_session, unregister_session）。`automation.py` 1742–1794（page/context/browser close, gc.collect）。
- **wait_for / networkidle**: `automation.py` に多数（上記 B.2 の行番号参照）。

---

*以上、実装は行わず分析と提案のみ。資格情報・個人情報は含めていない。*
