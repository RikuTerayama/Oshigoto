# Jobcan AutoFill 直列実行＋インメモリ待機キュー — 運用・UX リスク分析レポート

**作成日**: 2026-02-10  
**想定環境**: Render Starter 512MB/0.5CPU、MAX_ACTIVE_SESSIONS=1  
**目的**: キュー運用・UX の潜在リスクと「B 完了/キャンセル後に C 開始が遅い」体感の原因切り分けを整理する。実装は行わない。

---

## 0. Executive Summary（結論と推奨、想定ユーザー影響）

### 結論

- **「2番目が完了/キャンセルした後、3番目が開始するまでが少し遅い」体感**の主因は、**次ジョブ開始が「前ジョブのクリーンアップ（Playwright 終了＋ファイル削除＋prune_jobs）の完了後」にしか行われない**設計によるものと判断できる。コード上、`maybe_start_next_job()` は **run_automation_impl の finally ブロックの最後**（app.py 634 行）でしか呼ばれず、その直前に automation の browser/context/page close と gc.collect、続けて app 側のファイル削除・セッション削除・**prune_jobs()** が同期的に実行されている。
- **運用・UX 上の主なリスク**: (P0) インメモリキュー再起動で queued 消滅、(P0) ジョブハング時は後続が一切進まない、(P1) queued 中のタブ閉じ・離脱時もサーバ側は処理を続行する設計で「キャンセル」の明示的定義がない、(P1) キューに溜まったファイルのディスク・保持時間・漏洩リスク、(P2) 同一ユーザーの連続投入によるキュー占有や MAX_QUEUE_SIZE 到達。

### 推奨（最短で実施したいもの）

- **今すぐ**: UI に「次の処理開始までにクリーンアップで数十秒かかることがあります」等の中立メッセージを追加し、体感遅延の理由を説明する。あわせて、既存の `log_job_event` / `event=cleanup_done` をログで確認し、「遅延が cleanup なのか、開始ロジックなのか、UI 認識なのか」を切り分け可能にする。
- **次**: 永続キュー（Redis 等）の検討、ワーカー分離、Render プラン変更時の同時数想定。SRE_RUNBOOK にキュー・ジョブハング時の復旧手順を追記。
- **将来**: 観測基盤・SLO/アラート・レート制限・ジョブ優先度。

### 想定ユーザー影響

- **体感**: 「順番が来たのにすぐ始まらない」→ クリーンアップ待ちである旨の表示で緩和可能。
- **再起動**: 未実行の queued は消えるため、再送が必要である旨を README/画面で明示する必要がある。
- **ハング**: 1 件がハングすると後続が永遠に待つため、監視と手動復旧（再起動等）の手順を用意する必要がある。

---

## 1. 現状の仕様（状態遷移、API、フロント表示）

### 1.1 /upload の HTTP ステータスと JSON

| 条件 | HTTP | レスポンス例（要約） | 根拠（app.py） |
|------|------|---------------------|----------------|
| 即時開始（running 枠あり） | 200 | `job_id`, `message`, `status_url`, `resource_warnings` | 1593–1599 行 |
| キューに積んだ（queued） | 202 | `job_id`, `session_id`, `status: "queued"`, `queue_position`, `message`, `status_url` | 1554–1567 行 |
| キュー満杯 | 503 | `error`, `error_code: "QUEUE_FULL"`, `status_code`（job_id なし） | 1522–1526 行 |
| メモリガード超過 | 503 | `error`, `message`, `retry_after`, `status_code`（job_id なし） | 1462–1467 行 |

### 1.2 jobs / job_queue / queued_job_params の構造とライフサイクル

