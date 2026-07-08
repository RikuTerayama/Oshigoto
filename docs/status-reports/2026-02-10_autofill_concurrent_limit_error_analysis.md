# AutoFill「同時処理数上限で❌エラー表示になる（1/1で弾かれる）」問題 — 現状分析レポート

**作成日**: 2026-02-10  
**目的**: 原因を断定できるレベルの根拠を出し、改善プロンプト用の分析とする。実装は行わない。

---

## 1. 症状の再整理（UI表示、期待挙動）

### 前提

- 本番: Render Starter 512MB/0.5CPU
- `MAX_ACTIVE_SESSIONS=1` を想定
- 期待: A が実行中でも B/C はアップロードでき、サーバは **queued** で受け付け、順番に自動開始。画面は **queued → running → completed** を追従

### 症状（UI）

- **表示**: 「❌ エラーが発生しました」「同時処理数の上限に達しています（実行中: 1/1）。しばらく待ってから再試行してください。」
- **発生**: 2回目以降の実行、または 1 件実行中に追加アップロードしたとき
- **結果**: 処理が始まらず、エラー詳細・ログイン失敗系の原因一覧が出る

### 期待挙動

- B/C もアップロード可能
- サーバは 503 で弾かず **job_id** を返し **queued** で受付
- 順番が来たら自動で running → completed
- 画面は待機中表示（「このタブを開いたままにすると自動で開始します」等）で、エラー詳細は出さない

---

## 2. 結論（一次原因/二次原因。最短で断定）

### 一次原因

**本番にデプロイされているコードが「503 で弾く」設計のままである。**

- UI の文言 **「同時処理数の上限に達しています（実行中: 1/1）。しばらく待ってから再試行してください。」** は、**過去の `/upload` が 503 を返すときに含めていた `message` と完全一致**する（下記「バックエンド解析」参照）。
- **現在のローカル `app.py` には `error_code: "BUSY"` を返す分岐は存在しない**（`rg "BUSY" app.py` → 0件）。代わりに「running なら queued に積んで 202 + job_id を返す」分岐がある（1497–1559 行）。
- したがって **本番が main 等の古いコミットをデプロイしている**場合、2件目で 503 + 上記 message が返り、フロントがそれをエラー表示している、と断定できる。

### 二次原因

1. **バックエンド（古いコード）**: `running_count >= MAX_ACTIVE_SESSIONS` のときに **job_id を返さず** `return jsonify({ "error_code": "BUSY", "message": "現在の実行中ジョブ: 1件（上限: 1）。しばらく待ってから再試行してください。" }), 503` している。
2. **フロント**: **`result.job_id` の有無のみ**で成功/エラーを分岐（`templates/autofill.html` 1033–1052 行）。`response.status` / `response.ok` は見ていない。503 でも body は JSON なので `response.json()` は成功するが、古い実装では **job_id が無い** → else 節で `showErrorDetails(result.error)` が実行され、❌ と「同時処理数上限…」が表示される。
3. **別経路（現行コードの潜在バグ）**: `check_resource_limits()`（app.py 465–488 行）は **`running_count >= MAX_ACTIVE_SESSIONS` で同じ文言の RuntimeError を投げる**。これは **即時開始パスのみ**（1579 行）で呼ばれる。即時開始時点では既に 1 件 running を追加した直後なので、`MAX_ACTIVE_SESSIONS=1` だと **1件目アップロードでも raise しうる**。その場合 `upload_file` の `except Exception`（1601–1602 行）で `str(e)` が返り、UI には「予期しないエラーが発生しました: 同時処理数の上限に達しています（実行中: 1/1）。しばらく待ってから再試行してください。」と出る。2件目は **即時開始パスを通らない**（queued 分支で return する）ため、2件目でこのメッセージが出るなら **古い 503 返却**が主因。

---

## 3. バックエンド解析

### 3.1 定数（app.py）

