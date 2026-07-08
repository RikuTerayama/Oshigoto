# メモリ対策実装ドキュメント

## 概要

Jobcan AutomationをRender free plan（メモリ上限512MB）で安定稼働させるため、メモリスパイクとメモリリーク疑いの主要因を修正しました。

## 何を変えたか

### P0-1: Playwrightの確実なクリーンアップ

**問題:**
- ブラウザインスタンスがエラー時に確実に閉じられない可能性
- 1つのブラウザインスタンスで100-200MBを消費

**対策:**
- `browser`, `context`, `page` を `None` 初期化
- `finally` ブロックで確実にクリーンアップ（正常終了時とエラー時の両方）
- `page.close()` → `context.close()` → `browser.close()` の順に実行
- 各closeの成否をログに記録

**ファイル:** `automation.py:1522-1795`

### P0-2: jobsログの上限設定

**問題:**
- ログが無制限に蓄積され、メモリ使用量が増加

**対策:**
- `MAX_LOG_ENTRIES = 200` を定義（最大ログ件数）
- `MAX_LOG_CHARS = 2000` を定義（1ログの最大文字数）
- `add_job_log()` 関数内で自動的に制限

**ファイル:** `utils.py:327-348`

### P0-3: jobs辞書から完了ジョブを確実に間引く

**問題:**
- 完了/エラー状態のジョブがjobs辞書に残り続ける
- ログが蓄積され続ける

**対策:**
- `prune_jobs()` 関数を追加
- `completed` / `error` 状態のジョブを30分保持後に削除
- `run_automation()` の `finally` ブロックで実行
- `/status/<job_id>` エンドポイントの冒頭でも実行

**ファイル:** `app.py:251-297`, `app.py:733-752`, `app.py:817-821`

### P0-4: メモリ閾値の整合性を修正

**問題:**
- `MEMORY_WARNING_MB` のデフォルト値（512）が `MEMORY_LIMIT_MB`（450）より大きい

**対策:**
- `MEMORY_WARNING_MB` のデフォルト値を `400` に変更
- 起動時に閾値矛盾を検知して自動補正

**ファイル:** `app.py:26-35`, `render.yaml:37-41`

### P1-1: 計測ログユーティリティの作成

**目的:**
- 次回以降の原因特定が容易になる最小限の計測ログを追加

**実装:**
- `diagnostics/runtime_metrics.py` を新規作成
- スレッドセーフなカウンタ（`browser_active_count`）
- `log_memory()` 関数（メモリ使用量、jobs数、sessions数、ブラウザ数、主要envをログ出力）

**ファイル:** `diagnostics/runtime_metrics.py`（新規）

### P1-2: ブラウザ起動数/終了数のログ

**目的:**
- ブラウザインスタンスの残存を追跡

**実装:**
- ブラウザ起動時に `increment_browser_count()`
- `finally` ブロックで `decrement_browser_count()`
- エラー時も確実にデクリメント

**ファイル:** `automation.py:1530-1533`, `automation.py:1787-1792`

## どのログを見ればスパイク原因が追えるか

### メモリ使用量の推移

**ログプレフィックス:** `memory_check`

**主要タグ:**
- `upload_done` - ファイルアップロード直後
- `excel_before` / `excel_after` - Excel読み込み前後
- `browser_before` - ブラウザ起動前
- `job_start` - ジョブ開始時
- `job_completed` - ジョブ完了時
- `job_error` - ジョブエラー時
- `prune_jobs_before` / `prune_jobs_after` - ジョブ間引き前後

**ログ例:**
```
memory_check tag=upload_done rss_mb=120.5 jobs_count=2 sessions_count=1 browser_count=0 env_WEB_CONCURRENCY=1 env_WEB_THREADS=1 env_MAX_ACTIVE_SESSIONS=1 env_MEMORY_LIMIT_MB=450 env_MEMORY_WARNING_MB=400 job_id=xxx session_id=yyy
```

### ブラウザインスタンス数の推移

**ログプレフィックス:** `browser_count`

**ログ例:**
```
browser_count increment count=1
browser_count decrement count=0
```

**確認ポイント:**
- `increment` と `decrement` が対になっているか
- エラー時も `decrement` が実行されているか
- 最終的に `count=0` に戻っているか

### クリーンアップの成否

**ログプレフィックス:** `cleanup_result`

**ログ例:**
```
cleanup_result page_close=success
cleanup_result context_close=success
cleanup_result browser_close=success
cleanup_result playwright_close=success (via_with_block)
```

**確認ポイント:**
- 全て `success` になっているか
- `failed` の場合はエラー内容を確認

### ジョブ間引きの実行状況

**ログプレフィックス:** `job_prune`

**ログ例:**
```
job_prune removed job_id=xxx status=completed log_count=150 age_sec=1805.2
job_prune summary removed=3 remaining=1
```

**確認ポイント:**
- 30分以上経過したジョブが削除されているか
- `remaining` が適切な数に保たれているか

## 512MB環境での推奨設定

### render.yaml

