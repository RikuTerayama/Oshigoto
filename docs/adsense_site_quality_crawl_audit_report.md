# AdSense審査向け「サイト品質・必須要素・クロール到達性」監査レポート

**作成日**: 2026-02-24  
**対象**: 本リポジトリ（Flask サイト）  
**目的**: AdSenseのサイト審査で落ちやすい要因を、コード・ルーティング・コンテンツ・メタ情報・クロール到達性の観点で特定し、修正方針を作るための現状分析（実装は行わない）

---

## 0. 事前確認（ツール・前提の把握）

| 項目 | 結果 |
|------|------|
| **フレームワーク** | **Flask（Python）**。Next.js ではない。ルーティングは `app.py` の `@app.route` で定義。 |
| **package.json** | 存在する。用途は **開発用**（lint:html, audit:ui, report:content 等）。パッケージマネージャは npm（devDependencies に html-validate, ts-node, typescript）。本番ビルドは Python/Gunicorn。 |
| **ルーティング方式** | **app/ も pages/ も存在しない**。全ページは `app.py` のルート定義と `templates/` の Jinja2 テンプレートで構成。 |
| **主要機能** | Jobcan 勤怠自動入力（/autofill）、ツール一覧（/tools）、画像一括変換・PDF・画像ユーティリティ・SEO・CSV/Excel ツール、ガイド群、ブログ、事例、FAQ・用語集・ベストプラクティス・法務ページ。 |
| **主要ディレクトリ** | `app.py`（ルート・API・sitemap/robots）、`templates/`（各ページ＋includes）、`static/`（CSS/JS/robots.txt）、`lib/`（products_catalog, nav, routes）。 |
| **環境変数** | README.md に記載。`BASE_URL`, `ADSENSE_ENABLED`, `GA_MEASUREMENT_ID`, `GSC_VERIFICATION_CONTENT` 等。`.env` / `.env.example` はリポジトリ内に存在しない（.gitignore で除外されている可能性あり）。本番は Render 等で環境変数設定を想定。 |

---

## A. 結論サマリ（P0：AdSense申請前に直すべき順・最大7件）

1. **プライバシーポリシーと実装の整合**（広告配信・データ処理の記載を現状に合わせる）— 既存監査で指摘済み。第8項の「今後配信予定」と現 AdSense 配信の乖離、第4項と AutoFill サーバー処理の整合。
2. **必須ページの導線**：About / Contact / Privacy / Terms はフッター・ナビから到達可。**ベストプラクティス**はフッター・グローバルナビにリンクが無く、sitemap.html や本文リンクからのみ。重要ページの孤立リスク。
3. **404・クロール未登録**：/best-practices の 404 は末尾スラッシュ正規化と preflight で対策済み。クロール済み未登録 5 件（/, /privacy, /blog, /glossary, /guide/excel-format）向けに内部リンク・冒頭説明の強化は実施済み。
4. **問い合わせ・運営者情報**：Contact/About の GitHub リンクがプレースホルダーでないか（既存監査で RikuTerayama/jobcan_automation に修正済みの想定）。実体確認推奨。
5. **ツールページの「薄い」印象**：入力UIが主で、初期 HTML の説明文が短いツールがある。手順・FAQ・注意点は各ツール・ガイドで補完されているが、ツール単体で「何ができるか・手順・出力例」が一覧しやすいブロックがあるとより安全。
6. **事例3件の同型性**：case-study 3 ページは構造が非常に類似。重複・薄い判定のリスクは中。差別化された本文量があるか要確認。
7. **広告・アフィリエイト表記**：将来の PR 表記拡張余地は Privacy/Terms に一文追記可能。現状不足の指摘は不要とする。

---

## B. URLマップ（カテゴリ別・重要ページは ★）

### ツール系（入力UI中心）

| URL | テンプレート | 備考 |
|-----|-------------|------|
| / | landing.html | ★ LP |
| /autofill | autofill.html | ★ メインツール |
| /tools | tools/index.html | ★ ツール一覧 |
| /tools/image-batch | tools/image-batch.html | |
| /tools/pdf | tools/pdf.html | |
| /tools/image-cleanup | tools/image-cleanup.html | |
| /tools/seo | tools/seo.html | |
| /tools/csv | tools/csv.html | |
| /tools/minutes | （301 → /tools） | リダイレクトのみ |

### 記事・ブログ・ガイド系