| 定数 | 行 | 内容 |
|------|-----|------|
| MAX_ACTIVE_SESSIONS | 49 | `os.getenv("MAX_ACTIVE_SESSIONS", _default_sessions)`。RENDER 時は `_default_sessions="1"`（48 行） |
| JOB_TIMEOUT_SEC | 51 | `os.getenv("JOB_TIMEOUT_SEC", "300")`（5分） |
| QUEUED_MAX_WAIT_SEC | 376 | `os.getenv("QUEUED_MAX_WAIT_SEC", "1800")`（30分） |
| MAX_QUEUE_SIZE | 377 | `os.getenv("MAX_QUEUE_SIZE", "50")` |

### 3.2 /upload の分岐図（擬似コード）

```
upload_file()  # 1425–1602 行
├── バリデーション（file, size, email, password, validate_input_data）
│   └── エラー時 → jsonify({'error': ...})  ※HTTP 200の可能性あり
├── メモリガード（1457–1468）
│   └── memory_mb > MEMORY_WARNING_MB → return jsonify({..., 'status_code': 503}), 503
├── session_id, job_id 生成 / ファイル保存 / register_session（1474–1488）
├── with jobs_lock:（1497–1578）
│   ├── running_count = sum(1 for j in jobs.values() if j.get('status') == 'running')
│   ├── if running_count >= MAX_ACTIVE_SESSIONS:
│   │   ├── if len(job_queue) >= MAX_QUEUE_SIZE:
│   │   │   └── クリーンアップ後 → return jsonify({ 'error': '現在混雑しています。しばらくしてからお試しください。', 'error_code': 'QUEUE_FULL' }), 503  （1507–1513）
│   │   └── else:
│   │       └── jobs[job_id]=queued, job_queue.append, queued_job_params 設定
│   │           → return jsonify({ job_id, status:'queued', queue_position, message, status_url }), 202  （1554–1559）
│   └── else:  # 即時開始
│       └── jobs[job_id]=running, ... （1562–1576）
├── log_job_event("job_created", ...)  # 1577
├── resource_warnings = check_resource_limits()  # 1579  ※即時開始パスのみ。ここで running_count>=MAX なら RuntimeError
├── スレッド起動 run_automation_impl  # 1585–1591
├── return jsonify({ job_id, message, status_url, resource_warnings })  # 1593–1599  ※200
└── except Exception as e:  # 1601–1602
    └── return jsonify({'error': f'予期しないエラーが発生しました: {str(e)}'})  ※200、body に str(e)
```

**重要**: 現在のコードには **「running_count >= MAX_ACTIVE_SESSIONS のときに 503 + BUSY を返す」早期 return は無い**（1456 行はコメントのみ）。

### 3.3 503 が返る条件（BUSY / QUEUE_FULL / 例外）

| 条件 | HTTP | body 例 | 行 |
|------|------|---------|-----|
| メモリガード超過 | 503 | `error`, `message`, `status_code`（job_id なし） | 1462–1467 |
| キュー満杯 | 503 | `error`, `error_code: "QUEUE_FULL"`, `status_code`（job_id なし） | 1507–1513 |
| **BUSY（同時上限）** | **現在のコードには無い** | （古いコードでは `error_code: "BUSY"`, `message`: "現在の実行中ジョブ: 1件（上限: 1）。しばらく待ってから再試行してください。"） | — |
| 例外 catch | 200 | `error: "予期しないエラーが発生しました: " + str(e)`。check_resource_limits の RuntimeError なら上記と同じ文言が str(e) に含まれる | 1601–1602 |

### 3.4 queued が返る条件（202 + job_id）

- **条件**: `running_count >= MAX_ACTIVE_SESSIONS` かつ `len(job_queue) < MAX_QUEUE_SIZE`（1499–1514 行）。
- **返却**: HTTP **202**、body に **job_id**, **status: "queued"**, **queue_position**, **message**, **status_url**（1554–1559 行）。
- **レスポンス例**（現在のコード）:
```json
{
  "job_id": "<uuid>",
  "session_id": "<session_id>",
  "status": "queued",
  "queue_position": 1,
  "message": "現在、他ユーザーが作業中です。順番に処理します。このまま開いておくと自動で開始します。",
  "status_url": "/status/<job_id>"
}
```

### 3.5 check_resource_limits の判定と呼び出し