- **jobs** (dict): `job_id` → ジョブ情報。`status` は `queued` | `running` | `completed` | `error` | `timeout`。queued 時は `file_path`, `session_dir`, `session_id`, `queued_at`, `start_time` 等を保持。app.py 366 行付近で初期化、372 行で `job_queue` と 374 行で `queued_job_params` を定義。
- **job_queue** (deque): queued ジョブの **job_id** を FIFO で保持。enqueue は 1547 行（`job_queue.append(job_id)`）、dequeue は maybe_start_next_job 内 553 行（`job_queue.popleft()`）。サーバ再起動で消える（README 等に記載）。
- **queued_job_params** (dict): `job_id` → 実行用パラメータ（email, password, file_path, session_dir, session_id, company_id, file_size）。キューに積むときに 1548–1556 行で設定。maybe_start_next_job で 554 行 `queued_job_params.pop(job_id)` で取り出してからスレッド起動。資格情報は start 後は参照しない設計。

### 1.3 maybe_start_next_job が呼ばれるタイミング

- **呼び出し元は 1 箇所のみ**: **run_automation_impl** の **finally** ブロックの最後（app.py 634 行）。`try/except` のあと、`os.remove(file_path)` → `cleanup_user_session(session_id)` → `unregister_session(session_id)` → `prune_jobs()` を実行した直後に `maybe_start_next_job()`。
- **before_request では呼ばない**: app.py 106–124 行。before_request では **prune_jobs** を 5 分間隔（PRUNE_INTERVAL_SECONDS=300）で実行するのみ。次ジョブ開始は行わない。
- **get_status では呼ばない**: 1621 行で `prune_jobs()` を先頭で 1 回呼ぶのみ。

したがって **「次ジョブ開始」は必ず「前ジョブのスレッドの finally が終わった直後」** に限られる。

### 1.4 get_status の返却と queued 時の queue_position

- **返却**: `status`, `progress`, `step_name`, `logs`, `elapsed_sec`, `login_status`, `login_message`, `user_message`, `session_id`, `resources`, `resource_warnings`。queued 時は **queue_position** を追加（app.py 1665–1685 行）。queue_position は **jobs_lock 内**で `job_queue` を list 化し、`job_id` の 1-based インデックスで算出（1670–1678 行）。
- **get_status の先頭**: 1621 行で `prune_jobs()` を実行。そのため **ポーリングのたびに prune_jobs が走る**。

### 1.5 フロント（templates/autofill.html）の表示分岐とポーリング

- **/upload 直後**: `result.job_id` があればポーリング開始。`result.status === 'queued'` なら「少々お待ちください」「順番待ち（あなたの順番: N番目）」「このタブを開いたままにすると…」表示（1035–1037 行）。
- **ポーリング**: **2 秒間隔**（1197 行 `}, 2000)`）。`result.status` で分岐: `completed` → 成功、`error`/`timeout` → エラー＋showErrorDetails、`queued` → 待機中表示、それ以外 → 実行中（processing）（1218–1256 行）。
- **キャンセルボタン**: AutoFill 画面には **queued/running をキャンセルするボタンはない**。他ツール（image-cleanup, pdf, image-batch）には cancel があるが、autofill.html には存在しない（grep 結果より）。

---

## 2. 事象（B 完了/キャンセル後に C 開始が遅い）と再現シナリオ

### 2.1 事象

- A 実行中に B が queued → A 完了後に B が自動開始 → **B 完了（またはユーザーが「キャンセルした」と認識した）後、C が開始するまでが「少し遅い」** という体感。

### 2.2 再現シナリオ

1. MAX_ACTIVE_SESSIONS=1 で起動。
2. A がアップロード → running。B がアップロード → 202 + queued。C がアップロード → 202 + queued（queue_position=2 等）。
3. A 完了 → B が自動で running に変わる（確認済み）。
4. B が完了（またはユーザーがタブを閉じる等して「やめた」と認識）。
5. **C の「待機中」が「実行中」に変わるまでに、体感で数十秒程度かかることがある。**

### 2.3 「キャンセル」の解釈

