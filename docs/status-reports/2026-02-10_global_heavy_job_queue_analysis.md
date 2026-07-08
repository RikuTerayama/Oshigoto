# グローバル重いジョブキュー適合性分析レポート

**作成日**: 2026-02-10  
**目的**: 重いジョブ用グローバルキュー（各機能共通の待機キュー）が現状の構造にマッチするかを断定できるレベルで整理する。**本レポートは分析のみで実装は行わない。**

---

## 1. Executive Summary（結論を最初に）

- **現状「重いジョブ」でキュー＋ジョブID＋非同期実行を持っているのは Jobcan AutoFill のみ**である。入口は `POST /upload`、状態は `jobs` 辞書と `job_queue`（`deque`）で管理し、`MAX_ACTIVE_SESSIONS` による直列化とキュー満杯時 503 がある（根拠: `app.py` 369–377, 451–464, 637–727, 1438–1615, 1617–1714）。
- **他機能でサーバ側の重い処理**は次のとおり。
  - **SEO クロール** (`POST /api/seo/crawl-urls`): 同リクエスト内で同期実行、最大約 60 秒、ジョブID なし・キューなし（`app.py` 1037–1086, `lib/seo_crawler.py`）。
  - **議事録整形** (`POST /api/minutes/format`): 501 Not Implemented（`app.py` 988–991）。
  - **画像一括変換・PDF・画像クリーンアップ**: `app.py` には重い処理を行う POST API が存在せず、ツールページはテンプレート表示のみ（`app.py` 959–985）。
- **プロセス構成**: Render では `WEB_CONCURRENCY=1`, `WEB_THREADS=1`（`render.yaml` 20–23）。Dockerfile の CMD は `gunicorn ... --workers ${WEB_CONCURRENCY:-2}`（`Dockerfile` 65–66）。**本番は実質 1 worker 前提**のため、**インメモリのグローバルキューは「単一プロセス内」では有効**。worker 数を 2 以上にすると、`jobs` / `job_queue` は worker ごとに別インスタンスになるため、**現状のインメモリキューは分裂し、グローバルには効かなくなる**（根拠: `render.yaml`, `Dockerfile`, `app.py` 367–377）。
- **適合性の結論**:
  - **現状のまま「上にグローバル入場制限だけ載せる」ことは可能**（例: 全重い処理の入口で「グローバル admissions lock」を取得してから既存の AutoFill キュー or 同期処理に流す）。ただし **jobs / job_queue は AutoFill 専用のまま**なので、他機能でジョブID・ステータス・キャンセルを共通化するなら **jobs の共通化または別テーブル（Redis 等）が必要**。
  - **「jobs/job_queue を共通化しないと破綻するか」**: 共通の「待機列」で複数機能を扱うなら、**共通の job ストアとキューが必要**。現状の `job_queue` は AutoFill 用の `queued_job_params` と強く結合している（`app.py` 556–563, 1562–1564）ため、他機能を同じキューに載せるには **キュー要素の抽象化（job_type + payload）と共通 job レコード**が欠かせない。
- **推奨**: 実装しない前提で、**Option A（最小・インメモリ・単一 worker 前提の共通 admissions + 既存 AutoFill キュー維持）** が現状コードへの影響が最小。Option B（Redis）・Option C（worker 分離）は安定・スケールの代わりに導入コストと運用が増える。

---

## 2. 現状アーキテクチャ（機能別、根拠行番号つき）

### 2-1. どの機能が「重いジョブ」か（網羅）

| 機能 | 重い要因 | 入口 | 根拠（ファイル:行） |
|------|----------|------|---------------------|
| **Jobcan AutoFill** | Playwright + Chromium、Excel 読込、ネットワーク | `POST /upload` | `app.py:1453`, `automation.py:14-17, 1580-1637, 1751-1776`（sync_playwright, chromium.launch, page） |
| **SEO URL クロール** | CPU・ネットワーク、同一ホスト BFS、最大 60 秒 | `POST /api/seo/crawl-urls` | `app.py:1037-1086`, `lib/seo_crawler.py:9, 208-212, 328`（deque は BFS 用、ジョブキューではない） |
| **議事録整形** | （未実装） | `POST /api/minutes/format` | `app.py:988-991`（501 返却） |
| **画像一括変換** | サーバ側に重い API なし | GET のみ（テンプレート） | `app.py:959-964` |
| **PDF ユーティリティ** | 同上 | GET のみ | `app.py:966-971` |
| **画像クリーンアップ** | 同上 | GET のみ | `app.py:973-978` |
| **議事録ツール** | 同上＋API は 501 | GET + POST 501 | `app.py:980-985`, `988-991` |

