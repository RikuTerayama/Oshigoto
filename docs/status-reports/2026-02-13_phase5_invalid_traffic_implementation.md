# Phase 5: 無効トラフィック対策 実装ログ（2026-02-13）

## 目的
AdSense 承認後の無効トラ事故を「止められる」「見える」「守れる」状態にする。

## 実装内容

### A) 緊急停止: ADSENSE_ENABLED を効かせる
- **変更**: `templates/includes/head_meta.html` の AdSense script（adsbygoogle.js）を `{% if ADSENSE_ENABLED %} ... {% endif %}` で囲んだ。
- **効果**: 本番で `ADSENSE_ENABLED=false` にすると広告スクリプトが読み込まれず、view-source に adsbygoogle.js が出ない。
- **確認**: 環境変数 `ADSENSE_ENABLED` は app.py の `inject_env_vars` で既にテンプレに渡している（変更なし）。

### B) 実 IP / UA / Referer ログ
- **採用方式**: **ProxyFix**（werkzeug.middleware.proxy_fix.ProxyFix）。Render 等の単段プロキシ前提で `x_for=1, x_proto=1, x_host=1` を指定し、`request.remote_addr` を実クライアント IP に正す。
- **理由**: 実 IP をアプリ全体で一貫して使えるため、ログ・レート制限のキーにそのまま使える。ProxyFix を使わずログ用だけ X-Forwarded-For を読む方式も可能だが、今回は安全性重視で ProxyFix を採用。
- **変更**:
  - app.py: `ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)` を app 初期化直後に追加。
  - req_start ログに `ua=` と `ref=` を追加（各 200 文字で打ち切り）。req_end は従来どおり status/ms のみ（肥大化回避）。
- **効果**: 通常リクエストで req_start に ip, ua, ref が残る。ヘルス系は従来どおりログ抑制。

### C) レート制限（インメモリ固定窓）
- **対象**: `/upload`（10 req/1min/IP）, `/status/*`（120 req/1min/IP）, `/api/*`（60 req/1min/IP）。`/api/seo/crawl-urls` は既存の 1/min 制限に任せ、当制限では除外。
- **除外**: `/healthz`, `/livez`, `/readyz`, `/ping`, `/health`, `/ready`, `/static/*`, `/robots.txt`, `/sitemap.xml`, `/ads.txt`。
- **変更**: app.py に `RateLimiter` クラス（固定窓）と `rate_limit_check` の before_request を追加。超過時は 429 + JSON + Retry-After ヘッダ。
- **定数**: `_RATE_LIMITS = {'upload': 10, 'status': 120, 'api': 60}`。調整する場合は app.py の当該定数を変更。

### D) 検証スクリプト
- **追加**: `scripts/verify_rate_limit.py`。Flask test client で (1) /upload 11回 POST → 11回目 429、(2) /status/fake-id 121回 GET → 121回目 429、(3) /healthz 50回 GET → 全て 200、(4) /api/seo/crawl-urls 2回 POST → 2回目 429（既存制限）を確認。

### E) ドキュメント
- 本ファイル（Phase 5 実装ログ）。
- `docs/incident_runbook.md`（緊急遮断手順）。

## 環境変数で止めるもの
| 環境変数 | 効果 |
|----------|------|
| ADSENSE_ENABLED=false | 広告スクリプトを読み込まない（緊急で広告だけ止める） |

## 検証コマンド
- `python scripts/verify_rate_limit.py` … レート制限の動作確認
- `python scripts/smoke_test.py --deploy` … 既存デプロイ検証
- `python scripts/verify_deploy_routes.py` … ルート検証
