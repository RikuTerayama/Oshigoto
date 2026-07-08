# 本番デプロイ前スモーク検証レポート（証跡付き）

**日付**: 2026-02-10  
**目的**: minutes 削除と CSV/Excel ユーティリティ追加が本番デプロイ前に壊れていないかを事実ベース（証跡付き）で検証する。  
**対象ブランチ**: cleanup/remove-minutes, feature/add-csv-excel-utility, seo/topicality-phase-b

---

## 成果物一覧

| 成果物 | 説明 |
|--------|------|
| scripts/verify_deploy_routes.py | ルート検証（Flask test client または --live で実サーバ）。curl 風の証跡ログを標準出力・オプションでファイルに出力 |
| scripts/verify_deploy_routes.sh | 実サーバ起動後に curl -I で証跡を取得する用（BASE_URL 指定可） |
| scripts/e2e_tools_csv_playwright.py | /tools/csv の CDN ロード・Console・origin への POST/PUT/PATCH なしを Playwright で検証。--output で JSON 証跡 |
| docs/status-reports/2026-02-10_predeploy_smoke_verification.md | 本レポート |

**証跡の取り方（必須）**  
各ブランチで以下を記録した（本レポート「ブランチ別証跡」に貼付済み）。  
- `git rev-parse --abbrev-ref HEAD` / `git rev-parse HEAD`  
- `python -V`（実行環境）  
- `python scripts/verify_deploy_routes.py` の出力（HTTP code と Location の curl 風ログ）  
- 必要に応じて `python scripts/smoke_test.py --deploy` の結果  
- E2E を行う場合は `python scripts/e2e_tools_csv_playwright.py --output evidence_e2e.json` の結果

---

## 再現可能なスモークテスト手順

### 1. ルーティング・301 の証跡（サーバ不要）

```bash
# プロジェクトルートで
python scripts/verify_deploy_routes.py
# 証跡をファイルに追記する場合
python scripts/verify_deploy_routes.py --output evidence_routes.log
```

### 2. ルーティング・301 の証跡（実サーバで curl 風）

```bash
# ターミナル1: サーバ起動
flask run

# ターミナル2: 証跡取得（PowerShell の場合は curl は Invoke-WebRequest のエイリアスのことがあるため、Git Bash または WSL 推奨）
# Linux/macOS/Git Bash:
BASE_URL=http://127.0.0.1:5000 ./scripts/verify_deploy_routes.sh 2>&1 | tee evidence_curl.log
```

または実サーバに対して Python で同様の出力を得る場合:

```bash
python scripts/verify_deploy_routes.py --live http://127.0.0.1:5000 --output evidence_live.log
```

### 3. デプロイ判定用の一括チェック（既存）

```bash
python scripts/smoke_test.py --deploy
```

### 4. /tools/csv の CDN・Console・ファイル送信なし（E2E）

**前提**: Playwright インストール済み（`pip install playwright` 済みかつ `playwright install chromium` 実行済み）、サーバ起動済み。

```bash
# ターミナル1
flask run

# ターミナル2
set BASE_URL=http://127.0.0.1:5000
python scripts/e2e_tools_csv_playwright.py --output evidence_e2e.json
```

**証跡の見方**  
- `globals_ok`: true なら Papa, XLSX, Encoding, JSZip がすべて読み込めている。  
- `origin_mutating_requests`: 空配列なら origin への POST/PUT/PATCH は 0 件。  
- `console_errors`: 未定義エラーなどが含まれると配列に記録される。

### 5. CDN の簡単確認（手動・ブラウザ）

/tools/csv を開いたあと、開発者ツールの Console で次を実行する。`true` なら主要 CDN は読み込めている。

```js
typeof Papa !== 'undefined' && typeof XLSX !== 'undefined' && typeof Encoding !== 'undefined' && typeof JSZip !== 'undefined'
```

### 6. ファイルをサーバに送っていない確認（手動・ブラウザ）

1. /tools/csv を開く。  
2. Network タブを開き、ファイルを 1 つ選択して「実行」まで行う。  
3. 確認: 一覧に **origin への POST/PUT/PATCH が 0 件**であること（あるのは GET の HTML/JS/CSS/CDN のみ）。

---

## ブランチ別証跡

### feature/add-csv-excel-utility

**期待**: /tools/seo, /tools/csv, /guide/csv → 200。 /tools/minutes, /guide/minutes → 301。 /tools/pdf/ → 301。

**証跡（実行日 2026-02-10）**

```
=== deploy route verification evidence ===
git branch: feature/add-csv-excel-utility
git rev: 628eb1dbdb5fb44340c8283904a1fdb056791643
python: 3.14.0

(Flask test client, no server)
$ curl -I http://127.0.0.1:5000/tools/seo
HTTP/1.1 200 OK

  -> OK

$ curl -I http://127.0.0.1:5000/tools/csv
HTTP/1.1 200 OK

  -> OK

$ curl -I http://127.0.0.1:5000/guide/csv
HTTP/1.1 200 OK

  -> OK

$ curl -I http://127.0.0.1:5000/tools/minutes
HTTP/1.1 301 REDIRECT
Location: /tools

  -> OK

$ curl -I http://127.0.0.1:5000/guide/minutes
HTTP/1.1 301 REDIRECT
Location: /guide

  -> OK

$ curl -I http://127.0.0.1:5000/tools/pdf/
HTTP/1.1 301 REDIRECT
Location: /tools/pdf

  -> OK

=== end ===
```

**事実**: 上記のとおり、すべて期待どおり（200/301 と Location）。  
**smoke_test.py --deploy**: 実行結果 `OK: deploy verification (...)`（再実行で再現可能）。