- Playwright/Chromium 使用は `app.py`（ルート名のみ）, `automation.py`, `utils.py`, `jobcan_automation.py`, `browser_utils/` に存在するが、**ジョブキュー・ジョブID・status 管理と結合しているのは `app.py` + `automation.py` の AutoFill フローのみ**（`app.py` 367–377, 594–634, 1438–1615）。

### 2-2. 各機能ごとの整理（事実のみ・行番号付き）

#### Jobcan AutoFill

| 項目 | 内容 | 根拠（ファイル:行） |
|------|------|---------------------|
| 入口 API | `POST /upload` | `app.py:1453` |
| ジョブID 発行・返却 | `job_id = str(uuid.uuid4())`。running 時は 200 + `job_id`, `status_url`。queued 時は **202** + `job_id`, `status`, `queue_position`, `status_url` | `app.py:1488, 1512-1570, 1606-1611` |
| ステータス管理 | グローバル `jobs = {}`, `jobs_lock`。status 値: `queued`, `running`, `completed`, `error`, `timeout`。`logs` は `deque(maxlen=MAX_JOB_LOGS)`（500） | `app.py:367-368, 1532-1589, 637-696, 611-616, 382` |
| 並列制御 | `job_queue`（deque）, `queued_job_params`, `MAX_ACTIVE_SESSIONS`。`count_running_jobs()` で running 数取得。running ≥ 上限なら queued に積み、キュー長 ≥ `MAX_QUEUE_SIZE` で 503 QUEUE_FULL | `app.py:371-377, 451-464, 1512-1528, 484-486` |
| キャンセル | **main ブランチに cancel 用 API なし**（別 PR で `POST /cancel/<job_id>` を追加する想定のため、本レポートでは「現状なし」と記載） | `app.py` に `cancel` / `cancelled` の検索結果なし |
| 期限切れ・クリーンアップ | `prune_jobs()`: (1) queued で `QUEUED_MAX_WAIT_SEC` 超過 → timeout 化・キュー除去・ファイル・セッション削除 (2) completed/error/timeout で `end_time` から `JOB_RETENTION_SECONDS`（1800 秒）経過で `jobs` から削除。`_check_job_timeout` でジョブ実行中のハードタイムアウト（`JOB_TIMEOUT_SEC`） | `app.py:637-727, 653-696, 377-380, 49-51`, `automation.py:1473, 1491, 1556, 1567, 1687` |
| 例外時 | `run_automation_impl` の except で `jobs[job_id]['status'] = 'error'`, `login_message` 設定。finally でファイル削除・`cleanup_user_session`・`unregister_session`・`prune_jobs`・`maybe_start_next_job` | `app.py:606-634` |
| get_status | `GET /status/<job_id>`。**毎回先頭で `prune_jobs()` を呼ぶ**（間引きなし）。404/500/200 で JSON 返却、`queue_position` は queued 時のみ | `app.py:1617-1621, 1623-1704` |

#### SEO クロール

| 項目 | 内容 | 根拠（ファイル:行） |
|------|------|---------------------|
| 入口 API | `POST /api/seo/crawl-urls` | `app.py:1037` |
| ジョブID | なし。同リクエストで同期処理し `success`, `urls`, `warnings` を返す | `app.py:1078-1085` |
| ステータス管理 | なし（リクエストスコープのみ） | - |
| 並列制御 | IP あたり 60 秒に 1 回のレート制限（`_crawl_rate_by_ip`, `_CRAWL_RATE_SEC`）。キューなし | `app.py:1002-1053` |
| キャンセル | なし | - |
| 期限切れ | `crawl(..., total_timeout=60)` で最大 60 秒 | `app.py:1078-1084`, `lib/seo_crawler.py` |
| 例外時 | 未捕捉なら 500。クライアントは同期的に結果 or エラーを受け取る | - |

