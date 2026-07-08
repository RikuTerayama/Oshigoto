# 議事録整形（minutes）機能 完全削除 棚卸し・削除計画レポート

**日付**: 2026-02-10  
**目的**: minutes 機能を完全削除するための参照一覧と削除計画。本フェーズでは実装変更は行わず、レポート作成のみ。

---

## 1. Summary（削除対象の総数とカテゴリ）

| カテゴリ | 件数（目安） | 内容 |
|----------|--------------|------|
| ルーティング/エンドポイント | 3 | `/guide/minutes`, `/tools/minutes`, `POST /api/minutes/format` |
| UIテンプレート | 複数ファイル | tools/minutes.html, guide/minutes.html, 他ページ内の文言・リンク |
| 静的JS | 8ファイル + 1参照 | minutes-*.js 8本、seo.html が minutes-export.js を参照 |
| PRODUCTS/カタログ | 1エントリ | lib/products_catalog.py の minutes 定義 |
| ナビ/ヘッダー | 2箇所 | lib/nav.py（動的＋フォールバック） |
| sitemap/内部リンク | sitemap.xml は PRODUCTS 由来、sitemap.html 固定1行、他ページ内リンク多数 |
| ドキュメント | 多数 | docs/ 配下の設計・監査・レポート（参照のみ、削除は任意） |

**除外（minutes ツールとは無関係）**

- `utils.py`: `start_minutes` / `end_minutes`（時刻計算用変数名）→ 変更不要
- `SRE_RUNBOOK.md`, `README.md`: "5 minutes"（間隔の表記）→ 変更不要

---

## 2. 参照一覧（ファイル:行番号:要約）

### 2.1 app.py（ルーティング・エンドポイント）

| ファイル | 行番号 | 要約 |
|----------|--------|------|
| app.py | 1001-1004 | `@app.route('/guide/minutes')` → `guide_minutes()`、`guide/minutes.html` をレンダリング |
| app.py | 1139-1144 | `@app.route('/tools/minutes')` → `tools_minutes()`、`get_product_by_path('/tools/minutes')`、`tools/minutes.html` |
| app.py | 1147-1150 | `@app.route('/api/minutes/format', methods=['POST')` → `api_minutes_format()`、501 返却 |

sitemap.xml は PRODUCTS から動的生成（app.py 2103–2118）のため、PRODUCTS から minutes を削除すれば /tools/minutes と /guide/minutes は sitemap から自動で消える。

---

### 2.2 lib/（PRODUCTS・ナビ）

| ファイル | 行番号 | 要約 |
|----------|--------|------|
| lib/products_catalog.py | 146-185 | 製品エントリ `id: 'minutes'`, name: 議事録整形, path: /tools/minutes, guide_path: /guide/minutes, 説明・capabilities・faq 等 |
| lib/nav.py | 78 | フォールバック用 `{'name': '議事録整形', 'path': '/guide/minutes', 'icon': '📝'}`（get_nav_sections_fallback 内） |

※ get_nav_sections() は PRODUCTS から動的にツール/ガイドを組み立てるため、PRODUCTS から minutes を削除すれば通常ナビからは消える。フォールバックのみ手修正が必要。

---

### 2.3 templates/（UI・ガイド・共通）