- **サーバ側に「ユーザーがキャンセルした」という API はない**。タブを閉じても、ジョブは running/queued のままサーバで継続する。
- **queued の期限切れ**: QUEUED_MAX_WAIT_SEC（既定 30 分）を超えた queued は prune_jobs のフェーズ1で **timeout** にされ、`login_message` に「待機時間が上限を超えたためキャンセルされました。」が入る（app.py 657 行）。ユーザーが「キャンセルした」と感じるのは、(1) タブを閉じた、(2) 長時間待って timeout になった、のいずれかの可能性がある。

---

## 3. 原因仮説（コード根拠付き）と切り分け手順

### 3.1 次ジョブ開始が「前ジョブのクリーンアップ完了後」になっているための待ち

- **根拠**: app.py 619–634 行。run_automation_impl の **finally** の順序は次のとおり。  
  1. `os.remove(file_path)`  
  2. `cleanup_user_session(session_id)`（session_dir の shutil.rmtree、517–525 行）  
  3. `unregister_session(session_id)`  
  4. `prune_jobs()`  
  5. **maybe_start_next_job()**  

  さらに、**run_automation_impl が呼ぶ process_jobcan_automation** が return する**前**に、automation.py 側の **finally**（1750–1802 行）で **page.close() → context.close() → browser.close() → gc.collect()** が同期的に実行される。つまり「C のスレッドが start する」のは、**B の Playwright 終了＋ファイル/セッション削除＋prune_jobs がすべて終わった後**。

- **切り分け**: ログで `event=cleanup_done job_id=<B>`（automation.py 1802 行）と `autofill_event job_started job_id=<C>`（app.py 573 行）の **時間差** を計測。数秒〜数十秒あれば「クリーンアップ待ち」が主因。

### 3.2 タブを閉じただけではサーバはキャンセル扱いにならない

- **根拠**: クライアントとサーバのジョブ状態は **ポーリングで取得するだけ**で、クライアントから「キャンセル」を送る API はない（autofill.html に cancel ボタンなし）。タブを閉じても、B はサーバ上では running のまま完了まで実行され、そのあと finally → maybe_start_next_job で C が開始される。
- **切り分け**: ユーザーが「B をキャンセルした」と言っている場合、実際には B は最後まで走り、その終了＋クリーンアップの時間だけ C の開始が遅れている可能性を説明する。

### 3.3 queued→running の遷移は起きているが、フロントが認識するまでのポーリング待ち

- **根拠**: ポーリング間隔は **2 秒**（autofill.html 1197 行）。C が running に変わってから、最大で約 2 秒後に次の fetch で status が更新される。
- **切り分け**: サーバログで `job_started` の時刻と、C のジョブが実際に処理を開始している時刻を比較。2 秒以内の差なら「ポーリング待ち」の影響は小さい。

### 3.4 ロック競合や例外で maybe_start_next_job が呼ばれない経路

- **根拠**: maybe_start_next_job は **run_automation_impl の finally の最後**で 1 回だけ呼ばれる（634 行）。finally の前段で **例外** が出ると、その例外は finally 内の try/except（627–632 行）で握りつぶされ、**maybe_start_next_job は必ず実行される**。ただし、**cleanup の try 内で長時間ブロック**（例: rmtree が遅い、prune_jobs が重い）している間は、maybe_start_next_job まで到達しない。
- **切り分け**: ログで `cleanup_error`（629 行）や `prune_jobs_error in before_request`（124 行）の有無を確認。また、`autofill_event job_started` が C について出ているか確認。出ていなければ「cleanup または prune でブロック/例外」の可能性。

### 3.5 Render の CPU/メモリ逼迫でスレッドの進行が遅い

- **根拠**: 512MB/0.5CPU では、**browser.close()** や **gc.collect()**（automation.py 1776, 1784 行）が重くなりやすい。メモリ逼迫時は GC やカーネル側のリソース解放に時間がかかる。
- **切り分け**: Render のメトリクスで、B 完了前後の CPU/メモリ使用率を確認。`log_memory("browser_cleanup_after", ...)`（1791 行）の前後でメモリが下がるまでに時間がかかっていないか。

### 3.6 queued ジョブのファイル I/O がボトルネック

