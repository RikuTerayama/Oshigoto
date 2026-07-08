# Jobcan Automation メモリ最適化・軽量化 現状分析レポート

**作成日**: 2026-02-03  
**対象**: jobcan-automation (Flask + Jinja2)  
**目的**: Render上でのOOM（Out of Memory）によるサービス停止を避けるため、メモリ消費要因を特定し、改善候補を整理

---

## 1. 結論（OOMの主因候補トップ3）

### 🥇 **主因1: Playwrightブラウザインスタンスのメモリ消費（確度: 高）**

**推定メモリ消費**: 100-200MB/インスタンス  
**発生箇所**: `automation.py:1568-1979` (process_jobcan_automation関数内)

**問題点**:
- 1つのブラウザインスタンスで100-200MBを消費
- エラー時に`browser.close()`が確実に実行されない可能性
- `with sync_playwright() as p:`のコンテキスト内でエラーが発生した場合、finallyブロックの外で`browser.close()`が呼ばれる可能性
- 現在の設定: `MAX_ACTIVE_SESSIONS=1`（同時1セッションのみ）だが、ブラウザが適切にクリーンアップされないとメモリが蓄積

**根拠**:
- `render.yaml:44-45`: `MAX_ACTIVE_SESSIONS=1`（free plan 512MBで安定化）
- `automation.py:1568`: `with sync_playwright() as p:`でブラウザ起動
- `docs/memory-incident-report_2026-02-03.md:101-105`: ブラウザインスタンスのメモリ消費が確認されている

---

### 🥈 **主因2: Excelファイルのメモリ読み込み（確度: 中）**

**推定メモリ消費**: ファイルサイズの3-5倍（10MBファイル → 30-50MB）  
**発生箇所**: `utils.py:546-582` (load_excel_data関数)

**問題点**:
- `pandas.read_excel()`または`openpyxl.load_workbook()`で全データをメモリに読み込む
- ストリーミング処理ではなく、全データを一度に読み込む
- 10MB制限のExcelファイルでも、pandas/openpyxlがメモリ上に展開すると数倍のメモリを消費

**根拠**:
- `utils.py:552`: `data = pd.read_excel(file_path)`（全データをメモリに読み込む）
- `utils.py:559`: `wb = load_workbook(file_path)`（ワークブック全体をメモリに読み込む）
- `docs/memory-incident-report_2026-02-03.md:107-127`: Excelファイルのメモリ読み込みが問題として指摘されている

---

### 🥉 **主因3: ジョブログとグローバル辞書の蓄積（確度: 中）**

**推定メモリ消費**: 1ジョブあたり数MB（ログが数百行の場合）  
**発生箇所**: `app.py:156-157` (jobs辞書), `app.py:795-813` (ジョブ初期化)

**問題点**:
- `jobs[job_id]['logs']`が無制限に蓄積される
- 古いジョブがjobs辞書から削除されない場合、ログが蓄積され続ける
- 1ジョブあたり数百行のログが蓄積される可能性
- クリーンアップ処理（`prune_old_jobs()`）は30分保持期間後に実行されるが、エラー時に確実に実行されるか不明

**根拠**:
- `app.py:797`: `'logs': []`（ログが無制限に追加される）
- `app.py:159-160`: `JOB_RETENTION_SECONDS = 1800`（30分保持）
- `app.py:270-324`: `prune_old_jobs()`関数で古いジョブを削除
- `docs/memory-incident-report_2026-02-03.md:144-164`: ログの蓄積が問題として指摘されている

---

## 2. 現状（デプロイ構成・ワーカー・メモリ制限推定）

### 2.1 Render向け設定

**ファイル**: `render.yaml`