| ファイル | 行番号 | 要約 |
|----------|--------|------|
| templates/tools/minutes.html | 4-6 | page_title, page_description, breadcrumb_title（議事録整形） |
| templates/tools/minutes.html | 137-186 | CSS: .minutes-file-picker-row, .minutes-file-picker-btn 等、.minutes-error |
| templates/tools/minutes.html | 309-310 | h1「議事録整形」、説明文 |
| templates/tools/minutes.html | 372-388 | ファイルピッカー行・minutes-error の div |
| templates/tools/minutes.html | 450-456 | script: minutes-parse.js, minutes-normalize.js, minutes-date.js, minutes-extract.js, minutes-templates.js, minutes-export.js, minutes-export-v2.js |
| templates/tools/minutes.html | 483, 490, 547, 580, 626, 635, 643 | getElementById('minutes-error')、console ログ「minutes」 |
| templates/tools/minutes.html | 960, 970 | 関連ツール id 'minutes' の参照 |
| templates/tools/seo.html | 576 | `<script src=".../minutes-export.js">` 参照（SEOツールが export 用に利用） |
| templates/includes/head_meta.html | 28 | デフォルト description に「議事録整形」の文言 |
| templates/tools/index.html | 5 | page_description に「議事録整形」 |
| templates/landing.html | 5, 257, 309-311 | description、本文「議事録」、見出し「議事録・文書作成」「議事録の自動整形」 |
| templates/sitemap.html | 170 | `<li><a href="/guide/minutes">議事録整形ガイド</a>` 固定1行 |
| templates/privacy.html | 107 | 「議事録整形」の記載 |
| templates/guide/minutes.html | 全体 | 議事録整形ガイドページ（タイトル・説明・手順・FAQ・tool_path /tools/minutes） |
| templates/guide/index.html | 7 | meta description に「議事録整形」 |
| templates/guide/image-cleanup.html | 143 | 「次のガイド: 議事録整形」→ /guide/minutes へのリンク |
| templates/guide/autofill.html | 100, 104, 109, 115 | 他ツール説明で「議事録整形」「議事録」の言及 |
| templates/faq.html | 113, 533, 554 | /guide/minutes#faq へのリンク、議事録整形セクション |

---

### 2.4 static/js/（アセット）

| ファイル | 行番号 | 要約 |
|----------|--------|------|
| static/js/minutes-parse.js | 2 | コメント「議事録テキスト解析と抽出」 |
| static/js/minutes-normalize.js | 2 | 議事録テキストの正規化 |
| static/js/minutes-date.js | （ファイル全体が minutes 用） | 日付処理 |
| static/js/minutes-extract.js | 2 | 議事録テキスト解析と抽出 |
| static/js/minutes-templates.js | 2, 39, 97 | 議事録テンプレート、'議事録' デフォルトタイトル |
| static/js/minutes-export.js | 2, 11, 24 | 議事録エクスポート、filenameBase 'minutes' |
| static/js/minutes-export-v2.js | 2 | 議事録エクスポート v2 |

※ minutes-date.js は行番号未列挙だが、ツール専用として削除対象に含める。

---

### 2.5 sitemap / canonical / 内部リンク

- **sitemap.xml**: app.py の sitemap() が PRODUCTS から path / guide_path を追加。minutes を PRODUCTS から削除すれば /tools/minutes と /guide/minutes は sitemap に含まれなくなる。
- **sitemap.html**: templates/sitemap.html 170行目の「議事録整形ガイド」リンクは固定のため、削除または文言修正が必要。
- **canonical**: 各ページは個別に canonical を設定している想定。minutes ページ削除後は旧URLの canonical は不要。
- **内部リンク**: 上記 templates 一覧のとおり、landing・faq・guide/index・guide/image-cleanup・guide/autofill・privacy・head_meta・tools/index などに「議事録」文言または /guide/minutes, /tools/minutes へのリンクあり。

---

### 2.6 テスト・ドキュメント（参照のみ・削除は任意）

