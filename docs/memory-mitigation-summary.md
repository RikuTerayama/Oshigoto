# メモリ対策実装サマリー - P0完了

## 変更したファイル一覧

1. `automation.py` - Playwrightの確実なクリーンアップ、ブラウザ起動数/終了数のログ、メモリ計測ログ
2. `utils.py` - jobsログの上限設定
3. `app.py` - jobs辞書の間引き、メモリ閾値の整合性修正、メモリ計測ログ
4. `render.yaml` - メモリ閾値設定の整合性確認
5. `diagnostics/runtime_metrics.py` - 新規作成（計測ログユーティリティ）
6. `diagnostics/__init__.py` - 新規作成（モジュール初期化）

## 主要diff（P0-1からP0-4）

### P0-1: Playwrightの確実なクリーンアップ

**対象ファイル:** `automation.py:1518-1746`

**変更内容:**
- `browser`, `context`, `page` を `None` 初期化
- `with sync_playwright()` ブロック内で生成
- 正常終了時とエラー時の両方で `finally` ブロックで確実にクリーンアップ
- `page.close()` → `context.close()` → `browser.close()` の順に実行
- 各closeの成否をログに記録（`cleanup_result` プレフィックス）

**追加ログ:**
- `cleanup_result page_close=success` / `failed error=XXX`
- `cleanup_result context_close=success` / `failed error=XXX`
- `cleanup_result browser_close=success` / `failed error=XXX`
- `cleanup_result playwright_close=success (via_with_block)`

### P0-2: jobsログの上限設定

**対象ファイル:** `utils.py:327-348`

**変更内容:**
- `MAX_LOG_ENTRIES = 200` を定義（最大ログ件数）
- `MAX_LOG_CHARS = 2000` を定義（1ログの最大文字数）
- `add_job_log()` 関数内で:
  - メッセージ長が `MAX_LOG_CHARS` を超える場合は末尾を切って `...` を付加
  - ログ件数が `MAX_LOG_ENTRIES` を超える場合は古いログを削除（最新200件のみ保持）

**追加ログ:**
- なし（内部処理のみ）

### P0-3: jobs辞書から完了ジョブを確実に間引く

**対象ファイル:** `app.py`

**変更内容:**
- `JOB_RETENTION_SECONDS = 1800` を定義（30分）
- `prune_jobs()` 関数を追加:
  - `completed` / `error` 状態のジョブを対象
  - `end_time` から30分以上経過したジョブを削除
  - `end_time` がない場合は `start_time` から30分以上経過したジョブを削除
- ジョブ作成時に `end_time: None` を追加
- `status='completed'` / `status='error'` 設定時に `end_time = time.time()` を記録
- `run_automation()` の `finally` ブロックで `prune_jobs()` を呼び出し
- `/status/<job_id>` エンドポイントの冒頭で `prune_jobs()` を呼び出し

**追加ログ:**
- `job_prune removed job_id=XXX status=completed log_count=XXX age_sec=XXX`
- `job_prune summary removed=XXX remaining=XXX`

### P0-4: メモリ閾値の整合性を修正

**対象ファイル:** `app.py:26-35`, `render.yaml:37-41`

**変更内容:**
- `MEMORY_WARNING_MB` のデフォルト値を `512` から `400` に変更
- 起動時に `MEMORY_WARNING_MB >= MEMORY_LIMIT_MB` をチェック
- 矛盾が検出された場合は自動補正（WARNINGをLIMITの90%に設定）して警告ログを出力
- `render.yaml` のコメントを更新（整合性の説明を追加）

**追加ログ:**
- `memory_threshold_mismatch WARNING_MB=XXX >= LIMIT_MB=XXX - auto_correcting`
- `memory_threshold_auto_corrected WARNING_MB=XXX LIMIT_MB=XXX`

## 追加したログの一覧（grepしやすい固定prefix）

### cleanup_result
- `cleanup_result page_close=success`
- `cleanup_result page_close=failed error=XXX`
- `cleanup_result context_close=success`
- `cleanup_result context_close=failed error=XXX`
- `cleanup_result browser_close=success`
- `cleanup_result browser_close=failed error=XXX`
- `cleanup_result playwright_close=success (via_with_block)`

### job_prune
- `job_prune removed job_id=XXX status=XXX log_count=XXX age_sec=XXX`
- `job_prune summary removed=XXX remaining=XXX`

### memory_threshold
- `memory_threshold_mismatch WARNING_MB=XXX >= LIMIT_MB=XXX - auto_correcting`
- `memory_threshold_auto_corrected WARNING_MB=XXX LIMIT_MB=XXX`