```yaml
plan: free  # 512MB RAM
envVars:
  - WEB_CONCURRENCY: "1"  # workers数（free plan 512MBで安定化）
  - WEB_THREADS: "1"  # スレッド数（メモリ節約）
  - WEB_TIMEOUT: "180"  # タイムアウト3分
  - WEB_MAX_REQUESTS: "500"  # メモリリーク対策
  - MEMORY_LIMIT_MB: "450"  # OOM前に警告
  - MEMORY_WARNING_MB: "400"  # LIMITより小さい値
  - MAX_ACTIVE_SESSIONS: "1"  # 同時接続数制限
  - MAX_FILE_SIZE_MB: "10"  # ファイルサイズ制限
```

**推定メモリ内訳**:
- ベース（Flask + Gunicorn）: 60-100MB
- 1ブラウザインスタンス: 100-200MB
- Excel読み込み（10MBファイル）: 30-50MB
- ジョブログ・セッション管理: 10-20MB
- **合計**: 200-370MB（安全マージン: 80-150MB）

---

### 2.2 Gunicorn設定

**ファイル**: `Dockerfile:63-78`

```bash
CMD gunicorn --bind 0.0.0.0:$PORT \
  --workers ${WEB_CONCURRENCY:-2} \
  --threads ${WEB_THREADS:-2} \
  --timeout ${WEB_TIMEOUT:-180} \
  --max-requests ${WEB_MAX_REQUESTS:-500} \
  --max-requests-jitter ${WEB_MAX_REQUESTS_JITTER:-50} \
  app:app
```

**現在の設定**:
- `workers=1`: 1ワーカーのみ（メモリ節約）
- `threads=1`: 1スレッドのみ（メモリ節約）
- `max-requests=500`: 500リクエスト後にワーカー再起動（メモリリーク対策）
- `timeout=180`: 3分タイムアウト（Jobcan処理用）

---

### 2.3 Python依存関係

**ファイル**: `requirements.txt`

```
Flask==2.3.3
openpyxl==3.1.2
playwright==1.40.0
jpholiday==1.0.2
psutil==5.9.8
gunicorn==21.2.0
```

**メモリ消費の大きい依存**:
- `playwright==1.40.0`: ブラウザインスタンスで100-200MB/インスタンス
- `openpyxl==3.1.2`: Excel読み込みでファイルサイズの3-5倍
- `pandas`（オプション）: 同様にメモリ消費が大きい

---

## 3. ホットスポット一覧（ファイル/関数/根拠）

### 3.1 ブラウザ関連

| ファイル | 関数/行 | 問題 | 推定メモリ消費 | リスク |
|---------|---------|------|---------------|--------|
| `automation.py:1568` | `with sync_playwright() as p:` | ブラウザインスタンス起動 | 100-200MB/インスタンス | 高 |
| `automation.py:1600-1650` | ブラウザ起動オプション | メモリ最適化オプションあり | - | 中 |
| `automation.py:1653` | `browser = p.chromium.launch()` | ブラウザ起動 | 100-200MB | 高 |
| `automation.py:1979` | `browser.close()` | クリーンアップ（エラー時に未実行の可能性） | - | 高 |

**改善候補**:
- `finally`ブロックで確実に`browser.close()`を実行
- ブラウザ起動オプションの最適化（`--disable-dev-shm-usage`等は既に設定済み）
- エラー時の確実なクリーンアップ

---

### 3.2 Excel読み込み関連

| ファイル | 関数/行 | 問題 | 推定メモリ消費 | リスク |
|---------|---------|------|---------------|--------|
| `utils.py:552` | `pd.read_excel(file_path)` | 全データをメモリに読み込む | ファイルサイズ×3-5倍 | 中 |
| `utils.py:559` | `load_workbook(file_path)` | ワークブック全体をメモリに読み込む | ファイルサイズ×3-5倍 | 中 |
| `automation.py:1488` | `load_excel_data(file_path)` | Excel読み込み呼び出し | 30-50MB（10MBファイル） | 中 |

**改善候補**:
- ストリーミング処理（`openpyxl`の`read_only=True`モード）
- チャンク読み込み（pandasの`chunksize`パラメータ）
- 処理完了後の明示的なメモリ解放（`del data_source`）

