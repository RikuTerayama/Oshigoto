# メモリインシデント調査レポート - 2026/02/03

## 1. サマリー

2026年2月3日に、メモリ使用率が90-100%付近でスパイクする現象が複数回観測されました。メモリ上限512MB環境（Render free plan）で、OOM（Out of Memory）やプロセス再起動につながる可能性のある挙動が確認されています。

主な問題点:
- Playwrightブラウザインスタンスが1つあたり100-200MBを消費
- グローバルなjobs辞書に古いジョブが蓄積される可能性
- ログがjobs辞書内に無制限に蓄積される
- Excelファイルがメモリに全件読み込まれる
- ブラウザのクリーンアップがエラー時に確実に実行されない可能性

## 2. 観測されている症状

### 2.1 メモリ使用率の挙動パターン

以下のパターンが想定されます:

**パターンA: リクエスト時に一瞬上がって戻る**
- ファイルアップロード時、Excel読み込み時、Playwright起動時に一時的にスパイク
- 処理完了後にメモリが解放されれば正常
- 問題: 解放されない場合、ベースラインが上昇

**パターンB: 段差的にベースラインが上がって戻らない**
- 複数のジョブが同時実行され、各ジョブのメモリが解放されない
- jobs辞書やsession_managerに古いデータが残る
- 問題: 時間経過と共にメモリが枯渇

**パターンC: 時間と共にじわじわ増える**
- ログの蓄積、セッションの残存、ブラウザインスタンスの残存
- 問題: 長時間稼働でOOMに至る

### 2.2 想定される症状分類

| 症状 | 発生タイミング | 確度 | 影響 |
|------|--------------|------|------|
| メモリ使用率90-100%スパイク | ファイルアップロード時、Playwright起動時 | 高 | 高 |
| ベースライン上昇 | 複数ジョブ実行後 | 中 | 高 |
| プロセス再起動 | OOM発生時 | 中 | 高 |
| 503エラー | メモリ制限超過時 | 高 | 中 |
| 処理タイムアウト | メモリ不足による処理遅延 | 低 | 中 |

## 3. タイムライン

2026年2月3日のメモリスパイク観測:
- 複数回の90-100%付近のスパイクが確認
- 具体的な時刻はクラウド側ログで確認が必要

## 4. 証拠

### 4-1. ログ証拠

**必要なログ情報（未取得）:**

以下のログを取得してください:
- 期間: 2026/02/03 00:00-23:59（特にスパイクが観測された時間帯）
- 形式: テキスト形式
- 貼り付け先: `diagnostics/render_logs_2026-02-03.txt`
- 追加で欲しい情報:
  - デプロイ時刻
  - 再起動回数と時刻
  - 同時間帯のリクエスト数
  - エラーログ（OOM、Killed、exit code 137、SIGKILL等）

**取得手順:**
1. Render Dashboardにログイン
2. 対象サービス（jobcan-automation）を選択
3. Logsタブを開く
4. 期間を2026/02/03に設定
5. 全ログをコピーして `diagnostics/render_logs_2026-02-03.txt` に貼り付け

**期待されるログパターン:**
```
memory_limit_exceeded memory_mb=XXX limit=450
high_memory_usage memory_mb=XXX warning_threshold=512
emergency_memory_stop data=X memory=XXX (XX%) - preventing OOM
bg_job_start job_id=XXX session_id=XXX file_size=XXX
cleanup_complete job_id=XXX session_id=XXX cleanup_sec=XX
```

### 4-2. コード証拠

#### 4-2-1. 大きなメモリ確保につながる実装

**A. Playwrightブラウザインスタンス（最重要）**

場所: `automation.py:1607-1687`

```python
browser = p.chromium.launch(
    headless=True,
    args=browser_args,
    timeout=60000
)
context = browser.new_context(**context_options)
page = context.new_page()
```

問題点:
- 1つのブラウザインスタンスで100-200MBを消費する可能性
- ブラウザのクリーンアップが `browser.close()` で実行されるが、エラー時に確実に実行されない
- `with sync_playwright() as p:` のコンテキスト内でエラーが発生した場合、finallyブロックの外で `browser.close()` が呼ばれる可能性

確度: 高

**B. Excelファイルのメモリ読み込み**

場所: `utils.py:527-563`

