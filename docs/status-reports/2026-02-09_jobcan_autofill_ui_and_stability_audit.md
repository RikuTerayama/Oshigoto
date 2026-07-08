# Jobcan AutoFill UI不整合・安定性 監査レポート

**作成日**: 2026-02-09  
**対象**: UI二重表示・誤った赤表示、Render上でのハング/リソース逼迫  
**成果物**: 原因の実装根拠付き特定と修正方針（実装は行わない）

---

## ChatGPTに渡す要約ブロック（300〜600字）

Jobcan AutoFill の監査結果です。（1）**進捗UIの二重表示**は、`app.py` の `generate_user_message()` が `login_status == 'processing'` のときに `"🔄 ログイン処理中... - {login_message}"` を返しており、`login_message` がすでに「🔄 ログイン処理中...」のため「ログイン処理中... - ログイン処理中...」と重複して表示されることが原因です（1558–1567行）。（2）**initializing 時に赤×で表示される**のは、`templates/autofill.html` の `showLoginResult()` が `processing` 以外（`initializing` 含む）をすべて `else` で `statusIcon = '❌'`, `statusClass = 'error'` にしているためです（1102–1126行）。バックエンドは initializing を失敗扱いしていません。（3）**ハング/リソース逼迫**は、`/upload` がバックグラウンドスレッドで Playwright を同期的に実行しており、`MAX_ACTIVE_SESSIONS=20` のまま Render 512MB では過大であること、ジョブ全体のハードタイムアウトがなく、`networkidle` 等の長時間待機が重なるとメモリが逼迫することが要因です。修正方針は、メッセージ重複の解消、`initializing` を「進行中」表示にすること、同時実行を1件制限または厳格化、ジョブ全体のタイムアウトと finally の徹底です。

---

## 1. Executive summary

| 項目 | 内容 |
|------|------|
| **起きていること** | ① AutoFill 進捗UIが「ログイン処理中... - ログイン処理中...」のように二重表示される ② ログイン前（status=initializing）なのにログイン結果が赤×で「失敗」のように見える ③ Render 上でメモリが 512MB 付近まで上昇し、再実行すると処理が進まない／他ユーザーへ影響する懸念 |
| **最も可能性が高い原因** | ① **二重表示**: バックエンドの `generate_user_message()` が processing 時に「ログイン処理中...」と `login_message` をハイフンで連結しており、`login_message` が同じ文言のため見た目が二重になる。② **赤×誤表示**: フロントの `showLoginResult()` が `success` / `captcha_detected` 以外をすべて error 扱いしており、`initializing` が含まれる。③ **ハング/逼迫**: バックグラウンドスレッドで Playwright を同期実行、同時実行上限が 20 のまま、ジョブ全体のハードタイムアウトがなく、`networkidle` 等の長時間待機がメモリを圧迫。 |
| **推奨方針** | UI: メッセージ連結ロジックの見直し（重複時は片方のみ表示または文言変更）、`initializing` を「進行中」として表示する分岐の追加。安定性: 同時実行を 1 件に制限するか Render 前提で厳格化、ジョブ全体のハードタイムアウト（例: 3〜5 分）の導入、例外時も含めたクリーンアップの徹底、必要に応じたブラウザ起動オプションの軽量化。 |

---

## 2. PRが出てこない件の確認結果

### 実行したコマンドと結果要約

| コマンド | 結果要約 |
|----------|----------|
| `git remote -v` | `origin` = `https://github.com/RikuTerayama/jobcan_automation.git` (fetch/push) |
| `git branch -vv` | カレント: `feature/guide-autofill-unification`、追跡: `origin/feature/guide-autofill-unification`、push 済み |
| `git log -1 --oneline` | `0ba534c ia: unify autofill guide granularity` |
| `git status -s` | ローカルに未コミット変更あり（requirements.txt、複数 static/js、docs 等） |
| `git config --get remote.origin.url` | `https://github.com/RikuTerayama/jobcan_automation.git` |

### 原因候補と確認結果（箇条書き）

