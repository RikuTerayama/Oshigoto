# AutoFill 同時実行まわり実装サマリ（P0）

**日付**: 2026-02-10  
**目的**: Render 512MB/0.5CPU で「複数人が同時に触っても全体が止まらない」ようにする

---

## 変更点要約

| 項目 | 変更内容 |
|------|----------|
| **P0-1** | Render 検知時は `MAX_ACTIVE_SESSIONS` の default を 1 に（`RENDER` 未設定時は 20）。`/upload` の 503 レスポンスに `error_code: "BUSY"`, `retry_after_sec: 30` を追加。render.yaml は既に `MAX_ACTIVE_SESSIONS=1` を設定済み。 |
| **P0-2** | `check_resource_limits()` の上限判定を **running ジョブ数**（`count_running_jobs()`）に統一。session 数と乖離した場合は `jobs_session_mismatch` を警告ログに出力。 |
| **P0-3** | `prune_jobs` の削除対象 `status` に **`timeout`** を追加。timeout ジョブは `_check_job_timeout` で `end_time` を設定済みのためそのまま prune 可能。 |
| **P0-4** | `/status/<job_id>` のレスポンスに **`elapsed_sec`** を追加。automation.py の主要イベントで構造化ログ（`event=browser_launch|login_start|login_done|fill_start|fill_done|cleanup_done` + `job_id`, `elapsed_sec`）を出力。メモリログは既存の 4 点（upload_done, browser_after, job_completed, browser_cleanup_after）のまま。 |
| **Docs** | README / SRE_RUNBOOK に「512MB では同時 1 件、2 件目は BUSY(503)」の運用前提を追記。 |

---

## 追加・参照した環境変数

| 変数 | 役割 | 既定値（本番） |
|------|------|----------------|
| `MAX_ACTIVE_SESSIONS` | 同時実行可能な running ジョブ数の上限 | Render 時は **1**（`RENDER` が立っていると未設定でも 1）。それ以外は 20。 |
| `RENDER` | Render 上でセットされる。`MAX_ACTIVE_SESSIONS` 未設定時の default を 1 にするために参照 | 本番では設定済み |
| `JOB_TIMEOUT_SEC` | ジョブ全体のハードタイムアウト（秒） | 300（既存） |

※ P1 で導入する場合は `BLOCK_PW_RESOURCES=1`（画像/フォント/メディアブロック）を想定。今回は未実装。

---

## 検証手順と結果

### 手順（必須）

1. **2 件目が BUSY で返る**
   - AutoFill を 1 件実行中のまま、別タブ/別ブラウザで 2 件目の `/upload` を送る。
   - 期待: 2 件目が 503、body に `error_code: "BUSY"`, `retry_after_sec: 30` が含まれる。1 件目は完了または timeout まで進行する。
2. **timeout ジョブが prune される**
   - timeout したジョブが `prune_jobs` の対象になり、`retention_sec`（既定 30 分）経過後に `jobs` から削除されること。必要なら `JOB_RETENTION_SECONDS` を短くして確認。
3. **/status に elapsed_sec とログ**
   - `/status/<job_id>` の JSON に `elapsed_sec` が含まれること。ログに `event=browser_launch`, `event=login_start` 等が出力されること。

### 結果

- ローカルで 1) 2) 3) を実施し、期待どおりであることを確認する。
- 本番（Render）では 1) を実施し、2 件目が 503+BUSY になることと、1 件目が止まらないことを確認する。

---

## 変更ファイル一覧

- `app.py`: MAX_ACTIVE_SESSIONS の default（RENDER 時 1）、/upload の 503 に BUSY/retry_after_sec、check_resource_limits を running_count ベースに、prune_jobs に timeout、/status に elapsed_sec
- `automation.py`: 構造化ログ（event=..., job_id, elapsed_sec）を主要 6 イベントで追加
- `README.md`: 制限の仕組み・MAX_ACTIVE_SESSIONS=1 と BUSY の説明
- `SRE_RUNBOOK.md`: 運用前提と制限の仕組みの記述を更新
- `render.yaml`: 変更なし（既に MAX_ACTIVE_SESSIONS=1）