- **定義**: app.py 465–488 行。
- **判定**: **running_count**（`count_running_jobs()`）で上限判定。**active_sessions** は参考ログ用のみ（479 行: `running_count >= MAX_ACTIVE_SESSIONS` で RuntimeError、486 行: session_count != running_count で warning ログ）。
- **呼び出し**:
  - **1579 行**: `/upload` の **即時開始パスのみ**（ロック解放後）。この時点で既に 1 件 running を追加しているため、`MAX_ACTIVE_SESSIONS=1` だと **必ず raise** する（1件目アップロードでも失敗しうる）。
  - **1702 行**: `get_active_sessions()`（`/sessions`）。running が 1 件いれば raise。

### 3.6 job_queue / queued_job_params / maybe_start_next_job

| 項目 | 有無 | 場所 |
|------|------|------|
| job_queue | あり | 372 行 `deque()` |
| queued_job_params | あり | 374 行 |
| maybe_start_next_job | あり | 532–560 行（キュー先頭を running にしてスレッド起動） |
| 呼び出し | run_automation_impl の finally | 621 行 |

### 3.7 prune_jobs の queued / timeout 扱い

- **624–657 行**: フェーズ1で **status == 'queued'** かつ **current_time - queued_at > QUEUED_MAX_WAIT_SEC** のジョブをキューから除去し、**status='timeout'** にし、ファイル・セッション削除。
- **660–666 行**: フェーズ2で **completed / error / timeout** を retention 経過後に削除（`status not in ('completed','error','timeout')` はスキップ）。**timeout は削除対象に含まれている。**

### 3.8 get_status の queued 表示（queue_position, user_message）

- **user_message**: `generate_user_message` に **status == 'queued'** の分岐あり（1769 行）: `login_message or "現在、他ユーザーが作業中。順番に処理します。"`。
- **queue_position**: **不具合あり**。1672–1674 行で `queue_position` を参照して `response_data['queue_position']` に載せているが、**get_status 内で `queue_position` を代入している箇所が無い**。queued 時に `get_queue_position(job_id)` 等で設定する処理が欠けており、**実行時 NameError になるか未定義参照**の可能性がある。

### 3.9 503 errorhandler が /upload の jsonify(…), 503 に効かない点

- **238–254 行**: `@app.errorhandler(503)` で HTML エラーページを返す。
- **重要**: `/upload` で **`return jsonify(...), 503`** のように明示的に (response, 503) を返している場合は、**この errorhandler は呼ばれない**。クライアントが受け取るのは「HTTP 503 + JSON body」であり、UI のメッセージはその JSON の `error` / `message` から来る。

---

## 4. フロントエンド解析

### 4.1 /upload レスポンス解釈の分岐（job_id ベースか status code ベースか）

- **送信**: 1026 行 `fetch('/upload', { method: 'POST', body: formData })`。
- **解釈**: 1031 行 `const result = await response.json();`。**response.status / response.ok は参照していない。**
- **分岐**: 1033 行 **`if (result.job_id)`** で成功扱い → ポーリング開始。**else** でエラー扱い → 1049–1050 で `updateProgressStatus('error', ...)` と **showErrorDetails(result.error)**。
- **結論**: **job_id の有無のみ**で成功/エラーを決めており、status code ベースではない。503 で body に job_id が無ければ必ずエラー表示になる。

### 4.2 queued の表示条件と、error 詳細の出し分け

- **queued 表示**: 1033 が真かつ **1035 `result.status === 'queued'`** のとき、1036–1037 で「順番待ちです（あなたの順番: N番目）。このタブを開いたままにすると、自分の順番になったとき自動で開始します。」を表示。**showErrorDetails は呼ばない。**
- **ポーリング時**: 1236–1239 行で `result.status === 'queued'` なら同様の待機中表示。1212 行で queued 時はログイン結果ブロックを非表示。
- **error 詳細**: **1049–1050** は「result.job_id が無い」ときのみ。**1225, 1232** はポーリングで **result.status === 'error' / 'timeout'** のときのみ showErrorDetails。**queued のときは showErrorDetails を呼ばない。**

### 4.3 BUSY / QUEUE_FULL の扱い