- **push 漏れ**: 当該ブランチ `feature/guide-autofill-unification` はリモート追跡ありのため、このブランチについては push 済みと判断。
- **origin 違い**: 想定リポジトリが `RikuTerayama/jobcan_automation` であれば、現在の origin は一致。
- **リポ名変更 / ブランチ名違い**: 上記の前提であれば問題なし。別リポ・別ブランチで「PR が出てこない」場合は、そのブランチで同様に `git branch -vv` と `git push -u origin <branch>` の要否を確認すること。
- **権限**: コマンドからは確認していない。GitHub 上で PR 作成権限・ブランチ保護の有無を別途確認する必要がある場合は「未確認」とする。
- **結論**: 現在のブランチに限れば、PR 作成 URL（例: `https://github.com/RikuTerayama/jobcan_automation/compare/main...feature/guide-autofill-unification`）は妥当。別ブランチを指す場合は、そのブランチの push 有無・名前・origin を同じ手順で確認すること。

---

## 3. UI不具合の原因候補と根拠（重複表示・誤った赤表示）

### 3.1 二重表示「ログイン処理中... - ログイン処理中...」

| 観点 | 結果・根拠 |
|------|------------|
| **同一 DOM の二重描画** | テンプレ側で同じブロックを 2 回 include しているような重複は未検出。二重に見えるのは「1 ブロック内の文言」が重複しているため。 |
| **JS の append の多重** | 進捗メッセージは `updateProgressStatus(..., result.step_name, result.user_message)` で 1 回ずつセットしている（`templates/autofill.html` 1212 行付近）。`innerHTML +=` や `insertAdjacentHTML` の多重実行による増殖は、この進捗テキストの二重表示の主因ではない。 |
| **バックエンドのメッセージ内容** | **根拠**: `app.py` の `generate_user_message()`（1558–1574 行）。`status == 'running'` かつ `login_status == 'processing'` のとき `return f"🔄 ログイン処理中... - {login_message}"`（1567 行）。`automation.py` 1664 行で `login_message = '🔄 ログイン処理中...'` が設定されるため、`user_message` が「🔄 ログイン処理中... - 🔄 ログイン処理中...」となり、フロントでそのまま表示されると「ログイン処理中... - ログイン処理中...」のように見える。 |
| **フロントでの表示** | `templates/autofill.html` 1212 行: `updateProgressStatus('processing', result.step_name || '処理中', result.user_message || '...')`。`step_name` は「Jobcanログイン中...」等、`user_message` が上記の連結文字列のため、見出し＋本文の両方に「ログイン処理中」が入り二重表示になる。 |

**結論**: 二重表示の主因は、**バックエンドで「ログイン処理中...」と `login_message` をハイフンで連結していること**（`app.py` 1567 行）と、**その `login_message` がすでに「🔄 ログイン処理中...」であること**（`automation.py` 1664 行）の組み合わせ。

### 3.2 initializing なのに赤×で「失敗」のように表示される

| 観点 | 結果・根拠 |
|------|------------|
| **ステータスと UI のマッピング** | **根拠**: `templates/autofill.html` の `showLoginResult(loginStatus, loginMessage)`（1102–1140 行）。`loginStatus === 'processing'` のときのみログイン結果を非表示（1106–1109 行）。それ以外は `if (loginStatus === 'success')` / `else if (loginStatus === 'captcha_detected')` のいずれでもないため **`else` に入り、`statusIcon = '❌'`, `statusClass = 'error'` が設定される**（1124–1126 行）。 |
| **initializing の扱い** | バックエンドでは `login_status == 'initializing'` のとき `generate_user_message()` は `else` に入り「🔄 処理中... - {login_message}」を返しており、❌ にはしていない（1558–1569 行）。一方、フロントは **`login_status === 'initializing'` を `showLoginResult` に渡すと「processing 以外」として error 表示になる**。 |
| **ポーリングでの呼び出し** | `result.login_status !== 'processing'` のときに `showLoginResult(result.login_status, result.login_message)` を呼んでいる（1188 行付近）。そのため `initializing` の段階でもログイン結果ブロックが表示され、かつ error 表示になる。 |

**結論**: **「initializing なのに赤×」の原因は、`templates/autofill.html` の `showLoginResult()` が `success` / `captcha_detected` 以外をすべて error 扱いしていること**（1102–1126 行）。`initializing` を「進行中」として表示する分岐が存在しない。

### 3.3 その他（メモリガードの job_id 参照）

- **app.py** 1276–1282 行: メモリガードブロック内で `logger.warning(..., job_id=job_id)` としているが、`job_id` は 1299 行で生成されている。メモリガードが発動した場合、この行で **NameError になる可能性**がある。要確認。

---

## 4. ハング/リソース逼迫の原因候補と根拠（最重要）

### 4.1 実行形態とステータス管理

