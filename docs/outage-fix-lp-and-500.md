# LP劣化表示・/autofill等500 根本原因と恒久対応

## 現象（ユーザー報告）

1. **LP（/）**: 「⚠️ 一時的な表示の問題 / 製品情報の読み込みに問題が発生しています…」が続くことがある  
2. **/autofill, /tools, /about**: 「⚠️ エラーが発生しました / 予期しないエラー…」＋ エラーID（例: 20ef79da）で 500

## 根本原因（特定結果）

### 1. /autofill, /tools, /about が 500 になる原因

- **TemplateAssertionError: block 'og_title' defined twice**
- **場所**: `templates/includes/head_meta.html`（Twitter Card 内で `{% block twitter_title %}{% block og_title %}...` と `og_title` を二重定義していた）
- **経路**: これらのページは `{% include 'includes/head_meta.html' %}` を使用。include されたテンプレート内で同一 block 名を二度定義すると Jinja2 がエラーを出す。

### 2. LP で製品一覧が空／劣化表示になる原因

- **製品一覧の取得経路**: 従来は `context_processor` と `index()` の両方で `from lib.routes import PRODUCTS` に依存。
- **リスク**: `lib.routes` に将来重い import が入ると、context_processor の失敗 → 全ページで `products=[]` または 500。また、失敗時に「なぜ空になったか」がログに残りにくい設計だった。

## 実施した修正

### A. 製品カタログの分離（products が空になる根本対策）

| ファイル | 変更内容 |
|----------|----------|
| **lib/products_catalog.py**（新規） | 外部依存のない製品一覧のみを定義。import なし。 |
| **lib/routes.py** | `PRODUCTS` を `from lib.products_catalog import PRODUCTS` に変更。 |
| **app.py** | `context_processor`・`index()`・`tools_index()`・`validate_startup()` で `lib.products_catalog` を参照。空になった場合は `products_empty_reason` / `landing_page_products_empty` / `tools_page_products_empty` で理由をログに記録。 |

### B. /autofill 等 500 の解消（テンプレート修正）

| ファイル | 変更内容 |
|----------|----------|
| **templates/includes/head_meta.html** | Twitter Card 内の `{% block twitter_title %}{% block og_title %}...` を廃止。`twitter_title` / `twitter_description` を単一 block にし、同一テンプレ内で block の二重定義を防止。 |

### C. エラーログ・追跡の強化（既存＋微修正）

- **500/Exception ハンドラ**: 既に `logger.exception`・`error_id`・`X-Error-Id` を実装済み。
- **503 ハンドラ**: `logger.exception` でスタックトレースを出すように変更。path/method は取得できない場合に備えて try/except。
- **context_processor 失敗時**: ログに `products_empty_reason` と例外型・メッセージ・traceback を出力。

### D. テンプレートの安全化

| ファイル | 変更内容 |
|----------|----------|
| **templates/includes/structured_data.html** | Breadcrumb 用の `request.path` を、`request is defined and request` を確認した上で `request.path\|default('/')` に一本化。 |

### E. 再発防止

- **scripts/smoke_test.py**: `/`, `/autofill`, `/about`, `/tools`, `/healthz` を各10回取得し、全て 200 かつ本文に「⚠️ エラーが発生しました」が含まれないことを確認。
- **tests/test_index_page.py**: `test_about_returns_200`, `test_healthz_returns_200`, `test_smoke_multiple_requests_200` を追加。

## 変更ファイル一覧

- `lib/products_catalog.py`（新規）
- `lib/routes.py`
- `app.py`（context_processor, index, tools_index, validate_startup, errorhandler(503)）
- `templates/includes/head_meta.html`
- `templates/includes/structured_data.html`
- `tests/test_index_page.py`
- `scripts/smoke_test.py`（新規）
- `docs/outage-fix-lp-and-500.md`（本ドキュメント）

## 検証コマンドと結果

```powershell
# スモークテスト（Flask test client）
python scripts/smoke_test.py
# 期待: OK: 5 paths x 10 requests = all 200, no error page

# pytest
python -m pytest tests/test_index_page.py -v
# 期待: 8 passed
```

## Render 上での確認ポイント

1. **エラーIDからログを追う**  
   ユーザーからエラーID（例: 20ef79da）を受け取ったら、Render のログで次を検索:
   - `error_id=20ef79da` または `X-Error-Id: 20ef79da`
   - 同じ行付近に `logger.exception` によるスタックトレースが出ていることを確認。

2. **LP で製品が空になる場合**  
   ログで以下を検索:
   - `context_processor_error` … context_processor で例外（products が空になる原因）
   - `landing_page_products_empty` … index() で products 取得失敗
   - `products_empty_reason` … 例外型とメッセージ

3. **ヘルスチェック**  
   - `GET /healthz` が 200 であること（外部依存なしで常に 200 を返す設計）。

## 再発しない理由の要約

- **製品一覧**: `lib.products_catalog` のみに依存し、重い import の影響を受けない。失敗時は必ずログに理由を残す。
- **/autofill 等 500**: `head_meta.html` の block 二重定義をやめ、include 時も TemplateAssertionError が発生しないようにした。
- **追跡**: 500/503/未処理例外では `error_id` とスタックトレースを必ずログに出すため、次回同様の事象でもエラーIDから原因を特定できる。