- **根拠**: queued のファイルは **session_dir に保存されたまま**（app.py 1497 行の file_path）。maybe_start_next_job で C を開始するとき、C の file_path は既にディスク上にある。**prune_jobs** のフェーズ1では、期限切れ queued について **os.remove(fp)** と **cleanup_user_session(sid)**（rmtree）を順に実行（663–670 行）。キューに多くのジョブが溜まっていると、prune のループが長くなり、その間 jobs_lock は解放されない（フェーズ1は with jobs_lock 内でリスト構築し、ロック外で remove/rmtree）。ただし **maybe_start_next_job は prune_jobs の「後」** なので、prune が重いと「C 開始」そのものが遅れる。
- **切り分け**: ジョブ数が少ない状態（A,B,C の 3 件のみ）で同じ体感かどうか。差があれば、prune_jobs の負荷が効いている可能性。

### 3.7 check_resource_limits 等のガードが開始タイミングを遅らせているか

- **根拠**: **maybe_start_next_job** 内では check_resource_limits は呼ばれない（app.py 545–580 行）。即時開始パスでは **get_resource_warnings()**（例外を投げない）のみ（1596 行）。したがって「次ジョブ開始」がガードで遅れる要因は **ない**。

---

## 4. 潜在リスク一覧（運用・UX・セキュリティ・コスト）

| 優先度 | リスク | 内容 | 根拠・備考 |
|--------|--------|------|------------|
| **P0** | インメモリキュー再起動で queued 消滅 | サーバ再起動で job_queue / queued_job_params が消え、未実行の queued はすべて失われる。ユーザーは「順番待ち」のまま結果が返らず不満になりうる。 | app.py 372–374 行。README に記載済みだが、画面での注意喚起は要確認。 |
| **P0** | ジョブがハングすると後続が一切進まない | 1 件の running がハング（Playwright やネットワークでブロック）すると、finally に到達せず maybe_start_next_job が呼ばれない。キューが詰まったまま。 | app.py 634 行。監視と手動復旧（プロセス再起動等）の手順が SRE_RUNBOOK に必要。 |
| **P1** | queued 中にユーザーが離脱しても処理は続く | タブを閉じたりネットが切れても、サーバはジョブを実行し続ける。一方で「キャンセル」する手段が UI にない。 | autofill.html に cancel 相当なし。サーバ側にもキャンセル API なし。 |
| **P1** | キューに溜まるファイルの保管・削除 | queued の file_path は session_dir に保存されたまま（1497 行）。QUEUED_MAX_WAIT_SEC 超過で timeout にしてから削除（637–670 行）。保持中はディスク使用量・漏洩リスク・削除タイミングの説明が必要。 | 資格情報は queued_job_params に保持（メモリ）。ファイルは Excel のみ。 |
| **P1** | 「キャンセル」の定義不在 | ユーザーは「タブを閉じた＝キャンセル」と解釈しうるが、サーバは実行継続。timeout 時の「待機時間が上限を超えたためキャンセルされました。」（657 行）のみ。 | UX 上の不満と誤解を防ぐため、文言やヘルプで説明が必要。 |
| **P2** | 同一ユーザーの連続投入・キュー占有 | 同一ユーザーが連続でアップロードすると、キューを占有し、MAX_QUEUE_SIZE（50）に達すると 503 QUEUE_FULL になる。悪用や誤操作で他ユーザーが使えなくなる可能性。 | app.py 1514–1526 行。レート制限や「同一ユーザー N 件まで」は未実装。 |
| **P2** | 進捗表示が止まったときの誘導 | ポーリングが失敗し続ける（5 回で停止、1271–1275 行）と、画面は「実行中」のまま更新されない。何をしているか・どれくらい待つかの案内が不足しうる。 | autofill.html。ログやヘルプで「しばらく待っても動かない場合」の案内があるとよい。 |
| **P2** | ステータス文言の誤解 | 「待機時間が上限を超えたためキャンセルされました」が error 表示になりうる。queued と error の表示が明確に区別されているか要確認。 | 1236–1239 行で queued は status-queued。timeout は 1229–1232 行で error＋showErrorDetails。 |