---

### 3.3 ジョブ管理関連

| ファイル | 関数/行 | 問題 | 推定メモリ消費 | リスク |
|---------|---------|------|---------------|--------|
| `app.py:156-157` | `jobs = {}` | グローバル辞書 | 1ジョブあたり数MB | 中 |
| `app.py:797` | `'logs': []` | ログが無制限に蓄積 | 数百行で数MB | 中 |
| `app.py:270-324` | `prune_old_jobs()` | 30分保持後に削除 | - | 低 |
| `app.py:163-172` | `session_manager` | セッション管理 | 1セッションあたり数KB | 低 |

**改善候補**:
- ログの上限設定（例: 最大1000行）
- 古いログの自動削除（例: 100行を超えたら古いログを削除）
- ジョブ保持期間の短縮（30分 → 10分）

---

### 3.4 ファイルアップロード関連

| ファイル | 関数/行 | 問題 | 推定メモリ消費 | リスク |
|---------|---------|------|---------------|--------|
| `app.py:741` | `file = request.files['file']` | Flaskのファイルオブジェクト | ファイルサイズ分 | 低 |
| `app.py:781` | `file.save(file_path)` | ディスクに保存 | - | 低 |

**改善候補**:
- ストリーミング保存（既に実装済み）
- ファイルサイズ制限の厳格化（10MB → 5MB）

---

## 4. 再現手順（ローカルで負荷をかける方法、計測方法）

### 4.1 メモリ計測エンドポイント

**エンドポイント**: `/health/memory`（DEBUG時のみ有効）

**使用方法**:
```bash
# ローカルサーバー起動
python app.py

# 別ターミナルでメモリ計測
curl http://localhost:5000/health/memory | jq
```

**レスポンス例**:
```json
{
  "status": "ok",
  "timestamp": "2026-02-03T12:00:00",
  "process_memory": {
    "rss_mb": 120.5,
    "vms_mb": 250.3,
    "percent": 23.5
  },
  "system_memory": {
    "total_mb": 8192.0,
    "available_mb": 6000.0,
    "used_mb": 2192.0,
    "percent": 26.7
  },
  "limits": {
    "memory_limit_mb": 450,
    "memory_warning_mb": 400,
    "max_file_size_mb": 10,
    "max_active_sessions": 1
  },
  "resources": {
    "jobs_count": 2,
    "jobs_by_status": {
      "running": 1,
      "completed": 1
    },
    "sessions_count": 1,
    "browser_count": 1
  }
}
```

---

### 4.2 ログベースのメモリ計測

**既存のメモリ計測ログ**: `diagnostics/runtime_metrics.py:67-122`

**ログ形式**:
```
memory_check tag=upload_done rss_mb=120.5 jobs_count=2 sessions_count=1 browser_count=0 env_WEB_CONCURRENCY=1 env_WEB_THREADS=1 env_MAX_ACTIVE_SESSIONS=1 env_MEMORY_LIMIT_MB=450 env_MEMORY_WARNING_MB=400 job_id=xxx session_id=yyy
```

**計測ポイント**:
- `upload_done`: ファイルアップロード直後
- `excel_before`: Excel読み込み前
- `excel_after`: Excel読み込み後
- `browser_before`: ブラウザ起動前
- `browser_after`: ブラウザ起動後
- `prune_jobs_before`: ジョブ削除前
- `prune_jobs_after`: ジョブ削除後

**ログ解析コマンド**:
```bash
# Renderログからメモリ計測ログを抽出
grep "memory_check" render.log | tail -20

# メモリ使用量の推移を確認
grep "memory_check" render.log | awk '{print $3}' | cut -d= -f2
```

---

### 4.3 ローカル負荷テスト

**手順**:
1. ローカルサーバー起動
2. 10MBのExcelファイルをアップロード
3. `/health/memory`でメモリ計測
4. ブラウザ起動後のメモリ計測
5. 処理完了後のメモリ計測