#### 議事録整形 API

| 項目 | 内容 | 根拠（ファイル:行） |
|------|------|---------------------|
| 入口 API | `POST /api/minutes/format` | `app.py:988` |
| 挙動 | 501 Not Implemented | `app.py:989-991` |

#### 画像一括・PDF・画像クリーンアップ・議事録（ツールページ）

| 項目 | 内容 | 根拠（ファイル:行） |
|------|------|---------------------|
| サーバ側 | GET でテンプレートを返すのみ。重い処理を行う POST API は `app.py` に存在しない | `app.py:959-985` |

---

## 3. プロセス構成と「インメモリキュー可否」の結論

### 3-1. Gunicorn / Render の設定

| 項目 | 値 | 根拠（ファイル:行） |
|------|-----|---------------------|
| Render plan | free（コメントで 512MB 言及） | `render.yaml:5-8` |
| WEB_CONCURRENCY | 1 | `render.yaml:21-22` |
| WEB_THREADS | 1 | `render.yaml:22-23` |
| WEB_TIMEOUT | 180 | `render.yaml:25-26` |
| MAX_ACTIVE_SESSIONS | 1 | `render.yaml:43-44` |
| Dockerfile CMD | `gunicorn ... --workers ${WEB_CONCURRENCY:-2} --threads ${WEB_THREADS:-2} --worker-class sync` | `Dockerfile:65-68` |

- Render の環境変数で `WEB_CONCURRENCY=1` が渡るため、**本番は 1 worker**。Dockerfile のデフォルト 2 は Render 上では上書きされる。

### 3-2. インメモリのグローバルキューが「効く」条件・「効かない」条件

- **効く条件**: **単一 worker（単一プロセス）**。その 1 プロセス内の `jobs`, `job_queue`, `queued_job_params` が唯一の実体となり、全リクエストが同じキューを見る（`app.py:367-377`）。
- **効かない条件**: **複数 worker**。各 worker が自前の `jobs` / `job_queue` を持つため、キューが worker ごとに分裂し、「グローバルに 1 本の待機列」にはならない。また、再起動でキューは消える（インメモリのため）。

---

## 4. CPU/メモリ逼迫時の現状挙動（機能横断）

### 4-1. メモリガード・リソース制限の呼び出し箇所

| 関数・処理 | 役割 | 呼ばれる箇所（ファイル:行） |
|------------|------|-----------------------------|
| `get_system_resources()` | プロセス RSS・CPU・active_sessions 取得。MEMORY_WARNING_MB / MEMORY_LIMIT_MB 超でログ | `app.py:397-422`。呼び出し: `app.py:407-410, 468, 495, 1241, 1277, 1326, 1473, 1661, 1723, 1940` |
| `check_resource_limits()` | メモリ超過で RuntimeError。running ≥ MAX_ACTIVE で RuntimeError。readyz / sessions 等で使用 | `app.py:466-488`。呼び出し: `app.py:1724`（get_status 内） |
| `get_resource_warnings()` | 例外を出さず警告のみ。upload の即時開始パスで使用 | `app.py:491-505`。呼び出し: `app.py:1592-1597` |
| メモリガード（upload 前） | `resources['memory_mb'] > MEMORY_WARNING_MB` で 503 返却、新規ジョブ受付拒否 | `app.py:1471-1482` |
| `monitor_processing_resources()` | データ N/total 時点でメモリ使用率をログ。85% 超で警告、90% 超で RuntimeError で処理停止 | `app.py:1937-1954`。呼び出し: `automation.py:751-752` |

### 4-2. 逼迫時の挙動（事実）