### memory_check
- `memory_check tag=XXX rss=XXXMB job_id=XXX session_id=XXX browsers=XXX limit=XXXMB concurrency=XXX threads=XXX max_sessions=XXX`
- 主要タグ: `app_startup`, `upload_request_start`, `upload_done`, `excel_read_before`, `excel_read_after`, `browser_launch_before`, `browser_launch_after`, `job_completed`, `job_error_XXX`, `prune_jobs_before`, `prune_jobs_after`

### browser_count
- `browser_count_increment current=XXX`
- `browser_count_decrement current=XXX`

## 手動確認手順

### 1. ローカル起動確認

```bash
# アプリケーションを起動
python app.py

# または
gunicorn --bind 0.0.0.0:5000 app:app
```

### 2. 小さいExcelで1回実行

1. `/autofill` にアクセス
2. 小さいExcelファイル（数行程度）をアップロード
3. ログを確認して以下が出力されることを確認:
   - `memory_check tag=upload_done rss=XXXMB browsers=XXX`
   - `memory_check tag=excel_before rss=XXXMB`
   - `memory_check tag=excel_after rss=XXXMB`
   - `browser_count_increment current=1`
   - `memory_check tag=browser_before rss=XXXMB browsers=1`
   - `cleanup_result page_close=success`
   - `cleanup_result context_close=success`
   - `cleanup_result browser_close=success`
   - `browser_count_decrement current=0`
   - `memory_check tag=job_completed rss=XXXMB browsers=0`
   - `job_prune summary removed=XXX remaining=XXX`（30分後）

### 3. 意図的にエラーを起こす

1. 無効な認証情報でログインを試行
2. ログを確認して以下が出力されることを確認:
   - `browser_count_increment current=1`
   - `cleanup_result page_close=success` または `failed error=XXX`
   - `cleanup_result context_close=success` または `failed error=XXX`
   - `cleanup_result browser_close=success` または `failed error=XXX`
   - `browser_count_decrement current=0`（エラー時も確実にデクリメント）
   - `memory_check tag=job_error rss=XXXMB browsers=0`
   - エラー時もクリーンアップが実行され、ブラウザカウンタが0に戻ること

### 4. ログ上限の確認

1. 大量のログを生成する処理を実行
2. `/status/<job_id>` でログを確認
3. ログ件数が200件を超えないことを確認
4. 1ログの長さが2000文字を超えないことを確認

### 5. ジョブ間引きの確認

1. 複数のジョブを実行して完了させる
2. 30分以上待つ
3. `/status/<job_id>` にアクセス
4. ログに `job_prune removed` が出力されることを確認
5. 完了/エラー状態のジョブが削除されることを確認

### 6. メモリ閾値の確認

1. アプリケーション起動時のログを確認
2. `memory_threshold_mismatch` または `memory_threshold_auto_corrected` が出力されないことを確認（正常な設定の場合）
3. または、矛盾が検出された場合は自動補正が実行されることを確認

## P1実装完了（計測ログ追加）

### P1-1: 計測ログユーティリティの作成

**対象ファイル:** `diagnostics/runtime_metrics.py`（新規作成）

**実装内容:**
- スレッドセーフなカウンタ（`browser_active_count`）
- `log_memory()` 関数（メモリ使用量、jobs数、sessions数、ブラウザ数、主要envをログ出力）
- `increment_browser_count()` / `decrement_browser_count()` 関数

**呼び出しポイント:**
- ファイルアップロード直後（`app.py:756-761`）
- Excel読み込み前後（`automation.py:1465-1473`）
- ブラウザ起動前（`automation.py:1526-1528`）
- ジョブ開始時（`app.py:789-794`）
- ジョブ完了時（`automation.py:1732-1734`）
- ジョブエラー時（`automation.py:1742-1744`）
- prune_jobs実行前後（`app.py:294-304`）

### P1-2: ブラウザ起動数/終了数のログ

**対象ファイル:** `automation.py:1530-1533`, `automation.py:1787-1792`

**実装内容:**
- ブラウザ起動時に `increment_browser_count()` を呼び出し
- `finally` ブロックで `decrement_browser_count()` を呼び出し
- エラー時も確実にデクリメント

**追加ログ:**
- `browser_count increment count=XXX`
- `browser_count decrement count=XXX`

---

**実装完了日時:** 2026/02/03
**実装者:** 調査担当エンジニア