| URL | テンプレート | 備考 |
|-----|-------------|------|
| /blog | blog/index.html | ★ ブログ一覧 |
| /guide | guide/index.html | ★ ガイド一覧 |
| /guide/autofill | guide/autofill.html | |
| /guide/getting-started | guide/getting-started.html | |
| /guide/excel-format | guide/excel-format.html | ★ GSC 未登録対策対象 |
| /guide/troubleshooting | guide/troubleshooting.html | |
| /guide/complete | guide/complete-guide.html | |
| /guide/comprehensive-guide | guide/comprehensive-guide.html | |
| /guide/image-batch, /guide/pdf, /guide/image-cleanup, /guide/seo, /guide/csv | guide/*.html | ツール別ガイド |
| /guide/minutes | （301 → /guide） | リダイレクトのみ |
| /blog/implementation-checklist 他 12 記事 | blog/*.html | 固定リスト |

### 用語集・一覧系

| URL | テンプレート | 備考 |
|-----|-------------|------|
| /glossary | glossary.html | ★ 用語集（薄くなりやすいと指摘されがち） |
| /faq | faq.html | ★ FAQ |
| /best-practices | best-practices.html | ★ 404 対策済み |
| /sitemap.html | sitemap.html | HTML サイトマップ |

### 法務・運営者情報

| URL | テンプレート | 備考 |
|-----|-------------|------|
| /privacy | privacy.html | ★ 必須 |
| /terms | terms.html | ★ 必須 |
| /contact | contact.html | ★ 必須 |
| /about | about.html | ★ 必須 |

### その他（LP・事例）

| URL | テンプレート | 備考 |
|-----|-------------|------|
| /case-study/contact-center | case-study-contact-center.html | |
| /case-study/consulting-firm | case-study-consulting-firm.html | |
| /case-study/remote-startup | case-study-remote-startup.html | |

### API・動的・noindex（クローラ視点では本文にならない）

- `/api/pdf/unlock`, `/api/pdf/lock`, `/api/seo/crawl-urls`, `/api/minutes/format`（POST）
- `/upload`（POST）, `/status/<job_id>`, `/sessions`, `/cleanup-sessions`
- `/download-template`, `/download-previous-template`
- `/healthz`, `/livez`, `/readyz`, `/ping`, `/health`, `/ready`, `/test`

**参照元**: 全ルートは `app.py` に直書き。動的ルートは `[slug]` 形式はなく、ブログ・ガイド・事例は固定ルート＋固定テンプレート。データは `lib/products_catalog.py`（PRODUCTS）と `lib/nav.py`（get_nav_sections, get_footer_columns）。

---

## C. P0: 承認に直結し得る重大リスク（理由と証拠）

| # | リスク | 理由・証拠 |
|---|--------|------------|
| 1 | プライバシーポリシーと実装の矛盾 | 既存レポート `docs/adsense_low_value_content_audit_report_2026-02-24.md` 参照。第8項「今後配信予定」と AdSense 有効時の配信実態の乖離。第4項「原則ローカル処理」と Jobcan AutoFill のサーバー一時処理の矛盾。**証拠**: `templates/privacy.html` の該当項。 |
| 2 | 必須ページの導線不足 | About / Contact / Privacy / Terms はフッター「法的情報」「リソース」から 1 クリックで到達可能（`templates/includes/footer.html`、`lib/nav.py` の get_footer_columns）。**ベストプラクティス**はフッター・グローバルナビにリンクが無い（`get_footer_columns` に best-practices なし）。sitemap.html にも「ベストプラクティス」はあるが、sitemap.html 自体がフッターに無い。**証拠**: `lib/nav.py` 104–144 行、`templates/sitemap.html` 180 行。 |
| 3 | 404・未登録の残存リスク | /best-practices はルート存在（`app.py` 1368 行）、末尾スラッシュは `normalize_trailing_slash`（453–470 行）で 301。GSC で 404 が出ていた場合はキャッシュまたは別URLの可能性。preflight で 1b_best_practices 追加済み。 |
| 4 | 問い合わせ・運営者リンクの有効性 | 既存監査で「GitHub プレースホルダー → RikuTerayama/jobcan_automation に修正」とある。**証拠**: リポジトリ内で `github.com/your-repo` の有無は preflight の DISALLOWED_STRINGS で監視。実ファイルは `templates/contact.html`, `templates/about.html` を要確認。 |

---

## D. P1: 品質・回遊・インデックスに効く改善点（理由と証拠）

| # | 改善点 | 理由・証拠 |
|---|--------|------------|
| 1 | ベストプラクティスをフッターまたはリソースナビに追加 | 現在、ベストプラクティスは LP 本文・ブログ・ガイド・sitemap.html からのみ。フッター「リソース」に無い（`lib/nav.py` get_footer_columns）。 |
| 2 | ツールページの冒頭に「何ができるか・手順・注意点」を短くまとめたブロック | 例: `templates/tools/csv.html` はページヘッダー＋ファイル選択UIが主。説明はあるが「手順・FAQ・出力例」を折りたたみやアコーディオンで一覧できると、クローラ・審査員の把握が容易。**証拠**: `templates/tools/csv.html` 45–100 行付近。 |
| 3 | 事例 3 ページの差別化 | 3 件とも case-study-*.html で構造が類似。本文の独自性・文字量で差別化されているか要確認。**証拠**: `templates/case-study-contact-center.html` 等。 |
| 4 | sitemap.xml の base_url の一元化 | 現在 `app.py` 2164 行で `base_url = 'https://jobcan-automation.onrender.com'` とハードコード。環境変数 BASE_URL と揃えると運用しやすい。**証拠**: `app.py` 2151–2168 行。 |

---

## E. 「薄い」判定になりうるページ一覧（最大20件・カテゴリ別）

| カテゴリ | URL | 懸念（具体的不足） |
|----------|-----|---------------------|
| ツール | /tools/seo | モード切替・入力UIが主。説明・手順はあるが、初期表示で「何ができるか」が一覧しにくい可能性。 |
| ツール | /tools/pdf | 同型。複数モードで説明が分散。 |
| ツール | /tools/image-cleanup | 同型。 |
| ツール | /tools/image-batch | 同型。 |
| ツール | /tools/csv | 操作モードが多く、初見では価値が伝わりにくい可能性。 |
| 一覧 | /glossary | 用語の羅列になりがち。冒頭の「この用語集の価値」説明は追加済み（前回対応）。 |
| 一覧 | /blog | 記事一覧。冒頭説明・カテゴリはあり。前回「コンテンツハブ」説明と導線追加済み。 |
| 一覧 | /guide | ガイド一覧。リンクの羅列にならないよう、各グループ説明があるか要確認。 |
| 事例 | /case-study/contact-center | 他 2 事例と構造が類似。本文量・独自性で差別化されているか。 |
| 事例 | /case-study/consulting-firm | 同上。 |
| 事例 | /case-study/remote-startup | 同上。 |
| ガイド | /guide/image-batch | ツール別ガイド。1 ページあたりの本文量が少ない場合、薄く見える可能性。 |
| ガイド | /guide/pdf | 同上。 |
| ガイド | /guide/image-cleanup | 同上。 |
| ガイド | /guide/seo | 同上。 |
| ガイド | /guide/csv | 同上。 |
| その他 | /sitemap.html | リンク一覧＋短い説明。カテゴリ説明はあり。 |
| 法務 | （該当なし） | privacy / terms / contact / about は本文量・構成とも十分。 |

※ /, /autofill, /tools, /privacy, /guide/excel-format, /best-practices は、既存対応（内部リンク・冒頭説明・canonical・noindex 確認）により、ここでは「薄い」リストからは除外している。

---

## F. 必須ページ/導線の不足チェック結果

| 項目 | 結果 | 証拠 |
|------|------|------|
| About の存在 | あり | `app.py` 1363 行、`templates/about.html` |
| Contact の存在 | あり | `app.py` 1019 行、`templates/contact.html` |
| Privacy の存在 | あり | `app.py` 1009 行、`templates/privacy.html` |
| Terms の存在 | あり | `app.py` 1014 行、`templates/terms.html` |
| グローバルナビからの到達 | 1〜2 クリックで到達可 | `lib/nav.py` の get_nav_sections。Resource 配下に FAQ/用語集/ブログ/About/Contact/Privacy/Terms。 |
| フッターからの到達 | 1 クリックで到達可 | `templates/includes/footer.html`。ツール一覧・ガイド・リソース（FAQ/用語集/ブログ/About）・法的情報（Privacy/Terms/Contact）。 |
| ベストプラクティス | フッター・ナビに**無し** | get_footer_columns に best-practices が含まれていない。sitemap.html と LP/ブログ/ガイドの本文リンクからのみ。 |
| 運営主体・連絡手段 | About に開発背景・技術スタック、Contact に問い合わせ手段（GitHub 等）の記載あり | `templates/about.html`, `templates/contact.html`。 |
| 広告/アフィリエイト表記の拡張余地 | Privacy に Cookie・第三者・オプトアウトの記載あり。将来の PR 表記は Terms やフッターに一文追加可能。 | 現状で必須の欠落は指摘しない。 |

---

## G. クロール到達性チェック結果

| 項目 | 結果 | 証拠 |
|------|------|------|
| robots.txt | あり。複数行。Allow: /。Disallow: /status/, /api/, /sessions, /download-template, /download-previous-template, /cleanup-sessions。Sitemap 行あり。 | `static/robots.txt`。配信は `app.py` 2113 行（send_file）。フォールバック時も同構成（2118–2149 行）。 |
| sitemap.xml | 動的生成。固定 URL リスト＋PRODUCTS からツール・ガイドを追加。lastmod は当日。base_url はハードコード。 | `app.py` 2151–2246 行。必須 URL（/, /autofill, /tools, /privacy, /blog, /glossary, /guide/excel-format, /best-practices）はリストに含まれる。 |
| noindex の混入 | エラーページのみ meta robots noindex。通常ページの head_meta には noindex なし。動的パスは X-Robots-Tag で noindex。 | `templates/error.html` 6 行。`templates/includes/head_meta.html` に noindex なし。`app.py` 478–484 行（/status/, /api/, _NOINDEX_PATHS）。 |
| canonical | 全ページで head_meta により `BASE_URL + request.path` で自己参照。 | `templates/includes/head_meta.html` 43 行。 |
| 末尾スラッシュ | 存在するルートのみ 301 で正規化。重複 URL 防止。 | `app.py` 453–470 行 normalize_trailing_slash。 |
| www / https | リポジトリ内では base_url が https で統一。www の扱いは本番サーバ・CDN 次第。 | `app.py` 2164 行、`templates/includes/head_meta.html` の BASE_URL。 |
| 404・ソフト404・リダイレクト | /guide/minutes → 301 /guide。 /tools/minutes → 301 /tools。その他は通常 200。404 は error.html で表示。 | `app.py` 1083–1086 行、1226–1229 行。エラーハンドラは 266 行以降。 |
| JS 依存 | 主要ページはサーバー側で HTML をレンダリング。ツールページは UI が JS だが、説明・見出しは初期 HTML に含まれる。 | テンプレートは Jinja2 でサーバー描画。no-results 文言は JS で挿入（fromCharCode で本文に生文字列なし）。 |

---

## H. 改善方針（実装案の方向性のみ）

- **P0 プライバシー整合**: 第8項を「本サイトでは Google AdSense により広告を配信しています」に変更。第4項で Jobcan AutoFill のサーバー一時受領・処理後削除を明記。既存監査の推奨と同様。
- **P0 導線**: ベストプラクティスをフッター「リソース」またはナビのリソース配下に 1 リンク追加。必要なら sitemap.html もフッターからリンク。
- **P0 問い合わせ**: contact.html / about.html の GitHub リンクが正しいリポジトリを指しているか確認し、プレースホルダーなら修正。
- **P1 ツールページ**: 各ツールページの冒頭またはツールセクション直前に「できること・手順・注意点」を 3〜5 行の短文でまとめたブロックを追加。既存ガイドへのリンクを明示。
- **P1 事例**: 3 事例の本文を確認し、課題・解決策・数値等で差別化されているか確認。必要なら追記。
- **P1 sitemap**: base_url を環境変数 BASE_URL から取得するよう変更（未設定時は現行のハードコードにフォールバック）。
- **クロール・インデックス**: 現状で robots/sitemap/noindex/canonical は妥当。preflight の 1b（best-practices 200/301）、7（sitemap 必須 URL）、8（robots 複数行・Sitemap）、9（indexable 5 ページ）を継続して監視。

---

## I. 追加で確認が必要な点（リポジトリだけでは確定できないもの）

- **本番の実際の HTTP ステータス**: /best-practices および /best-practices/ が本番で 200/301 になっているかは、curl または preflight --live で確認する必要がある。
- **GSC の「クロール済み・インデックス未登録」の原因**: コンテンツの薄さか、クロール頻度・内部リンクかは GSC の詳細のみで判断可能。リポジトリ上は canonical・noindex・内部リンクは整備済み。
- **AdSense 審査員の実際の閲覧経路**: トップ→ツール一覧→個別ツールか、検索から直で来るかは不明。主要ランディングと法務ページの品質を揃えておく方針で十分。
- **環境変数の本番値**: BASE_URL, ADSENSE_ENABLED, GSC_VERIFICATION_CONTENT 等が Render 等でどう設定されているかは、リポジトリ外のため未確認。

---

以上が現状分析レポートである。次の工程で、上記方針に基づくタスク分解と実装を行う。