| 状況 | 挙動 | 根拠（ファイル:行） |
|------|------|---------------------|
| メモリ > MEMORY_WARNING_MB（upload 時） | 503 を返し、ジョブは作成しない | `app.py:1474-1481` |
| メモリ > MEMORY_LIMIT_MB（readyz） | 503 を返す | `app.py:1242-1244` |
| running > MAX_ACTIVE_SESSIONS（readyz） | 503 を返す | `app.py:1247-1250` |
| キュー満杯（len(job_queue) ≥ MAX_QUEUE_SIZE） | 503 QUEUE_FULL、ファイル・セッション削除して返す | `app.py:1515-1528` |
| 処理中のメモリ 90% 超 | `monitor_processing_resources` が RuntimeError を投げ、ジョブは error 扱いになり finally でクリーンアップ | `app.py:1952-1954`, `automation.py:751-752` |
| ジョブがハング | `_check_job_timeout` が JOB_TIMEOUT_SEC 超過で status=timeout にし return。スレッドは finally でクリーンアップし、`maybe_start_next_job` で次を開始 | `automation.py:1473-1483, 1556, 1567, 1687`, `app.py:620-634` |
| キューが溜まり続ける | キュー長は MAX_QUEUE_SIZE で打ち切り。queued は QUEUED_MAX_WAIT_SEC 超過で timeout 化され prune で削除 | `app.py:1515-1516, 637-670` |

---

## 5. グローバルキュー適合性評価（現状にマッチするか、障壁）

### 5-1. 既存 per-feature キューを残したまま「上にグローバル入場制限」を置けるか

- **置ける**。全「重い処理」の入口（現状は実質 `POST /upload` と `POST /api/seo/crawl-urls`）で、**先にグローバルな admissions lock（例: セマフォ or 1 本の「重い処理許可」フラグ）を取得**し、取得できたら既存の AutoFill キュー or 同期 crawl に流す形にできる。
- 根拠: AutoFill は既に `jobs_lock` と `count_running_jobs()` で「running 数」を見て queued に振り分けている（`app.py:1512-1520`）。ここに「グローバル admissions」を追加するだけなら、`jobs` / `job_queue` の構造を変えずに済む。

### 5-2. jobs / job_queue を共通化しないと破綻するか

- **「共通の待機列」で複数機能を扱うなら、共通化が必要**。現状の `job_queue` は AutoFill 専用で、`queued_job_params` が `email`, `password`, `file_path`, `session_dir` 等に強く依存している（`app.py:556-563, 1562-1564`）。他機能を同じ `job_queue` に載せるには、(1) キュー要素を `(job_id, job_type)` のような形にし、(2) 実行時に `job_type` に応じて別処理に振る、あるいは (3) 共通の「ジョブレコード」を Redis 等で持ち、キューは job_id の並びだけにする、などの設計が必要。
- **結論**: 「入場制限だけグローバル」なら共通化は必須ではない。「キュー・ジョブID・ステータス・キャンセルを全機能で統一」するなら、**共通の job ストア（現行 `jobs` の拡張 or Redis）とキュー抽象化が障壁**となる。

### 5-3. 障壁のまとめ

| 障壁 | 説明 | 関連コード |
|------|------|------------|
| job_queue と queued_job_params の結合 | AutoFill 専用の payload。他機能を載せるには「job_type + 汎用 payload」または別ストアが必要 | `app.py:375-377, 556-563, 1562-1564` |
| get_status が job_id 単位 | 現行は AutoFill の `jobs[job_id]` 前提。共通化するなら status 取得 API を共通仕様にする必要 | `app.py:1617-1704` |
| 複数 worker でキュー分裂 | worker 数 2 以上だとインメモリキューはプロセスごとに別になる。グローバルに 1 本にするには Redis 等の共有ストアが必要 | `app.py:367-377`, `Dockerfile:66` |

---

## 6. Option A / B / C（実装案の比較・影響範囲）

※ いずれも**今回のレポートでは実装しない**。選択肢の整理のみ。

### Option A: 最小（インメモリ、単一プロセス前提、全重いジョブ共通の admissions lock + global queue の「入場のみ」）

