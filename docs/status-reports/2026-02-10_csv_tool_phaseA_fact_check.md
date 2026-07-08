# CSV/Excelユーティリティ 追加 Phase A 事実確認レポート

**日付**: 2026-02-10  
**目的**: 新ツール追加に必要な最小変更点をファイル・行番号付きで棚卸し。Phase A ではコード変更は行わない。

---

## 1. 現在ブランチ・コミットと minutes 削除の取り込み状況

| 項目 | 結果 |
|------|------|
| 現在ブランチ | `cleanup/remove-minutes` |
| 現在の最新コミット | `af8a6a2 docs(minutes): add remove-minutes implementation report` |
| origin/main 最新 | `9a8686f Merge pull request #39 from RikuTerayama/analysis/pdf-utility-encrypted-and-image-conversion` |

**結論**: minutes 削除は **cleanup/remove-minutes** ブランチ上にあり、**origin/main には未マージ**。main 相当へはまだ取り込まれていない。CSV ツール実装は、cleanup/remove-minutes をベースにしても、main をベースにしてもよい（main ベースの場合は minutes 旧URL の 301/410 は含まれない）。

**minutes 削除の状態（事実）**  
- `lib/products_catalog.py`: minutes エントリは存在しない（最終は seo で 145–185 行）。  
- `app.py`: 1001–1004 行（/guide/minutes → 301）、1139–1144 行（/tools/minutes → 301）、1145–1150 行（/api/minutes/format → 410）のみ。議事録のレンダリング・API 処理はなし。  
- `lib/nav.py`: フォールバックに議事録の項目はない（73–78 行は image-cleanup の次が Web/SEO）。

---

## 2. 既存ツール追加パターンの再確認

### 2.1 lib/products_catalog.py

- **構造**: `PRODUCTS` はリスト。各要素は辞書。  
  - 必須: `id`, `name`, `description`, `path`, `guide_path`, `status`, `icon`。  
  - 任意: `category`, `tags`, `features`, `capabilities`, `recommended_for`, `usage_steps`, `constraints`, `faq`。  
- **ツール例**: image-batch（20–58 行）、pdf（61–102 行）、image-cleanup（103–143 行）、seo（145–185 行）。  
- **追加位置**: 新エントリは `seo` の前（144 行の直前にブロックを挿入）または `]` の前（185 行の上）に追加。既存は id 順でないため、**185 行の `}` と `]` の間に csv を挿入**する形が安全。

### 2.2 app.py ルーティング

- **ガイド**: `@app.route('/guide/xxx')` → `return render_template('guide/xxx.html')` のみ。  
  - 例: `/guide/seo` 1006–1009 行。  
- **ツール**: `@app.route('/tools/xxx')` → 関数内で `from lib.routes import get_product_by_path`、`product = get_product_by_path('/tools/xxx')`、`return render_template('tools/xxx.html', product=product)`。  
  - 例: `/tools/seo` 1151–1156 行。  
- **追加位置**:  
  - `/guide/csv`: 1009 行の直後（guide_seo の次）に追加。  
  - `/tools/csv`: 1156 行の直後（tools_seo の次）に追加。  
  - （minutes の 301/410 は 1001–1004、1139–1144、1145–1150 にあり、そのまま残す。）

### 2.3 templates の共通部品

- **ツールページ**:  
  - `page_title`, `page_description`, `breadcrumb_title` を `{% set %}`（pdf.html 4–6 行）。  
  - `{% include 'includes/head_meta.html' %}`、`{% block description_meta %}`、`{% block og_description %}`。  
  - product ありなら `includes/structured_data.html` と SoftwareApplication 用 `extra_structured_data`（pdf.html 11–36 行）。  
  - body: `includes/header.html`、`includes/breadcrumb.html`。  
  - ページヘッダー直下で `{% include 'includes/tool_guide_link.html' %}`（pdf.html 309 行）。  
  - ファイル選択: dropzone、#file-list、#rejected-files（pdf.html 313–329 行）。  