**スクリプト例** (`scripts/test_memory.sh`):
```bash
#!/bin/bash
# メモリ計測テストスクリプト

BASE_URL="http://localhost:5000"

echo "=== 初期状態 ==="
curl -s "$BASE_URL/health/memory" | jq '.process_memory.rss_mb'

echo "=== ファイルアップロード後 ==="
curl -s -X POST \
  -F "file=@test.xlsx" \
  -F "email=test@example.com" \
  -F "password=test" \
  -F "company_id=test" \
  "$BASE_URL/upload" > /dev/null

sleep 2
curl -s "$BASE_URL/health/memory" | jq '.process_memory.rss_mb'

echo "=== ブラウザ起動後 ==="
sleep 10
curl -s "$BASE_URL/health/memory" | jq '.process_memory.rss_mb'
```

---

### 4.4 Python tracemalloc（開発用）

**スクリプト例** (`scripts/trace_memory.py`):
```python
import tracemalloc
import time
from app import app

tracemalloc.start()

# 処理前のスナップショット
snapshot1 = tracemalloc.take_snapshot()
top_stats1 = snapshot1.statistics('lineno')

# テスト処理実行
with app.test_client() as client:
    # ファイルアップロード
    with open('test.xlsx', 'rb') as f:
        client.post('/upload', data={
            'file': f,
            'email': 'test@example.com',
            'password': 'test',
            'company_id': 'test'
        })

# 処理後のスナップショット
snapshot2 = tracemalloc.take_snapshot()
top_stats2 = snapshot2.statistics('lineno')

# 差分を表示
for stat in top_stats2[:10]:
    print(stat)
```

**実行方法**:
```bash
python scripts/trace_memory.py
```

**注意**: tracemallocは本番環境では使用しない（パフォーマンス影響あり）

---

## 5. 改善案（P0/P1/P2）

### P0: 設定で効く（即効性が高い、リスク低）

#### P0-1: Gunicornワーカー調整（既に最適化済み）

**現状**: `WEB_CONCURRENCY=1`, `WEB_THREADS=1`  
**効果**: メモリ使用量を最小化  
**リスク**: 低（既に設定済み）  
**実装コスト**: 小（設定変更のみ）  
**影響範囲**: 全体

---

#### P0-2: max-requestsの調整（既に設定済み）

**現状**: `WEB_MAX_REQUESTS=500`  
**効果**: メモリリーク対策（500リクエスト後にワーカー再起動）  
**リスク**: 低（既に設定済み）  
**実装コスト**: 小（設定変更のみ）  
**影響範囲**: 全体

**推奨**: 300-500の範囲で調整（メモリリークの発生頻度に応じて）

---

#### P0-3: ログ抑制

**現状**: ログが無制限に出力される  
**効果**: ログバッファのメモリ消費を削減  
**リスク**: 低（ログレベル調整のみ）  
**実装コスト**: 小（設定変更のみ）  
**影響範囲**: 全体

**推奨**:
- 本番環境: `WEB_LOG_LEVEL=warning`（INFOログを抑制）
- 開発環境: `WEB_LOG_LEVEL=info`（現状維持）

---

### P1: コード修正で効く（効果大、リスク中）

#### P1-1: ブラウザクリーンアップの確実化

**現状**: エラー時に`browser.close()`が確実に実行されない可能性  
**効果**: ブラウザインスタンスのメモリリークを防止（100-200MB削減）  
**リスク**: 中（エラーハンドリングの変更）  
**実装コスト**: 中（try-finallyブロックの追加）  
**影響範囲**: `automation.py:1568-1979`

**実装案**:
```python
browser = None
context = None
page = None

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(...)
        # ... 処理 ...
except Exception as e:
    # エラーハンドリング
    pass
finally:
    # 確実にクリーンアップ
    if page:
        try:
            page.close()
        except:
            pass
    if context:
        try:
            context.close()
        except:
            pass
    if browser:
        try:
            browser.close()
        except:
            pass
```