| 項目 | 内容 |
|------|------|
| 概要 | 既存の AutoFill `job_queue` はそのまま。全重い処理の入口で「グローバル admissions lock」（例: 同時 1 件のセマフォ）を取得。取得できたら AutoFill は既存キューへ、SEO crawl は同期実行。 |
| 良い点 | 変更が少ない。`app.py` の upload と api_seo_crawl_urls の入口だけ触ればよい。 |
| 悪い点 | キューは AutoFill 専用のまま。SEO は「待機列」に乗らず、入場できなければ 503 やレート制限で弾く形になる。 |
| 影響範囲 | `app.py`（upload 冒頭、api_seo_crawl_urls 冒頭、グローバル lock 変数）。必要なら `lib/seo_crawler.py` の timeout 調整。 |
| Render Starter での現実性 | 1 worker のままならそのまま使える。メモリ増で安定化はしやすいが、キュー設計は変わらない。 |

### Option B: 安定（Redis 等で永続キュー、再起動耐性、複数 worker / 将来スケール対応）

| 項目 | 内容 |
|------|------|
| 概要 | ジョブメタデータとキューを Redis に置く。全重い処理を「job_id を発行 → Redis にキュー追加 → worker が 1 本取り出して実行」に統一。 |
| 良い点 | 再起動後もキューが残る（Redis の永続化による）。worker を複数にしても 1 本のキューを共有できる。 |
| 悪い点 | Redis の導入・運用・接続管理が必要。既存の `jobs` / `job_queue` / `queued_job_params` を Redis に寄せるか、二重管理になる。 |
| 影響範囲 | `app.py`（upload, status, cancel, prune の置き換え）、`automation.py`（ジョブ取得元）、新規 `lib/queue_redis.py` 等。Render では Redis アドオンが必要。 |
| Render Starter での現実性 | Redis アドオンを契約すれば可能。コストと設定が増える。 |

### Option C: 分離（Web と Worker を分ける、ジョブサーバ化）

| 項目 | 内容 |
|------|------|
| 概要 | Web はリクエスト受付とジョブ登録のみ。別プロセス or 別サービスで「worker」がキューから取り出して Playwright / crawl を実行。 |
| 良い点 | Web の応答性が安定。worker のスケールやリソースを個別に設定できる。 |
| 悪い点 | アーキテクチャ変更が大きい。キュー・ストレージ・worker のデプロイ・監視が必要。 |
| 影響範囲 | `app.py`（upload はジョブ投入のみ）、`automation.py` は worker 側に。新規 worker エントリポイント・キュー・ストア。 |
| Render Starter での現実性 | 2 サービス（web + worker）になるため、プランとコストの検討が必要。 |

---

## 7. UX/運用面の論点（グローバルキュー前提）

- **「機能 A の重い処理」実行中に「機能 B」を叩いたらどうするか**: Option A では、グローバル入場が 1 件なら B は待たせるか 503 にするかになる。待たせるなら B 用の「待機列」と UI（queued 表示）が必要で、現状は AutoFill のみがその仕組みを持つ。
- **待機表示の統一**: queued / running / completed / error / timeout を共通にするには、全機能が同じ status API（例: `GET /status/<job_id>`）と同一の status 値を使う必要がある。現状は AutoFill のみ。
- **queued の Cancel（自分の順番を抜ける）を共通仕様にする場合**: キャンセル API が job_id を前提とするため、全機能で job_id を発行し、キューに載せる設計にしないと共通化しない。現状 main には cancel API なし（別 PR で追加予定）。
- **悪用・占有対策**: 同一ユーザー上限（同一 IP や session あたりの同時 1 件・キュー内 1 件）、`MAX_QUEUE_SIZE`、レート制限（SEO の 60 秒/IP のようなもの）をグローバルキューでも検討できる。現状は AutoFill が `MAX_QUEUE_SIZE` とキュー長チェックのみ（`app.py:1515-1516`）。

---

## 8. 追加で必要な最小ログ/観測（どこに何を出すか）