---

## 5. 推奨アクション（P0/P1/P2、工数感、効果）

### 今すぐ（工数小、効果大）

- **UI にクリーンアップ待ちの説明を追加**: queued 表示または「次の処理を開始しています」表示の近くに、「次の処理開始までに、前の処理の終了作業で数十秒かかることがあります。」等の中立メッセージを 1 行追加。**効果**: 体感遅延の理由が伝わり不満を減らせる。**根拠**: 3.1 の設計。
- **既存ログでの切り分け手順をドキュメント化**: `event=cleanup_done`（automation.py 1802）、`autofill_event job_started`（app.py 573）、`cleanup_file`（622）の 3 点を、Render ログでどう検索するか・何秒差なら「cleanup 遅延」と見るかを SRE_RUNBOOK または本レポート 7 に追記。**効果**: 「遅延が cleanup か、開始ロジックか、UI か」を短時間で切り分けられる。
- **queued 表示の改善**: 既存の「このタブを開いたままにすると自動で開始します」に加え、**「前の処理の終了後、自動で開始します（数十秒かかることがあります）」** を追記してもよい。**効果**: 待ち時間の見通しがつく。

### 次（中期的）

- **永続キュー（Redis 等）の検討**: 再起動でキューが消えないようにする。**効果**: P0 の「再起動で queued 消滅」を解消。
- **ワーカー分離**: キュー＋別ワーカーで実行し、Web リクエストと重い処理を分離。**効果**: 負荷の隔離とスケールのしやすさ。
- **Render プラン変更時の想定**: MAX_ACTIVE_SESSIONS を 2 以上にする場合のキュー・同時実行の挙動を README に明記。
- **SRE_RUNBOOK にキュー・ジョブハング時の復旧手順を追記**: 「後続が進まない場合」「該当ジョブのログ確認」「再起動の判断」を簡潔に記載。

### 将来

- **観測基盤**: ジョブ単位の経過時間・キュー長・cleanup 時間をメトリクス化。
- **SLO/アラート**: 「キュー先頭の待ち時間が N 分超過」等のアラート。
- **レート制限**: 同一 IP/ユーザーあたりのアップロード頻度制限。
- **ジョブ優先度**: 現状は FIFO のみ。優先度付きキューは将来検討。

---

## 6. 変更案サマリ（ファイル名と差分方針のみ。実装しない）

### 重大不具合があった場合の最小変更案

- **ジョブハングで後続が進まない**: 現状は「手動でプロセス再起動」が現実的な復旧。コードで対処するなら、(1) **JOB_TIMEOUT_SEC** を automation 側で確実に効かせ、時間切れで status=timeout にし、finally に必ず到達させる、(2) 別スレッドで「running が N 分動いていない」を検知して強制 timeout にする、等。**ファイル**: automation.py（タイムアウト処理）、app.py（監視スレッドを入れる場合はここ）。**差分方針**: 既存の JOB_TIMEOUT_SEC がどこで効いているか確認し、最後の砦として run_automation_impl 側で「経過時間で timeout に書き換え、finally を実行」する経路を確保する。

### 観測性の最小追加案（実装しないが方針のみ）

- **ログイベント案**: 次のイベントを `log_job_event` または既存 logger で出力することを推奨。  
  - **queued_created**: キューに積んだ直後（既存 job_queued で代用可）。  
  - **running_started**: キューから取り出してスレッド start した直後（既存 job_started で代用可）。  
  - **cleanup_started** / **cleanup_finished**: run_automation_impl の finally の先頭と、maybe_start_next_job の直後。**効果**: 「遅延が cleanup なのか、maybe_start_next_job 以降なのか」を秒単位で切り分けられる。  
  - **queued_timeout**: prune_jobs で queued を timeout にしたとき（job_id, queue_position 等）。  