---

#### P1-2: Excel読み込みのストリーミング化

**現状**: 全データをメモリに読み込む  
**効果**: Excel読み込み時のメモリ消費を削減（30-50MB → 10-20MB）  
**リスク**: 中（処理ロジックの変更）  
**実装コスト**: 中（ストリーミング処理の実装）  
**影響範囲**: `utils.py:546-582`, `automation.py:1488`

**実装案**:
```python
def load_excel_data(file_path):
    if openpyxl_available:
        from openpyxl import load_workbook
        # read_onlyモードでストリーミング読み込み
        wb = load_workbook(file_path, read_only=True)
        ws = wb.active
        
        # 行ごとに処理（メモリ効率的）
        valid_rows = 0
        for row in ws.iter_rows(min_row=2, values_only=True):
            # 処理...
            valid_rows += 1
        
        return wb, valid_rows
```

---

#### P1-3: ジョブログの上限設定

**現状**: ログが無制限に蓄積される  
**効果**: ジョブログのメモリ消費を削減（数MB削減）  
**リスク**: 低（ログ上限の追加のみ）  
**実装コスト**: 小（上限チェックの追加）  
**影響範囲**: `app.py:797`, `utils.py:330-335` (add_job_log関数)

**実装案**:
```python
MAX_JOB_LOGS = 1000  # 最大ログ行数

def add_job_log(job_id: str, message: str, jobs: dict):
    if job_id in jobs:
        logs = jobs[job_id].get('logs', [])
        logs.append(f"[{timestamp}] {sanitized_message}")
        
        # 上限を超えたら古いログを削除
        if len(logs) > MAX_JOB_LOGS:
            jobs[job_id]['logs'] = logs[-MAX_JOB_LOGS:]
```

---

#### P1-4: ジョブ保持期間の短縮

**現状**: 30分保持  
**効果**: 古いジョブのメモリ消費を削減  
**リスク**: 低（保持期間の短縮のみ）  
**実装コスト**: 小（設定変更のみ）  
**影響範囲**: `app.py:159-160`

**実装案**:
```python
JOB_RETENTION_SECONDS = 600  # 30分 → 10分
```

---

### P2: 構造改善（効果大、リスク高、コスト大）

#### P2-1: ジョブキュー化（Celery等）

**現状**: バックグラウンドスレッドで処理  
**効果**: メモリ使用量の制御、スケーラビリティ向上  
**リスク**: 高（アーキテクチャ変更）  
**実装コスト**: 大（ジョブキューの導入、ワーカー分離）  
**影響範囲**: 全体

**推奨**: 中長期の改善案として検討

---

#### P2-2: ブラウザ処理の外部化（Browserless等）

**現状**: Playwrightを同一プロセスで実行  
**効果**: ブラウザインスタンスのメモリ消費を分離  
**リスク**: 高（外部サービスの依存）  
**実装コスト**: 大（外部サービスの導入、API変更）  
**影響範囲**: `automation.py`

**推奨**: 中長期の改善案として検討

---

#### P2-3: ブラウザ内ツールへの移管

**現状**: 一部ツールはブラウザ内処理（画像変換、PDF処理等）  
**効果**: サーバー側のメモリ消費を削減  
**リスク**: 低（既に実装済み）  
**実装コスト**: 小（既存ツールの活用）  
**影響範囲**: 新規ツール開発時

**推奨**: 新規ツール開発時はブラウザ内処理を優先

---

## 6. 次アクション（ChatGPTに渡すための前提情報）

### 6.1 発生条件

- **環境**: Render free plan（512MB RAM）
- **発生タイミング**: 
  - ブラウザインスタンス起動時（100-200MB消費）
  - Excelファイル読み込み時（30-50MB消費）
  - 長時間稼働時（メモリリークの蓄積）