---

### cleanup/remove-minutes

**期待**: minutes は 301。CSV ツールはこのブランチには含まれないため /tools/csv, /guide/csv は 404 が想定。

**証跡（実行日 2026-02-10）**

```
=== deploy route verification evidence ===
git branch: cleanup/remove-minutes
git rev: af8a6a21d8f74b2e611fb4a1b72f5f922aa7d3d7
python: 3.14.0

(Flask test client, no server)
$ curl -I http://127.0.0.1:5000/tools/seo
HTTP/1.1 200 OK

  -> OK

$ curl -I http://127.0.0.1:5000/tools/csv
HTTP/1.1 404

  -> FAIL expected 200

$ curl -I http://127.0.0.1:5000/guide/csv
HTTP/1.1 404

  -> FAIL expected 200

$ curl -I http://127.0.0.1:5000/tools/minutes
HTTP/1.1 301 REDIRECT
Location: /tools

  -> OK

$ curl -I http://127.0.0.1:5000/guide/minutes
HTTP/1.1 301 REDIRECT
Location: /guide

  -> OK

$ curl -I http://127.0.0.1:5000/tools/pdf/
HTTP/1.1 301 REDIRECT
Location: /tools/pdf

  -> OK

=== end ===
```

**事実**: /tools/csv と /guide/csv は 404（このブランチに CSV ツールは未マージのため想定どおり）。/tools/minutes, /guide/minutes は 301、/tools/pdf/ は 301 で期待どおり。

---

### seo/topicality-phase-b

**期待**: このブランチは minutes 削除・CSV ツールのどちらも含まない想定。そのため /tools/minutes, /guide/minutes は 200（旧挙動）、/tools/csv, /guide/csv は 404。

**証跡（実行日 2026-02-10）**

```
=== deploy route verification evidence ===
git branch: seo/topicality-phase-b
git rev: fc44c9e3598eb52237bbea7016bf9eabb2ffc382
python: 3.14.0

(Flask test client, no server)
$ curl -I http://127.0.0.1:5000/tools/seo
HTTP/1.1 200 OK

  -> OK

$ curl -I http://127.0.0.1:5000/tools/csv
HTTP/1.1 404

  -> FAIL expected 200

$ curl -I http://127.0.0.1:5000/guide/csv
HTTP/1.1 404

  -> FAIL expected 200

$ curl -I http://127.0.0.1:5000/tools/minutes
HTTP/1.1 200 OK

  -> FAIL expected 301

$ curl -I http://127.0.0.1:5000/guide/minutes
HTTP/1.1 200 OK

  -> FAIL expected 301

$ curl -I http://127.0.0.1:5000/tools/pdf/
HTTP/1.1 301 REDIRECT
Location: /tools/pdf

  -> OK

=== end ===
```

**事実**: /tools/minutes と /guide/minutes は 200（minutes 削除未マージのため旧挙動）。/tools/csv, /guide/csv は 404。/tools/pdf/ は 301 で期待どおり。

---

## 事実（コード・設定に基づく）

| 項目 | 根拠 |
|------|------|
| /tools/minutes の 301 | app.py に `@app.route('/tools/minutes')` で `redirect('/tools', code=301)` が定義されている（minutes 削除ブランチ・feature ブランチ）。 |
| /guide/minutes の 301 | app.py に `@app.route('/guide/minutes')` で `redirect('/guide', code=301)` が定義されている（同上）。 |
| /tools/pdf/ の 301 | app.py の `normalize_trailing_slash()` が GET/HEAD で末尾スラッシュを canonical に 301 する。 |
| /tools/csv, /guide/csv の有無 | feature/add-csv-excel-utility にルートとテンプレートが存在。cleanup/remove-minutes と seo/topicality-phase-b には存在しない。 |
| ファイルをサーバに送らない | static/js/csv-ops.js および templates/tools/csv.html に fetch / XMLHttpRequest / FormData によるアップロードは 0 件。FileReader と Blob ダウンロードのみ。 |
| CDN の読み込み順 | templates/tools/csv.html で file-validation → file-utils → jszip → zip-utils → PapaParse → SheetJS → encoding-japanese → csv-ops.js。 |

---

## 推測・注意（事実と分離）

- **verify_deploy_routes.py の「FAIL」**: スクリプトは「本番デプロイ後」の期待値（CSV 200・minutes 301）で判定している。cleanup/remove-minutes では CSV は存在しないため 404 で FAIL になるが、ブランチの内容としては正しい。seo/topicality-phase-b では minutes がまだ 200 のため 301 期待で FAIL になる。  
- **E2E**: Playwright が未インストールまたはサーバ未起動の環境では実行できない。証跡が必要な場合は、手動で「CDN の簡単確認」と「Network で POST/PUT/PATCH 0 件」を実施する。  
- **CSP**: 本レポート時点で CSP により CDN がブロックされている設定は未確認。本番で CSP を導入する場合は cdnjs / sheetjs / jsdelivr を script-src に含める必要がある。

---

## 修正の有無

今回の検証では、**コードの不具合修正は行っていない**。  
- feature/add-csv-excel-utility: ルート・301・CSV はすべて期待どおり。  
- cleanup/remove-minutes: minutes 301 は期待どおり。CSV は未実装のため 404 は想定どおり。  
- seo/topicality-phase-b: minutes 削除・CSV 未マージのため、現状の 200/404 はブランチ内容と一致。

今後、本番デプロイ前にマージ順が変わった場合は、再度 `python scripts/verify_deploy_routes.py` および必要に応じて E2E を実行し、証跡を本レポートに追記することを推奨する。