- **グローバル入場**: 入場要求・入場許可・入場拒否（理由: メモリガード / キュー満杯 / グローバル lock 取得失敗）を 1 行ログに。job_id があれば付与。秘匿情報（パスワード等）は出さない。
- **キュー長・running 数**: 既存の `log_job_event` や `count_running_jobs()` の結果を、入場時・ジョブ開始時・ジョブ終了時に出すと、「後片付けで遅い」などの切り分けに使える（別 PR で cleanup_started / cleanup_finished を出している場合はそれと整合させる）。
- **get_status の prune**: 現状は **get_status の先頭で毎回 `prune_jobs()` を呼んでいる**（`app.py:1620-1621`）。ポーリング過多だと負荷になるため、**30 秒に 1 回など間引き**を入れるとよい（別 PR で `_last_status_prune_time` と 30 秒間隔を導入する想定）。

---

## 9. 検証チェックリスト（本番/ローカル、Network/ログで何を見るか）

- 本番（Render）: `/readyz` の 503/200、ログの `memory_limit_exceeded` / `max_sessions_exceeded` / `QUEUE_FULL` の有無。`job_prune` の頻度と `prune_jobs` 実行タイミング。
- ローカル: 2 クライアントで同時に `/upload` し、1 件目が running・2 件目が queued で 202 になること。キュー満杯（MAX_QUEUE_SIZE まで積む）で 503 QUEUE_FULL になること。
- Network: `/upload` の 200 vs 202、`/status/<job_id>` の 200 と `queue_position` の有無。
- ログ: `autofill_event` や `job_created`, `job_queued`, `job_started`, `job_prune` の有無と、`queue_length` / `running_count` が含まれるか（別 PR で拡張している場合）。

---

## 10. 参照（ファイル＋行番号一覧）

| ファイル | 行番号 | 内容 |
|----------|--------|------|
| app.py | 37-51 | MEMORY_LIMIT_MB, MEMORY_WARNING_MB, MAX_FILE_SIZE_MB, MAX_ACTIVE_SESSIONS, JOB_TIMEOUT_SEC |
| app.py | 101-123 | before_request, _last_prune_time, PRUNE_INTERVAL_SECONDS, prune_jobs の 300 秒間引き |
| app.py | 367-382 | jobs, jobs_lock, job_queue, queued_job_params, QUEUED_MAX_WAIT_SEC, MAX_QUEUE_SIZE, JOB_RETENTION_SECONDS, MAX_JOB_LOGS |
| app.py | 397-422 | get_system_resources |
| app.py | 440-445 | get_queue_position |
| app.py | 446-458 | log_job_event（現行シグネチャ） |
| app.py | 461-505 | count_running_jobs, check_resource_limits, get_resource_warnings |
| app.py | 553-634 | maybe_start_next_job, run_automation_impl（finally 含む） |
| app.py | 637-727 | prune_jobs（queued timeout 化と completed/error/timeout 削除） |
| app.py | 959-991 | tools/image-batch, pdf, image-cleanup, minutes, api/minutes/format（501） |
| app.py | 1002-1086 | api/seo/crawl-urls（レート制限、crawl 同期実行） |
| app.py | 1241-1264 | readyz（メモリ・running チェック、503） |
| app.py | 1438-1615 | upload_file（メモリガード、queued/running 分岐、job_queue.append, 503 QUEUE_FULL） |
| app.py | 1617-1621 | get_status（先頭で prune_jobs 無条件呼び出し） |
| app.py | 1622-1714 | get_status（jobs 参照、queue_position, 返却） |
| app.py | 1769-1794 | generate_user_message（status 別メッセージ） |
| app.py | 1937-1954 | monitor_processing_resources |
| automation.py | 14-17, 1580-1637, 1751-1776 | Playwright 利用、sync_playwright, chromium, page/context/browser クリーンアップ |
| automation.py | 1473-1483, 1491, 1556, 1567, 1687 | _check_job_timeout, JOB_TIMEOUT_SEC 適用箇所 |
| automation.py | 751-752 | monitor_processing_resources 呼び出し |
| lib/seo_crawler.py | 9, 208-212, 328 | deque（BFS 用）, crawl の total_timeout |
| render.yaml | 1-46 | plan, WEB_CONCURRENCY, WEB_THREADS, MAX_ACTIVE_SESSIONS, MEMORY_LIMIT_MB 等 |
| Dockerfile | 65-77 | gunicorn CMD, WEB_CONCURRENCY:-2, WEB_THREADS:-2 |

---

以上。