- **発生頻度**: 不定期（メモリ使用量が450MBを超えた場合）

---

### 6.2 ログ

**メモリ計測ログ**:
```
memory_check tag=upload_done rss_mb=120.5 jobs_count=2 sessions_count=1 browser_count=0 env_WEB_CONCURRENCY=1 env_WEB_THREADS=1 env_MAX_ACTIVE_SESSIONS=1 env_MEMORY_LIMIT_MB=450 env_MEMORY_WARNING_MB=400 job_id=xxx session_id=yyy
```

**OOM関連ログ**:
- Renderログで`killed`, `OOM`, `exit status 137`を検索
- メモリ警告: `high_memory_usage memory_mb=XXX warning_threshold=400`
- メモリ超過: `memory_limit_exceeded memory_mb=XXX limit=450`

---

### 6.3 対象機能

- **Jobcan自動入力** (`/upload`): ブラウザインスタンス + Excel読み込み
- **その他ツール**: ブラウザ内処理（サーバー側メモリ影響なし）

---

### 6.4 優先順位

1. **P0**: 設定調整（即効性が高い、リスク低）
   - ログ抑制（`WEB_LOG_LEVEL=warning`）
   - `max-requests`の調整（300-500の範囲）

2. **P1**: コード修正（効果大、リスク中）
   - ブラウザクリーンアップの確実化（最優先）
   - Excel読み込みのストリーミング化
   - ジョブログの上限設定
   - ジョブ保持期間の短縮

3. **P2**: 構造改善（中長期）
   - ジョブキュー化
   - ブラウザ処理の外部化

---

### 6.5 計測方法

- **エンドポイント**: `/health/memory`（ローカル/ステージング環境）
- **ログ**: `memory_check`タグでメモリ計測ログを確認
- **Renderログ**: `killed`, `OOM`, `exit status 137`を検索

---

## 7. ブラウザ内ツールの影響評価

### 7.1 サーバー側でのファイル受信

**確認結果**: ブラウザ内ツール（画像変換、PDF処理等）はサーバー側でファイルを受けていない

**根拠**:
- `templates/tools/*.html`: クライアント側で処理（`ToolRunner`クラス使用）
- サーバー側のルーティング: `/tools/*`は静的ページのみ（ファイルアップロードなし）

**結論**: ブラウザ内ツールはサーバー側メモリに影響しない

---

### 7.2 テンプレートの巨大インラインJS/JSON

**確認結果**: テンプレートに巨大なインラインJS/JSONは埋め込まれていない

**根拠**:
- `templates/tools/*.html`: 外部JSファイル（`static/js/*.js`）を使用
- インラインJS: 最小限（初期化コードのみ）

**結論**: テンプレートのレスポンス肥大によるメモリ圧迫のリスクは低い

---

### 7.3 静的アセットの配信

**確認結果**: 静的アセットはFlaskの`static`フォルダから配信

**根拠**:
- `static/`: CSS、JS、画像ファイル
- Flaskの静的ファイル配信: メモリ効率的（ストリーミング配信）

**結論**: 静的アセットの配信によるメモリ圧迫のリスクは低い

---

## 8. 追加情報

### 8.1 メモリ計測用スクリプト

**ファイル**: `scripts/test_memory.sh`（作成予定）

**用途**: ローカル環境でメモリ使用量を計測

---

### 8.2 メモリホットスポットCSV

**ファイル**: `report/memory_hotspots.csv`（作成予定）

**用途**: 疑わしいホットスポット一覧をCSV形式で出力

---

## 9. 参考資料

- `docs/memory-incident-report_2026-02-03.md`: メモリインシデントレポート
- `docs/memory-mitigation.md`: メモリ対策ドキュメント
- `docs/memory-mitigation-summary.md`: メモリ対策サマリー
- `SRE_RUNBOOK.md`: SRE運用マニュアル

---

**レポート作成者**: Cursor AI  
**最終更新**: 2026-02-03