```python
def load_excel_data(file_path):
    if pandas_available:
        import pandas as pd
        data = pd.read_excel(file_path)  # 全データをメモリに読み込む
        return data, len(valid_rows)
    elif openpyxl_available:
        from openpyxl import load_workbook
        wb = load_workbook(file_path)  # ワークブック全体をメモリに読み込む
        return wb, valid_rows
```

問題点:
- 10MB制限のExcelファイルでも、pandas/openpyxlがメモリ上に展開すると数倍のメモリを消費
- ストリーミング処理ではなく、全データを一度に読み込む

確度: 中

**C. ファイルアップロードと保存**

場所: `app.py:622-669`

```python
file_path = os.path.join(session_dir, filename)
file.save(file_path)  # ファイルをディスクに保存
```

問題点:
- Flaskの `request.files['file']` が一時的にメモリに保持される可能性
- 大きなファイル（10MB）の場合、メモリ上に複数コピーが存在する可能性

確度: 低

**D. ログの蓄積**

場所: `app.py:676-693`, `utils.py:330-335`

```python
jobs[job_id] = {
    'logs': [],  # ログが無制限に蓄積される
    ...
}

def add_job_log(job_id: str, message: str, jobs: dict):
    if job_id in jobs:
        jobs[job_id]['logs'].append(f"[{timestamp}] {sanitized_message}")
```

問題点:
- ログが配列に無制限に追加され続ける
- 古いジョブがjobs辞書から削除されない場合、ログが蓄積され続ける
- 1ジョブあたり数百行のログが蓄積される可能性

確度: 高

#### 4-2-2. キャッシュやグローバル変数など解放されにくい保持

**A. グローバルjobs辞書**

場所: `app.py:135-136`

```python
jobs = {}
jobs_lock = threading.Lock()
```

問題点:
- グローバル変数として、完了したジョブもjobs辞書に残り続ける可能性
- クリーンアップ処理が `finally` ブロック内にあるが、エラー時に確実に実行されるか不明
- 古いジョブがjobs辞書から削除されない場合、メモリリークの原因となる

確度: 高

**B. セッション管理**

場所: `app.py:139-148`

```python
session_manager = {
    'active_sessions': {},
    'session_lock': threading.Lock(),
    ...
}
```

問題点:
- セッションが `unregister_session()` で削除されるが、エラー時に確実に実行されない可能性
- 30分以上のセッションは `/cleanup-sessions` で削除されるが、自動実行されない

確度: 中

**C. 一時ファイルの残存**

場所: `app.py:206-211`, `app.py:213-221`

```python
def get_user_session_dir(session_id):
    session_dir = os.path.join(tempfile.gettempdir(), f'jobcan_session_{session_id}')
    if not os.path.exists(session_dir):
        os.makedirs(session_dir)
    return session_dir

def cleanup_user_session(session_id):
    try:
        session_dir = get_user_session_dir(session_id)
        if os.path.exists(session_dir):
            shutil.rmtree(session_dir)
```

問題点:
- セッションディレクトリがクリーンアップされない場合、ディスク容量は増えるがメモリには直接影響しない
- ただし、大量のセッションディレクトリが残ると、ファイルシステムのパフォーマンスに影響

確度: 低

#### 4-2-3. 同時実行数やキュー処理の設定

**A. 同時実行数制限**

場所: `app.py:30`, `render.yaml:43-44`

```python
MAX_ACTIVE_SESSIONS = int(os.getenv("MAX_ACTIVE_SESSIONS", "20"))
```

```yaml
- key: MAX_ACTIVE_SESSIONS
  value: "1"  # 同時接続数制限（free plan 512MB）
```

問題点:
- デフォルト値が20だが、render.yamlでは1に設定
- ただし、jobs辞書のサイズチェックが `len(jobs)` で行われているが、古いジョブが残っている場合、実際の同時実行数より多い

確度: 中

**B. Gunicorn設定**

場所: `Dockerfile:63-78`, `render.yaml:21-36`

```dockerfile
CMD gunicorn --bind 0.0.0.0:$PORT \
  --workers ${WEB_CONCURRENCY:-2} \
  --threads ${WEB_THREADS:-2} \
  ...
```

```yaml
- key: WEB_CONCURRENCY
  value: "1"  # workers数（free plan 512MBで安定化）
- key: WEB_THREADS
  value: "1"  # スレッド数（メモリ節約）
```