| ファイル | 要約 |
|----------|------|
| docs/seo/2026-02-10_topicality_phaseB_changes.md | minutes をツール例として言及 |
| docs/seo/2026-02-10_phaseA_fact_check.md | templates/tools/minutes.html のガイドリンク有無 |
| docs/seo/2026-02-10_topicality_audit.md | /guide/minutes, /tools/minutes, /api/minutes/format の記載 |
| docs/status-reports/2026-02-10_global_heavy_job_queue_analysis.md | 議事録整形 API 501 の説明 |
| docs/status-reports/constraints-consistency.md | minutes の制約（テキスト長） |
| docs/status-reports/2026-02-06_product_ui_and_feature_audit.md | ツール・ガイド・API 一覧に minutes 含む |
| README.md | 議事録整形 (v2)、content-reports の minutes |
| report/seo_technical_audit.md | /guide/minutes, /tools/minutes |
| docs/ui-header-footer-related-tools.md | minutes.html の記載 |
| docs/tools-mvp-implementation-report.md | /tools/minutes、minutes 関連実装の詳細 |
| docs/minutes-mvp-implementation-summary.md | 議事録整形 MVP サマリ全体 |
| docs/minutes-formatting-design-report-v1.md | 議事録整形設計レポート全体 |
| docs/ia-reports/guide-resources-audit.md | /guide/minutes の構造 |
| docs/feature-reports/feature-gap-prioritization.md | minutes ツール・API・JS 一覧 |
| docs/feature-plans/01_image-style-v1.md | minutes.html 対象外の記述 |
| docs/dev-samples/minutes/sample_long.md, sample_short.md | 議事録サンプル（開発用） |
| docs/content-reports/01_minutes.md, 00_master_overview.md | 議事録整形コンテンツレポート |
| docs/adsense-improvement-implementation-summary.md | tools/minutes.html の記載 |
| docs/seo-p0-implementation-summary.md, seo-p0-1-sitemap-implementation.md, seo-p0-1-verification-guide.md | sitemap の /guide/minutes, /tools/minutes 例 |
| docs/seo-utilities-analysis-report-v1.md | minutes-export.js 参照 |