```yaml
envVars:
  - key: WEB_CONCURRENCY
    value: "1"  # workers数（free plan 512MBで安定化）
  - key: WEB_THREADS
    value: "1"  # スレッド数（メモリ節約）
  - key: MAX_ACTIVE_SESSIONS
    value: "1"  # 同時接続数制限（free plan 512MB）
  - key: MEMORY_LIMIT_MB
    value: "450"  # OOM前に警告
  - key: MEMORY_WARNING_MB
    value: "400"  # LIMITより小さい値に設定
```

### 推奨理由

- **WEB_CONCURRENCY=1**: 複数workerはメモリを消費するため、512MB環境では1が安全
- **WEB_THREADS=1**: スレッド数が多いとメモリ使用量が増加
- **MAX_ACTIVE_SESSIONS=1**: 同時実行数を1に制限することで、メモリ使用量を予測可能に
- **MEMORY_WARNING_MB=400**: LIMIT（450）より小さい値に設定し、余裕を持たせる

## もし90%到達で停止するなら、その際に出るログの読み方

### 停止前のログパターン

1. **メモリ使用率の上昇**
   ```
   memory_check tag=XXX rss_mb=XXX jobs_count=XXX sessions_count=XXX browser_count=XXX
   ```
   - `rss_mb` が450MBに近づいているか確認
   - `browser_count` が0より大きい場合、ブラウザが残っている可能性
   - `jobs_count` が大きい場合、古いジョブが残っている可能性

2. **警告ログ**
   ```
   high_memory_usage memory_mb=XXX warning_threshold=400
   memory_limit_exceeded memory_mb=XXX limit=450
   ```

3. **緊急停止ログ**
   ```
   emergency_memory_stop data=X memory=XXX (XX%) - preventing OOM
   ```

### 停止原因の特定手順

1. **停止直前のログを確認**
   - `memory_check` ログで `rss_mb`, `browser_count`, `jobs_count` を確認
   - `browser_count` が0より大きい場合 → ブラウザが残っている
   - `jobs_count` が大きい場合 → 古いジョブが残っている

2. **クリーンアップログを確認**
   - `cleanup_result` ログで `failed` がないか確認
   - `failed` がある場合 → クリーンアップが失敗している

3. **ジョブ間引きログを確認**
   - `job_prune` ログで間引きが実行されているか確認
   - 間引きが実行されていない場合 → `prune_jobs()` が呼ばれていない可能性

4. **ブラウザカウントログを確認**
   - `browser_count increment` と `decrement` が対になっているか確認
   - `decrement` が不足している場合 → ブラウザが残っている

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
   - `memory_check tag=upload_done`
   - `memory_check tag=excel_before`
   - `memory_check tag=excel_after`
   - `browser_count increment count=1`
   - `browser_count decrement count=0`
   - `cleanup_result page_close=success`
   - `cleanup_result context_close=success`
   - `cleanup_result browser_close=success`
   - `memory_check tag=job_completed`

### 3. 意図的にエラーを起こす

1. 無効な認証情報でログインを試行
2. ログを確認して以下が出力されることを確認:
   - `browser_count increment count=1`
   - `browser_count decrement count=0`（エラー時も確実に実行）
   - `cleanup_result page_close=success (error_path)` または `(outer_error_path)`
   - `cleanup_result context_close=success (error_path)` または `(outer_error_path)`
   - `cleanup_result browser_close=success (error_path)` または `(outer_error_path)`

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

## 変更したファイル一覧

1. `automation.py` - Playwrightの確実なクリーンアップ、ブラウザカウント、メモリ計測
2. `utils.py` - jobsログの上限設定
3. `app.py` - jobs辞書の間引き、メモリ閾値の整合性修正、メモリ計測
4. `render.yaml` - メモリ閾値設定の整合性確認
5. `diagnostics/runtime_metrics.py` - 計測ログユーティリティ（新規）

## 追加したログの一覧（grepしやすい固定prefix）

### memory_check
- `memory_check tag=XXX rss_mb=XXX jobs_count=XXX sessions_count=XXX browser_count=XXX env_XXX=XXX`

### browser_count
- `browser_count increment count=XXX`
- `browser_count decrement count=XXX`

### cleanup_result
- `cleanup_result page_close=success` / `failed error=XXX`
- `cleanup_result context_close=success` / `failed error=XXX`
- `cleanup_result browser_close=success` / `failed error=XXX`
- `cleanup_result playwright_close=success (via_with_block)`

### job_prune
- `job_prune removed job_id=XXX status=XXX log_count=XXX age_sec=XXX`
- `job_prune summary removed=XXX remaining=XXX`

### memory_threshold
- `memory_threshold_mismatch WARNING_MB=XXX >= LIMIT_MB=XXX - auto_correcting`
- `memory_threshold_auto_corrected WARNING_MB=XXX LIMIT_MB=XXX`

## 次のステップ

P0とP1の実装が完了しました。次は以下を検討してください:

1. **本番環境での監視**
   - メモリ使用量の推移を定期的に確認
   - `browser_count` が0に戻っているか確認
   - `job_prune` が適切に実行されているか確認

2. **パフォーマンステスト**
   - 複数のジョブを連続実行してメモリ使用量を確認
   - エラー時のクリーンアップが確実に実行されるか確認

3. **P2実装（余力があれば）**
   - セッション掃除の自動化
   - Excel処理のメモリ削減

---

**実装完了日時:** 2026/02/03
**実装者:** 調査担当エンジニア