問題点:
- render.yamlでは1 worker、1 threadに設定されているが、デフォルト値が2
- 1 workerでも、Playwrightブラウザインスタンスが複数起動される可能性（jobs辞書に古いジョブが残っている場合）

確度: 中

#### 4-2-4. メモリ監視とOOM防止

場所: `app.py:150-175`, `app.py:1000-1022`

```python
def get_system_resources():
    memory_info = process.memory_info()
    memory_mb = memory_info.rss / 1024 / 1024
    if memory_mb > MEMORY_WARNING_MB:
        logger.warning(f"high_memory_usage memory_mb={memory_mb:.1f}")
    if memory_mb > MEMORY_LIMIT_MB:
        logger.error(f"memory_limit_exceeded memory_mb={memory_mb:.1f} limit={MEMORY_LIMIT_MB}")

def monitor_processing_resources(data_index, total_data):
    if memory_usage_percent > 90:
        logger.error(f"emergency_memory_stop ... - preventing OOM")
        raise RuntimeError(f"メモリ使用率が危険域に達しました: {memory_usage_percent:.1f}%")
```

問題点:
- メモリ監視は実装されているが、OOM防止のための実際のアクション（ジョブの強制終了、古いジョブの削除）が不十分
- 90%を超えた場合に例外を投げるが、既にメモリが確保された後では効果が限定的

確度: 高

### 4-3. 設定証拠

**メモリ制限設定**

場所: `app.py:27-28`, `render.yaml:38-41`

```python
MEMORY_LIMIT_MB = int(os.getenv("MEMORY_LIMIT_MB", "450"))
MEMORY_WARNING_MB = int(os.getenv("MEMORY_WARNING_MB", "512"))
```

```yaml
- key: MEMORY_LIMIT_MB
  value: "450"  # OOM前に警告
- key: MEMORY_WARNING_MB
  value: "400"
```

問題点:
- `MEMORY_WARNING_MB` のデフォルト値（512）が `MEMORY_LIMIT_MB`（450）より大きい（設定ミス）
- render.yamlでは400に設定されているが、デフォルト値が512のまま

確度: 高

## 5. 根本原因の仮説 上位3つ

### 仮説1: Playwrightブラウザインスタンスのクリーンアップ不備（確度: 高）

**根拠:**
- `automation.py:1687` で `browser.close()` が呼ばれているが、エラー発生時に確実に実行されない可能性
- `with sync_playwright() as p:` のコンテキスト内でエラーが発生した場合、finallyブロックの外で `browser.close()` が呼ばれる
- ブラウザインスタンスが1つあたり100-200MBを消費するため、複数のインスタンスが残るとメモリが枯渇

**証拠:**
- `automation.py:1690-1694` で例外処理があり、`browser.close()` が呼ばれる前にreturnされる可能性
- エラー時にブラウザが確実に閉じられる保証がない

**影響:**
- 1つのブラウザインスタンスが残ると100-200MBのメモリが解放されない
- 複数のジョブがエラーで終了した場合、複数のブラウザインスタンスが残る可能性

### 仮説2: グローバルjobs辞書への古いジョブの蓄積（確度: 高）

**根拠:**
- `app.py:135` でグローバル変数 `jobs = {}` が定義されている
- ジョブのクリーンアップが `finally` ブロック内で実行されるが、エラー時に確実に実行されるか不明
- ログが `jobs[job_id]['logs']` に無制限に蓄積される

**証拠:**
- `app.py:712-718` でエラー時にjobs辞書が更新されるが、削除されない
- `app.py:727-728` でクリーンアップが実行されるが、エラーが発生した場合、この部分が実行されない可能性

**影響:**
- 古いジョブがjobs辞書に残り続けると、メモリが解放されない
- ログが蓄積され続けると、メモリ使用量が増加

### 仮説3: Excelファイルのメモリ読み込み（確度: 中）

**根拠:**
- `utils.py:533` で `pd.read_excel(file_path)` が全データをメモリに読み込む
- `utils.py:540` で `load_workbook(file_path)` がワークブック全体をメモリに読み込む
- 10MBのExcelファイルでも、メモリ上に展開すると数倍のメモリを消費

**証拠:**
- ストリーミング処理ではなく、全データを一度に読み込む実装
- pandas/openpyxlはメモリ効率が良くない場合がある

**影響:**
- 大きなExcelファイル（10MB）の場合、メモリ上に30-50MBを消費する可能性
- 複数のジョブが同時実行されると、メモリ使用量が急増