ブログ（templates/blog/*.html）: minutes/議事録の一致なし。

---

## 3. 削除計画（何を消す / 何を修正 / 何を残す）

### 3.1 削除するもの

- **app.py**: `/guide/minutes` のルートと `guide_minutes()`、`/tools/minutes` のルートと `tools_minutes()`、`/api/minutes/format` のルートと `api_minutes_format()`。
- **lib/products_catalog.py**: `PRODUCTS` 内の `id: 'minutes'` のエントリ全体。
- **lib/nav.py**: `get_nav_sections_fallback()` 内の `{'name': '議事録整形', 'path': '/guide/minutes', 'icon': '📝'}` の1要素。
- **templates/tools/minutes.html**: ファイルごと削除。
- **templates/guide/minutes.html**: ファイルごと削除。
- **static/js**: 次の8ファイルを削除。  
  `minutes-parse.js`, `minutes-normalize.js`, `minutes-date.js`, `minutes-extract.js`, `minutes-templates.js`, `minutes-export.js`, `minutes-export-v2.js`  
  （seo.html が minutes-export.js を参照しているため、SEOツール側で代替実装または別ライブラリに差し替える必要あり。削除時は seo.html の該当 script 削除または差し替えをセットで実施。）

### 3.2 修正するもの（文言・リンク・参照の削除・変更）

- **templates/tools/seo.html**: `minutes-export.js` の script タグを削除または、export 機能を別 JS で賄うよう変更。
- **templates/includes/head_meta.html**: デフォルト description から「議事録整形」を外す（他ツールのみの文言に）。
- **templates/tools/index.html**: page_description から「議事録整形」を削除。
- **templates/landing.html**: page_description・本文・「議事録・文書作成」セクション（見出しと「議事録の自動整形」）を削除または一般文言に変更。
- **templates/sitemap.html**: `/guide/minutes` の行（議事録整形ガイド）を削除。
- **templates/privacy.html**: 「議事録整形」の言及を削除または「画像変換・PDF・SEO等」にまとめる。
- **templates/guide/index.html**: meta description から「議事録整形」を削除。
- **templates/guide/image-cleanup.html**: 「次のガイド: 議事録整形」を、次の存在するガイド（例: 議事録の次が seo なら「次のガイド: Web/SEO」）に変更するか、該当ブロックを削除。
- **templates/guide/autofill.html**: 「議事録整形」「議事録」の言及を「画像・PDF・SEO」等に変更（他ツール列挙から議事録を外す）。
- **templates/faq.html**: `/guide/minutes#faq` へのリンクと「議事録整形」セクション（h3 とリンク）を削除または他ツールに統合。

### 3.3 残すもの（本削除では変更しない）

- **utils.py**: `start_minutes` / `end_minutes`（時刻計算）はそのまま。
- **SRE_RUNBOOK.md**, **README.md**: "5 minutes" 等の間隔表記はそのまま。
- **docs/** 配下の過去レポート・設計書は「履歴」として残すか、別タスクで整理するかは任意。受け入れ条件の「grep で minutes が 0 件」には含めない想定（docs は除外してよい）。

---

## 4. SEO 方針案（旧 URL の扱い）

削除後、旧 URL の挙動として以下の選択肢を整理する。実装は行わない。

| 方針 | 内容 | メリット | デメリット |
|------|------|----------|------------|
| **404** | `/tools/minutes`, `/guide/minutes`, `/api/minutes/format` はルート削除のためそのまま 404 | 実装が不要。シンプル。 | 検索エンジンがインデックス削除するまで時間がかかる場合あり。 |
| **410 Gone** | 上記パスを専用ハンドラで 410 返却 | 「恒久的に削除」と明示でき、検索エンジンがインデックスから外しやすい。 | ルート削除に加え、404 ハンドラまたは専用ルートで 410 を返す実装が必要。 |
| **301 リダイレクト** | 旧 URL を別ページへ 301 | リンクジュースやブックマークを別ページに集約できる。 | 遷移先を決める必要がある（例: /tools や /guide）。「議事録」専用の代替が無い場合は /tools が無難。 |
| **301 で代替ツールへ** | 将来「議事録に代わる新ツール」を用意する前提で、/tools/minutes → /tools/新ツール に 301 | コンテンツのつながりを維持できる。 | 新ツールの URL が決まっていないと設定できない。 |

**判断の目安**

- インデックス削除を早く伝えたい → **410**。
- 実装コストを最小にしたい → **404**（ルート削除のみ）。
- ツール一覧などへ誘導したい → **301 で /tools または /guide**。
- 後日、別サービスで「議事録」系を再提供する可能性がある → その URL へ **301** を検討。

sitemap.xml は PRODUCTS から生成しているため、minutes を PRODUCTS から外せば **sitemap からは自動で消える**。sitemap.html は上記のとおり 1 行削除が必要。

---

## 5. 受け入れ条件（削除完了の確認）

実装フェーズ後に、以下を満たすことを推奨する。

1. **コード・テンプレート・静的ファイル**:  
   `minutes` / `議事録` / `/tools/minutes` / `/guide/minutes` / `/api/minutes` で検索したとき、**意図した残り（utils.py の start_minutes/end_minutes、SRE/README の "5 minutes"、必要に応じて docs を除外）以外に一致が無いこと**。  
   例: `grep -r "minutes\|議事録\|/tools/minutes\|/guide/minutes\|/api/minutes" --include="*.py" --include="*.html" --include="*.js" .` で、除外パターン以外 0 件（または docs を除外したうえで 0 件）。

2. **旧 URL の挙動**:  
   - `/tools/minutes`, `/guide/minutes` にアクセスしたとき、方針どおり **404 / 410 / 301** のいずれかであること。  
   - `/api/minutes/format` も同様に 404 / 410 / 301 のいずれか（またはルート削除で 404）。

3. **sitemap**:  
   - `GET /sitemap.xml` のレスポンスに `/tools/minutes` および `/guide/minutes` が**含まれない**こと。  
   - `sitemap.html` に「議事録整形ガイド」のリンクが**残っていない**こと。

4. **ナビ・一覧**:  
   - ヘッダー・フッター・ツール一覧・ガイド一覧に「議事録整形」または `/guide/minutes` / `/tools/minutes` のリンクが**表示されない**こと。  
   - 他ページ（landing, faq, privacy, guide/autofill, guide/image-cleanup 等）から議事録へのリンクが**削除または変更されている**こと。

5. **SEO ツール**:  
   - `templates/tools/seo.html` が `minutes-export.js` に依存しない状態になっていること（削除または別実装に差し替え済み）。

6. **（任意）docs**:  
   - 過去レポートは残す場合、本番コード・テンプレート・静的アセットにのみ上記 grep と URL 確認を適用し、docs は除外してよい。

---

以上。本レポートは実装変更を行わず、削除計画と受け入れ条件の整理のみを行う。