| 項目 | 根拠（ファイル・行・関数） |
|------|----------------------------|
| **ルート** | `app.py` の `/upload`（1245 行付近）で `upload_file()` を呼び出し。 |
| **実行形態** | バックグラウンドの **スレッド** で実行。`run_automation()` を `threading.Thread(target=run_automation)` で起動（1405–1406 行）。`process_jobcan_automation(job_id, ...)` をスレッド内で呼び出し（1355 行）。リクエストは即座に `job_id` を返し、処理はスレッド内で同期的に進行。 |
| **ステータス管理** | グローバルな `jobs` 辞書と `jobs_lock`（364 行）。`jobs[job_id]` に `status`, `login_status`, `login_message`, `step_name`, `logs` 等を保持。`get_status`（1420 行付近）で参照。 |

### 4.2 ブラウザ自動化の実体

| 項目 | 根拠 |
|------|------|
| **ライブラリ** | Playwright（`automation.py` で `from playwright.sync_api import sync_playwright`、1612–1616 行で `p.chromium.launch(...)`）。 |
| **起動** | `automation.py` 1612–1616 行: `headless=True`, `timeout=60000`、多数の `--disable-*` オプションで軽量化を試みている（1567–1606 行）。画像/フォントの明示的無効化（例: `--blink-settings=imagesEnabled=false`）は未使用。 |
| **終了** | `automation.py` 1717–1752 行付近の **finally** で `page.close()` → `context.close()` → `browser.close()` を順に実行。クリーンアップは実装されている。 |
| **例外時** | 外側の `except` で `login_message` 等を更新したあと、finally が実行される設計。例外時にプロセスが残留しないようにはなっているが、**ジョブ全体のハードタイムアウト（スレッド強制打ち切り等）はない**。 |

### 4.3 ハングの典型要因のコード上の当たり

| 要因 | 確認結果・根拠 |
|------|----------------|
| **タイムアウト** | 各 `page.wait_for_*` には個別 timeout が設定されている（例: 429–430 行 45000ms、641 行 45000ms）。ただし **ジョブ全体を N 分で打ち切る仕組みはない**。長時間 `networkidle` 待ち等が重なると、スレッドがブロックしたままメモリを占有し続ける。 |
| **リトライ** | `perform_login_with_captcha_retry` で `max_captcha_retries=3`（1667 行）。無限ループは見当たらない。 |
| **同時実行** | `MAX_ACTIVE_SESSIONS = 20`（app.py 47 行）。**Render 512MB/0.5CPU では 20 並列は過大**。1055–1057 行で `len(jobs) > MAX_ACTIVE_SESSIONS` のとき 503 を返すが、上限値そのものが Render 前提では緩い。同時実行ロックで「1 件のみ実行」とするような制限はない。 |
| **ロック** | `jobs_lock` は `get_status` やジョブ更新時の短いクリティカルセクション用。**「実行中ジョブが 1 件を超えたら新規ジョブを拒否する」ような排他は未実装**。 |
| **一時ファイル・クリーンアップ** | `run_automation` の `finally`（1375–1403 行）で `os.remove(file_path)`、`cleanup_user_session`、`unregister_session`、`prune_jobs` を実行。クリーンアップは行われている。 |

### 4.4 Render 制約前提の再発防止策（最低限のガード・方針のみ）

- **同時実行を 1 件に制限**するか、Render 用に `MAX_ACTIVE_SESSIONS` を 1 に設定し、2 件目はキューまたは「実行中です」表示で弾く。
- **ジョブ全体のハードタイムアウト**（例: 3〜5 分）を設け、超過時はスレッド内で処理を打ち切り、状態を `failed` ではなく `aborted` / `timeout` にする（実装はスレッド側の協調的チェックまたは別プロセスでの監視など、設計要検討）。
- **例外時も必ずクリーンアップ**する finally は既にあるが、ブラウザ/コンテキスト/ページの null チェックと close の順序を再確認する。
- **ブラウザ起動オプション**で、画像無効・動画無効・viewport の縮小など、さらに軽量化できる余地がある（CAPTCHA 等の要件と要相談）。

---

## 5. 修正方針（優先度順・最小変更案・影響範囲・リスク）