## 6. 再現手順または再現のための計測案

### 6.1 再現手順（ローカル環境）

**前提条件:**
- メモリ制限を512MBに設定（環境変数 `MEMORY_LIMIT_MB=512`）
- 複数のジョブを同時実行

**手順:**
1. アプリケーションを起動
2. 複数のブラウザタブで `/autofill` にアクセス
3. 各タブで異なるExcelファイルをアップロード（10MB程度）
4. メモリ使用量を監視（`/readyz` エンドポイントで確認可能）
5. エラーを意図的に発生させる（無効な認証情報など）
6. メモリ使用量が90%を超えるか確認

**期待される結果:**
- メモリ使用量が90-100%に達する
- 古いジョブがjobs辞書に残る
- ブラウザインスタンスが残る

### 6.2 再現が難しい場合の計測案

**計測を入れる場所:**

1. **ブラウザインスタンス数の監視**
   - 場所: `automation.py:1607` の前後
   - 計測内容: ブラウザインスタンスの起動数と終了数
   - 実装: グローバル変数でカウント

2. **jobs辞書のサイズ監視**
   - 場所: `app.py:675` の前後
   - 計測内容: jobs辞書のサイズ、各ジョブのメモリ使用量
   - 実装: `len(jobs)` と各ジョブの `logs` 配列のサイズ

3. **Excelファイル読み込み時のメモリ使用量**
   - 場所: `utils.py:527` の前後
   - 計測内容: 読み込み前後のメモリ使用量
   - 実装: `get_system_resources()` を呼び出し

4. **セッションクリーンアップの実行確認**
   - 場所: `app.py:727-728`
   - 計測内容: クリーンアップが実行されたかどうか
   - 実装: ログに記録

**計測の実装例:**

```python
# app.py に追加
browser_instance_count = 0
browser_instance_lock = threading.Lock()

def increment_browser_count():
    global browser_instance_count
    with browser_instance_lock:
        browser_instance_count += 1
        logger.info(f"browser_instance_count={browser_instance_count}")

def decrement_browser_count():
    global browser_instance_count
    with browser_instance_lock:
        browser_instance_count -= 1
        logger.info(f"browser_instance_count={browser_instance_count}")

# automation.py に追加
from app import increment_browser_count, decrement_browser_count

# browser起動時
increment_browser_count()
try:
    browser = p.chromium.launch(...)
    ...
finally:
    try:
        browser.close()
    except:
        pass
    decrement_browser_count()
```

## 7. 改善案 優先度順

### 優先度1: すぐできる対策（影響: 大、実装コスト: 低、リスク: 低）

#### 7-1-1. ブラウザインスタンスの確実なクリーンアップ

**対象ファイル:** `automation.py`
**対象関数:** `process_jobcan_automation()`
**変更内容:**

```python
# 現在の実装（問題あり）
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(...)
        context = browser.new_context(...)
        page = context.new_page()
        # 処理...
        browser.close()  # エラー時に実行されない可能性
except Exception as e:
    # エラー処理
    return

# 改善案
browser = None
context = None
page = None
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(...)
        context = browser.new_context(...)
        page = context.new_page()
        # 処理...
except Exception as e:
    # エラー処理
    pass
finally:
    # 確実にクリーンアップ
    try:
        if page:
            page.close()
    except:
        pass
    try:
        if context:
            context.close()
    except:
        pass
    try:
        if browser:
            browser.close()
    except:
        pass
```

**期待される効果:**
- ブラウザインスタンスが確実に閉じられる
- メモリリークの防止

**リスク:**
- 低（既存の処理ロジックに影響しない）

#### 7-1-2. jobs辞書のクリーンアップ強化

**対象ファイル:** `app.py`
**対象関数:** `run_automation()` 内のfinallyブロック
**変更内容:**

```python
# 現在の実装
finally:
    try:
        cleanup_user_session(session_id)
        unregister_session(session_id)
    except Exception as cleanup_error:
        logger.error(f"cleanup_error ...")

# 改善案
finally:
    try:
        cleanup_user_session(session_id)
        unregister_session(session_id)
    except Exception as cleanup_error:
        logger.error(f"cleanup_error ...")
    finally:
        # jobs辞書からも確実に削除
        with jobs_lock:
            if job_id in jobs:
                # ログを制限（最新100件のみ保持）
                if len(jobs[job_id].get('logs', [])) > 100:
                    jobs[job_id]['logs'] = jobs[job_id]['logs'][-100:]
                # ジョブを削除（完了後30分経過したもの）
                job_age = time.time() - jobs[job_id].get('start_time', 0)
                if jobs[job_id]['status'] in ('completed', 'error') and job_age > 1800:
                    del jobs[job_id]
                    logger.info(f"job_cleaned job_id={job_id} age_sec={job_age:.1f}")
```