- **ガイドページ**:  
  - guide/pdf.html 構成: page_title、description_meta、container、h1、できること、課題、使い方、制限、データ取り扱い、FAQ（faq_list + guide_faq_jsonld）、関連リンク（tool_path, tool_name, guide_related_links）、nav-links、footer。  
  - tool_path / tool_name は末尾で set し、guide_related_links を include（pdf.html 189–194 行）。

### 2.4 tool-runner / file-utils / zip-utils

- **参照**: pdf.html 528–531 行で file-validation.js、file-utils.js、zip-utils.js、tool-runner.js を読み込み。  
- **file-validation.js**: `FileValidation.validateFiles(files, rules)`、`FileValidation.sanitizeFilename(filename)`。  
- **file-utils.js**: `FileUtils.downloadBlob(blob, filename)` 等。  
- **zip-utils.js**: `ZipUtils.createZip(outputs, zipName)`。グローバル `JSZip` 使用。  
- CSV ツールでも同じ script を読み込み、同じパターンで利用可能。

---

## 3. 新ツール追加に必要な最小変更点（ファイル:行番号）

| # | ファイル | 行番号・変更内容 |
|---|----------|------------------|
| 1 | lib/products_catalog.py | 185 行の `}` の直後、`]` の前に新しい辞書 1 件を追加。`id: 'csv'`, `path: '/tools/csv'`, `guide_path: '/guide/csv'`, `status: 'available'` および name, description, icon, constraints, faq 等を定義。 |
| 2 | app.py | 1009 行の直後に `@app.route('/guide/csv')` と `guide_csv()` を追加。`return render_template('guide/csv.html')`。 |
| 3 | app.py | 1156 行の直後に `@app.route('/tools/csv')` と `tools_csv()` を追加。get_product_by_path('/tools/csv')、render_template('tools/csv.html', product=product)。 |
| 4 | lib/nav.py | 78 行の `{'name': 'Web/SEO', ...}` の直前に、`{'name': 'CSV/Excelユーティリティ', 'path': '/guide/csv', 'icon': '📊'}` を 1 件追加（get_nav_sections_fallback の items 内）。get_nav_sections は PRODUCTS から生成するため、PRODUCTS に csv を追加すればツール一覧・ガイド一覧には自動で出る。 |
| 5 | templates/sitemap.html | 170 行の `</ul>` の直前に、`<li><a href="/guide/csv">CSV/Excelユーティリティガイド</a> - CSV/Excelツールの使い方</li>` を 1 行追加（他ガイドと同様の運用）。 |
| 6 | templates/tools/csv.html | **新規**。pdf.html を参考に、最小で page_title, page_description, breadcrumb, head_meta, header, breadcrumb, page-header（h1 + tool_guide_link）、tool-section（ファイル選択または「準備中」）、footer。 |
| 7 | templates/guide/csv.html | **新規**。guide/pdf.html を参考に、最小で page_title, description_meta, container, h1, 短い説明、tool_path='/tools/csv', tool_name='CSV/Excelユーティリティ'、guide_related_links、nav-links、footer。 |

**sitemap.xml**: app.py の sitemap() は PRODUCTS から path / guide_path を取得して URL を追加している（2094–2118 行）。PRODUCTS に csv を追加すれば `/tools/csv` と `/guide/csv` は sitemap.xml に自動で含まれる。固定リストの追加は不要。

---

## 4. まとめ

- minutes は機能としては削除済み（PRODUCTS に無い。app.py は旧 URL の 301/410 のみ）。main には未マージ。  
- 新ツール追加の最小変更は上記 7 点（products_catalog 1 件追加、app.py 2 ルート追加、nav フォールバック 1 件、sitemap.html 1 行、tools/csv.html 新規、guide/csv.html 新規）。  
- 既存の file-validation / file-utils / zip-utils / tool-runner はそのまま利用する。

以上。Phase B では上記に沿ってブランチ `feature/add-csv-excel-utility` で実装する。