| 優先度 | 内容 | 最小変更案 | 影響範囲 | リスク |
|--------|------|------------|----------|--------|
| P0 | 二重表示の解消 | `generate_user_message()` で `login_status == 'processing'` かつ `login_message` がすでに「ログイン処理中」系のときは、連結せず 1 つの文言だけ返す、または `step_name` と役割を分離してフロントで重複表示しない。 | 表示文言のみ。API の返す `user_message` の形式が変わる。 | 低。 |
| P0 | initializing の赤×解消 | `showLoginResult()` に `initializing` 用の分岐を追加し、アイコンを 🔄 等の中立表示、`statusClass` を `pending` または非 error にする。 | AutoFill 画面のログイン結果ブロックのみ。 | 低。 |
| P0 | メモリガードの job_id 参照 | メモリガード発動時のログで `job_id` を参照しないか、ガードを `job_id` 生成後に移動するか、ログメッセージを「新規ジョブ開始前」などに変更する。 | ログ出力とガードの実行順序。 | ガードを後ろに移すと、その時点では既にリソースを消費している可能性あり。 |
| P1 | 同時実行の厳格化 | Render 用に `MAX_ACTIVE_SESSIONS=1` を推奨またはデフォルトに近づける。新規ジョブ開始前に「実行中ジョブ数 >= 1」なら 503 または「しばらく待ってください」を返す。 | 複数ユーザーが同時に AutoFill を実行した場合に待ちまたは拒否。 | 他ユーザー影響を抑えたい場合は許容。 |
| P1 | ジョブ全体のハードタイムアウト | スレッド内で開始時刻を記録し、所定時間を超えたら処理を打ち切り、状態を `timeout`/`aborted` にし、既存の finally でクリーンアップする。 | 長時間かかるジョブが強制終了する。 | ユーザーには「タイムアウトしました」で案内する必要あり。 |
| P2 | ブラウザ軽量化 | 画像無効・viewport 縮小等をオプションで検討。 | CAPTCHA やレイアウト依存がある場合は要検証。 | 中。 |

---

## 6. 追加で入れたい観測性（案・コード変更は行わない）

- **ログ粒度**: ジョブ開始・ブラウザ起動・ログイン試行開始/終了・ジョブ完了/エラー/タイムアウトを一貫したフォーマット（例: `job_id`, `event`, `elapsed_sec`）で出力する。
- **タイムアウトログ**: ハードタイムアウトを導入した場合、打ち切り時に `timeout_elapsed_sec` と `job_id` をログに残す。
- **実行 ID**: リクエスト/ジョブ単位で一意 ID を付与し、ログとステータスレスポンスに含めるとトレースしやすい。
- **計測**: メモリ使用量のサンプリング（既存の `log_memory` 等）を、ジョブ開始前・ブラウザ起動後・ジョブ終了時の三点に限定して負荷を抑えつつ、Render 上のスパイク傾向を把握できるようにする。

---

## 7. すぐに試せる再現手順（資格情報は書かない）

### ローカル

1. アプリを起動し、AutoFill 画面を開く。
2. 有効な Excel と、**ログインに時間がかかる／CAPTCHA が出る** 認証情報を用意する（本番の資格情報は使わない）。
3. ファイルをアップロードして「実行」。進捗ポップアップで「ログイン処理中... - ログイン処理中...」の二重表示が出るか確認する。
4. ログイン前にポーリングが返す `login_status: 'initializing'` のタイミングで、ログイン結果が赤×で表示されないか確認する（デベロッパーツールで `/status/<job_id>` の応答を確認するとよい）。
5. メモリ再現は、可能なら複数ブラウザタブで同時に複数回アップロードし、プロセスのメモリ使用量を監視する。

### 本番（Render）

1. Render のダッシュボードでメモリ使用率を確認しつつ、AutoFill を 1 件実行。完了後にメモリが戻るか確認する。
2. 同じ条件で連続して 2 件目を実行し、2 件目が進まない／ハングするか、または 503 になるかを確認する。
3. 資格情報は本番環境のものを画面に入力するが、レポートや共有用のログには絶対に含めない。

---

## 8. 参照したファイル一覧

- `app.py`（1245, 1276–1282, 1299, 1324–1344, 1354–1374, 1405–1406, 1421–1512, 1558–1574, 1055–1057, 47, 364）
- `templates/autofill.html`（951–982, 1066–1092, 1094–1099, 1102–1151, 1167–1240, 1212, 1188 付近）
- `automation.py`（1–80, 422, 695, 700, 710, 1474, 1482, 1495, 1500, 1521, 1533, 1542, 1547, 1567–1616, 1640–1642, 1660–1673, 1715–1752, 1773, 1832, 1839, 1861）
- `utils.py`（407–414, 335–377）

---

*以上、実装は行わず現状分析と修正方針までの監査レポートとする。*