- **QUEUE_FULL**: 1044–1045 行で **result.error_code === 'QUEUE_FULL'** のとき **warning** 表示のみ（「混雑しています」「現在混雑しています。しばらくしてからお試しください。」）。**showErrorDetails は呼ばない。**
- **BUSY**: **専用分岐は無い**。job_id が無いため else に入り、**result.error** で showErrorDetails が呼ばれ、古い 503 の `message` または `error` がそのまま表示される。

### 4.4 queued 時の文言

- 「このタブを開いたままにすると、自分の順番になったとき自動で開始します。」は 1037 行（初回）および 1238 行（ポーリング）で **必ず含まれる**（posText + autoStart）。

---

## 5. “queued にならず error になる”原因候補ランキング（根拠付き）

| 順位 | 原因 | 根拠 |
|------|------|------|
| **1** | **本番が古いコミット（503 BUSY 返却あり）をデプロイしている** | UI の文言が古い `/upload` の 503 body の message と一致。現行 app.py に `"BUSY"` は 0 件（grep 済み）。 |
| **2** | **フロントが job_id の有無だけで成功/エラー判定している** | autofill.html 1033–1052。503 で job_id が無いと else → showErrorDetails(result.error)。 |
| **3** | **get_status で queue_position 未代入** | app.py 1672–1674 で queue_position を参照するが、同関数内で代入が無く、queued ポーリングで NameError の可能性。 |
| 4 | check_resource_limits が即時開始パスで raise する | 1579 行。1件目でも MAX=1 なら raise し、「予期しないエラー: 同時処理数上限…」になりうる。2件目は queued で return するため通常は通らない。 |

---

## 6. 最小修正方針 3案（実装しない。差分方針のみ）

### 方針 A: キューを正として動かす（本番をキュー実装に合わせる）

- **前提**: 本番のデプロイ元を、**キュー実装が入っているブランチ/コミット**に切り替える（例: feature/autofill-queue-ux-obs や fix/autofill-ui-and-stability の該当コミット）。
- **確認**: デプロイ対象の `app.py` に **「running_count >= MAX_ACTIVE_SESSIONS のとき return jsonify(..., 503)」のブロックが無いこと**を確認する。
- **追加**: get_status で queued 時に **queue_position を代入**してから response_data に載せる（例: `queue_position = get_queue_position(job_id)` を jobs_lock 内で実行）。
- **任意**: 即時開始パスで check_resource_limits() を呼ぶと 1 件目でも raise するため、呼び出しタイミングの見直しまたは「自ジョブ追加後の running は許容」とする判定の検討。

### 方針 B: BUSY / 503 を待機表示にする暫定（見た目だけ）

- **バックエンド**: 変更しない（引き続き 503 + BUSY + job_id なし）。
- **フロント**: **result.error_code === 'BUSY'** のとき、updateProgressStatus を **'queued' または 'warning'** にし、文言を「混雑中のためお待ちください。このタブを開いたままにすると自動で開始する場合があります。」等にし、**showErrorDetails を呼ばない**。  
  - 注意: job_id が無いためポーリングは開始されず、自動開始はできない。あくまで「エラー詳細を出さない」暫定。

### 方針 C: デプロイ / PR 不備の修正

- Render のデプロイ元ブランチを、**キュー実装がマージ済みのブランチ**に変更する（例: main にキュー PR をマージしてから main をデプロイ）。
- デプロイ後、**Network で POST /upload の 2 件目が 202 + job_id になっているか**を確認するチェックリストを運用に入れる。

---

## 7. 確認チェックリスト（デプロイ反映、Network で見る項目、再現コマンド）

### デプロイ反映

- [ ] Render ダッシュボードで **デプロイ元ブランチ**を確認（main か、キュー実装入りブランチか）。
- [ ] デプロイされているコミットの `app.py` で、`/upload` 内に **「running_count >= MAX_ACTIVE_SESSIONS のとき return jsonify(..., 503)」および "BUSY"** が無いことを確認（`rg "BUSY" app.py` が 0 件）。

### Network で見る項目（本番・ローカル共通）