- **既存 log_memory**: タグは `upload_done`, `browser_after`, `browser_cleanup_after`, `prune_jobs_before`, `prune_jobs_after` 等。ここに **cleanup_started** / **cleanup_finished** を追加すると、メモリと時刻の対応が取りやすい。**ファイル**: app.py（finally の先頭と maybe_start_next_job の直後）、automation.py（既存 cleanup 前後で log_memory あり）。

### UI・ドキュメントの変更案（方針のみ）

- **templates/autofill.html**: queued メッセージまたは実行中メッセージの近くに、上記「数十秒かかることがあります」の 1 行を追加。
- **README.md**: キュー利用時の「再起動で消える」「クリーンアップで次開始まで時間がかかることがある」を 1 行ずつ明記。
- **SRE_RUNBOOK.md**: 「AutoFill キュー・ジョブハング時の確認手順」を 1 セクション追加。ログ検索キーワード（autofill_event, cleanup_done, job_started）と、復旧の判断（再起動のタイミング）を簡潔に記載。

---

## 7. 検証チェックリスト（本番/ローカル、Network、ログ）

### 本番

- [ ] Render のデプロイコミット SHA を確認し、キュー実装（maybe_start_next_job、202 + queued）が含まれているか確認する。
- [ ] 2 タブでアップロードし、2 件目の POST /upload が **202** かつ body に **job_id**, **status: "queued"** があることを Network で確認する。
- [ ] 1 件目完了後、2 件目が「実行中」に変わるまで、Network の /status/<job_id> の応答で **status** が `queued` → `running` に変わるタイミングを確認する。

### ローカル

- [ ] MAX_ACTIVE_SESSIONS=1 で起動し、A → B → C の順でアップロード。B が queued → A 完了後に B が running、B 完了後に C が running になることを確認する。
- [ ] 上記の「B 完了」から「C の status が running になるまで」の時間を、ブラウザの時刻とサーバログの `job_started` / `cleanup_done` で計測する。

### Network で見るポイント

- **POST /upload**: Status 200/202/503、body の `job_id`, `status`, `queue_position`（queued 時）。
- **GET /status/<job_id>**: ポーリングごとの `status`, `queue_position`, `elapsed_sec`。queued → running の変化が 2 秒以内に表れるか。

### ログで見るポイント

- **autofill_event**: `event=job_queued`, `job_started`, `job_completed`, `job_error`, `job_timeout`。`job_id`, `queue_position`, `elapsed_sec` で「どのジョブがいつ動いたか」を追う。
- **event=cleanup_done** (automation.py 1802): 該当 job_id のブラウザ終了がいつ完了したか。
- **cleanup_file** (app.py 622): ファイル削除がいつ行われたか。
- **cleanup_error** (app.py 629): クリーンアップ失敗で maybe_start_next_job が遅れていないか。
- **prune_jobs_error in before_request** (app.py 124): prune の例外でリクエストが遅れていないか。

---

## 参照（ファイル・行）

| 内容 | ファイル | 行 |
|------|----------|-----|
| job_queue, queued_job_params, QUEUED_MAX_WAIT_SEC, MAX_QUEUE_SIZE | app.py | 370–377 |
| cleanup_user_session（rmtree） | app.py | 517–525 |
| maybe_start_next_job | app.py | 545–580 |
| run_automation_impl finally（cleanup → maybe_start_next_job） | app.py | 619–634 |
| prune_jobs（queued 期限切れ・timeout 削除） | app.py | 637–670 |
| before_request（prune 5 分間隔） | app.py | 102–124 |
| get_status 先頭の prune_jobs | app.py | 1621 |
| /upload queued 時 202 返却 | app.py | 1509–1567 |
| log_job_event 定義・呼び出し | app.py | 446–457, 573, 600–604, 619, 1559–1560, 1590 |
| page/context/browser close, gc.collect | automation.py | 1750–1802 |
| event=cleanup_done | automation.py | 1802 |
| ポーリング 2 秒、queued/running 表示 | templates/autofill.html | 1197, 1218–1256 |
| キャンセルボタン（AutoFill にはなし） | — | — |