**期待される効果:**
- 古いジョブがjobs辞書から削除される
- ログの蓄積が制限される

**リスク:**
- 低（既存の処理ロジックに影響しない）

#### 7-1-3. ログの蓄積制限

**対象ファイル:** `utils.py`
**対象関数:** `add_job_log()`
**変更内容:**

```python
# 現在の実装
def add_job_log(job_id: str, message: str, jobs: dict):
    if job_id in jobs:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        sanitized_message = sanitize_log_message(message)
        jobs[job_id]['logs'].append(f"[{timestamp}] {sanitized_message}")

# 改善案
MAX_LOG_ENTRIES = 200  # 最大ログ数

def add_job_log(job_id: str, message: str, jobs: dict):
    if job_id in jobs:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        sanitized_message = sanitize_log_message(message)
        jobs[job_id]['logs'].append(f"[{timestamp}] {sanitized_message}")
        # ログ数制限
        if len(jobs[job_id]['logs']) > MAX_LOG_ENTRIES:
            # 古いログを削除（最新MAX_LOG_ENTRIES件のみ保持）
            jobs[job_id]['logs'] = jobs[job_id]['logs'][-MAX_LOG_ENTRIES:]
```

**期待される効果:**
- ログの蓄積が制限される
- メモリ使用量の削減

**リスク:**
- 低（既存の処理ロジックに影響しない）

#### 7-1-4. メモリ警告閾値の修正

**対象ファイル:** `app.py:27-28`
**変更内容:**

```python
# 現在の実装（問題あり）
MEMORY_LIMIT_MB = int(os.getenv("MEMORY_LIMIT_MB", "450"))
MEMORY_WARNING_MB = int(os.getenv("MEMORY_WARNING_MB", "512"))  # LIMITより大きい

# 改善案
MEMORY_LIMIT_MB = int(os.getenv("MEMORY_LIMIT_MB", "450"))
MEMORY_WARNING_MB = int(os.getenv("MEMORY_WARNING_MB", "400"))  # LIMITより小さい
```

**期待される効果:**
- メモリ警告が適切に機能する

**リスク:**
- 低（設定値の修正のみ）

### 優先度2: 恒久対策（影響: 大、実装コスト: 中、リスク: 中）

#### 7-2-1. メモリ計測の追加

**対象ファイル:** `app.py`, `automation.py`
**変更内容:**

```python
# app.py に追加
def log_memory_usage(tag: str):
    """メモリ使用量をログに記録"""
    try:
        resources = get_system_resources()
        memory_usage_percent = (resources['memory_mb'] / MEMORY_LIMIT_MB) * 100
        logger.info(f"memory_check tag={tag} memory={resources['memory_mb']:.1f}MB/{MEMORY_LIMIT_MB}MB ({memory_usage_percent:.1f}%) jobs={len(jobs)} sessions={len(session_manager['active_sessions'])}")
    except:
        pass

# 重要なポイントで呼び出し
# - ファイルアップロード時
# - ブラウザ起動時
# - Excel読み込み時
# - 処理完了時
```

**期待される効果:**
- メモリ使用量の推移を追跡できる
- 問題の特定が容易になる

**リスク:**
- 低（ログ出力のみ）

#### 7-2-2. ヒープスナップショット取得の仕組み

**対象ファイル:** 新規作成 `utils/memory_profiler.py`
**変更内容:**

```python
import tracemalloc
import gc

def take_memory_snapshot(tag: str):
    """メモリスナップショットを取得"""
    try:
        tracemalloc.start()
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')
        
        logger.info(f"memory_snapshot tag={tag}")
        for index, stat in enumerate(top_stats[:10], 1):
            logger.info(f"  {index}. {stat}")
        
        tracemalloc.stop()
    except:
        pass
```

**期待される効果:**
- メモリ使用量の内訳を確認できる
- 問題の特定が容易になる

**リスク:**
- 低（デバッグ用の機能）

#### 7-2-3. 重い処理をワーカー分離