1. **Request**: `POST /upload`（2件目、または 1 件実行中の状態で送信）。
2. **Response**:
   - **Status**: **202** なら queued 受付。**503** なら拒否（古い BUSY または QUEUE_FULL）。
   - **Body（JSON）**:
     - **job_id** があるか。
     - **status** が `"queued"` か。
     - **error_code** が `"BUSY"` または `"QUEUE_FULL"` か。
     - **message** / **error** に「同時処理数の上限に達しています」「現在の実行中ジョブ: 1件」が含まれるか。

**判定**: 本番で 503 + body に job_id が無く error_code が BUSY または message に上記文言があれば **「デプロイが古い」** と結論づける。

### ローカル再現（資格情報不要でできる範囲）

- **現在のコードの期待挙動**:
  - 2件目（running が 1 の状態で /upload）→ **HTTP 202**、body に **job_id**, **status: "queued"**, **queue_position**。
  - 1件目は即時開始パスで **check_resource_limits()** が走り、MAX_ACTIVE_SESSIONS=1 だと **RuntimeError** になる可能性あり（1件目から「予期しないエラー: 同時処理数上限…」が出る場合あり）。
- **再現方法**:
  1. `MAX_ACTIVE_SESSIONS=1` でサーバ起動（例: `set MAX_ACTIVE_SESSIONS=1` のうえで `flask run` または `python app.py`）。
  2. **2 つのブラウザタブ**で AutoFill を開き、1 タブでアップロード開始（running になる）→ もう 1 タブで同様にアップロード。
  3. 2 タブ目で **202 と job_id が返り「待機中」表示になるか**、**503 と「エラー」表示になるか**を確認。
- **curl で 2 件目だけ叩く**場合は、1 件目を「実行中」にしておく必要があるため、事前に 1 タブでアップロードを開始した状態で、別端末または別タブから `curl -X POST -F "file=@テンプレート.xlsx" -F "email=..." -F "password=..." ... /upload` で確認可能。  
- **期待**: ローカルがキュー実装済みなら 2 件目は **202 + job_id**。本番で **503 + BUSY** なら本番だけ古いデプロイ。

### 再現コマンド（手動確認用）

```bash
# 環境変数
set MAX_ACTIVE_SESSIONS=1   # Windows
# export MAX_ACTIVE_SESSIONS=1  # Linux/macOS

# サーバ起動後、2タブで順にアップロードするか、2件目の POST のみ curl で送る
# 2件目の Response: Status 202 + body に job_id, status:"queued" → キュー実装が効いている
# 2件目の Response: Status 503 + body に error_code:"BUSY" → 古いコード
```

---

## 参照（ファイル・行）

| 内容 | ファイル | 行 |
|------|----------|-----|
| MAX_ACTIVE_SESSIONS, JOB_TIMEOUT_SEC | app.py | 47–51 |
| count_running_jobs | app.py | 460–463 |
| check_resource_limits（running_count で判定、RuntimeError 文言） | app.py | 465–488（479–482） |
| job_queue, queued_job_params, QUEUED_MAX_WAIT_SEC, MAX_QUEUE_SIZE | app.py | 370–377 |
| get_queue_position | app.py | 437–443 |
| maybe_start_next_job | app.py | 532–560 |
| run_automation_impl finally | app.py | 621 |
| prune_jobs（queued 期限切れ・timeout 削除） | app.py | 624–657, 660–666 |
| /upload キュー分岐・202 返却 | app.py | 1497–1559 |
| /upload 即時開始・check_resource_limits 呼び出し | app.py | 1579 |
| /upload 例外時 | app.py | 1601–1602 |
| get_status（queue_position 参照のみ・未代入） | app.py | 1672–1674 |
| generate_user_message（queued） | app.py | 1769 |
| errorhandler(503) | app.py | 238–254 |
| fetch /upload、result.job_id 分岐 | templates/autofill.html | 1026, 1031, 1033–1052 |
| queued 表示・QUEUE_FULL・showErrorDetails | templates/autofill.html | 1035–1037, 1044–1050, 1236–1239 |
| MAX_ACTIVE_SESSIONS（本番） | render.yaml | 43–44 |
| キュー関連 env（README） | README.md | 269–270 |