**対象ファイル:** 新規作成（将来的な改善）
**変更内容:**

- Playwright処理を別プロセスで実行
- メインプロセスとメモリを分離
- プロセス間通信で結果を返す

**期待される効果:**
- メインプロセスのメモリ使用量を削減
- OOMの影響を局所化

**リスク:**
- 高（大規模な変更が必要）
- 実装コストが高い

#### 7-2-4. キュー化

**対象ファイル:** 新規作成（将来的な改善）
**変更内容:**

- ジョブをキューに投入
- ワーカープロセスで順次処理
- メモリ使用量を制御

**期待される効果:**
- 同時実行数を厳密に制御
- メモリ使用量の予測が容易

**リスク:**
- 高（大規模な変更が必要）
- 実装コストが高い

### 優先度3: 暫定対策（影響: 中、実装コスト: 低、リスク: 低）

#### 7-3-1. メモリ上限の引き上げ

**対象ファイル:** `render.yaml`
**変更内容:**

```yaml
# 現在の設定
plan: free  # 512MB

# 改善案（根本原因の特定を前提に）
plan: starter  # 1GB以上
```

**期待される効果:**
- メモリ不足によるOOMを回避
- 一時的な対策として有効

**リスク:**
- 低（設定変更のみ）
- ただし、根本原因の解決にはならない

**注意:**
- 根本原因の特定を前提に扱う
- 長期的な解決策ではない

## 8. 実装に入る前のチェックリスト

- [ ] クラウド側ログを取得し、OOMや再起動の証拠を確認
- [ ] ローカル環境で再現テストを実施
- [ ] メモリ計測を追加し、問題の特定を優先
- [ ] ブラウザインスタンス数の監視を追加
- [ ] jobs辞書のサイズ監視を追加
- [ ] 改善案の優先度1から順に実装
- [ ] 各改善案の実装後に、メモリ使用量の変化を確認
- [ ] 本番環境へのデプロイ前に、ステージング環境でテスト

## 9. 追加で必要な情報と未確定点

### 9.1 追加で必要な情報

1. **クラウド側ログ**
   - 期間: 2026/02/03 00:00-23:59
   - 形式: テキスト
   - 貼り付け先: `diagnostics/render_logs_2026-02-03.txt`
   - 特に確認したい内容:
     - OOMエラー（Out of memory, Killed, exit code 137, SIGKILL）
     - メモリ関連のログ（memory_limit_exceeded, high_memory_usage等）
     - 再起動の記録
     - リクエスト数とタイミング

2. **メモリ使用量の推移データ**
   - Render Dashboardのメトリクス
   - スパイクが発生した時刻
   - ベースラインの推移

3. **同時実行数の実績**
   - スパイク発生時の同時実行ジョブ数
   - セッション数の推移

### 9.2 調査で未確定な点

1. **ブラウザインスタンスの実際のメモリ使用量**
   - 仮説: 100-200MB
   - 確認方法: メモリ計測を追加して実測

2. **jobs辞書に残る古いジョブの数**
   - 仮説: エラー時にジョブが残る
   - 確認方法: jobs辞書のサイズ監視を追加

3. **Excelファイル読み込み時の実際のメモリ使用量**
   - 仮説: ファイルサイズの数倍
   - 確認方法: 読み込み前後のメモリ使用量を計測

4. **セッションクリーンアップの実行率**
   - 仮説: エラー時にクリーンアップが実行されない
   - 確認方法: クリーンアップの実行ログを確認

### 9.3 まずやるべき計測追加の最小セット

1. **ブラウザインスタンス数の監視**
   - 場所: `automation.py:1607` の前後
   - 実装: グローバル変数でカウント、ログに記録

2. **jobs辞書のサイズ監視**
   - 場所: `app.py:675` の前後
   - 実装: `len(jobs)` をログに記録

3. **メモリ使用量の定期ログ**
   - 場所: `app.py:1000-1022` の `monitor_processing_resources()`
   - 実装: より頻繁にログを出力（データ処理ごと）

4. **クリーンアップの実行確認**
   - 場所: `app.py:727-728`
   - 実装: クリーンアップの実行をログに記録

これらの計測を追加することで、次回のインシデント時に原因の特定が容易になります。

---

**レポート作成日時:** 2026/02/03
**作成者:** 調査担当エンジニア
**次回レビュー予定:** クラウド側ログ取得後
