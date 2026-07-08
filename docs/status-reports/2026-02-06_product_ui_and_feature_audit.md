# プロダクト・UI・機能 監査レポート（2026-02-06）

**読者**: ChatGPT（次のプロンプト生成）、未来の自分（改善ロードマップ参照）  
**目的**: 現時点の状態を判断しやすい形でまとめ、クオリティ評価・UI改善方針・追加推奨サービス・実装用プロンプト生成の依頼に使う。

---

## 1) リポジトリ概要（根拠付き）

### フレームワーク
- **Flask + Jinja2**。エントリ: `app.py`。テンプレート: `templates/`。静的: `static/`。
- **根拠**: `app.py` で `Flask(__name__)`, `render_template()`, `url_for('static', ...)` を使用。

### 主要ルーティング（app.py の @app.route から抽出）

| URL | 関数 | テンプレ |
|-----|------|----------|
| `/` | index | landing.html |
| `/autofill` | autofill | autofill.html |
| `/privacy` | privacy | privacy.html |
| `/terms` | terms | terms.html |
| `/contact` | contact | contact.html |
| `/guide` | guide_index | guide/index.html |
| `/guide/getting-started` 他 | 各 guide_* | guide/getting-started.html 等 |
| `/guide/image-batch`, `/guide/pdf`, `/guide/image-cleanup`, `/guide/minutes`, `/guide/seo` | 各 | guide/<id>.html |
| `/tools` | tools_index | tools/index.html |
| `/tools/image-batch`, `/tools/pdf`, `/tools/image-cleanup`, `/tools/minutes`, `/tools/seo` | tools_* | tools/<id>.html |
| `/faq` | faq | faq.html |
| `/glossary` | glossary | glossary.html |
| `/about` | about | about.html |
| `/best-practices` | best_practices | best-practices.html |
| `/sitemap.html` | sitemap_html | sitemap.html |
| `/blog` | blog_index | blog/index.html |
| `/blog/<slug>` | 各 | blog/<slug>.html |
| `/case-study/contact-center` 他 | 各 | case-study-*.html |
| `/api/minutes/format` | api_minutes_format | — (501) |
| `/api/seo/crawl-urls` | api_seo_crawl_urls | — (POST) |
| `/upload` | upload_file | — (POST, Jobcan用) |
| `/sitemap.xml` | sitemap | 動的XML |
| `/robots.txt`, `/ads.txt` | 各 | 動的 |

### ツール定義（lib/products_catalog.py の PRODUCTS）

| id | name | path | guide_path | 制約（catalog 記載） |
|----|------|------|------------|----------------------|
| autofill | Jobcan AutoFill | /autofill | — | — |
| image-batch | 画像一括変換 | /tools/image-batch | /guide/image-batch | 最大50ファイル、1ファイル20MB |
| pdf | PDFユーティリティ | /tools/pdf | /guide/pdf | 最大10ファイル、1ファイル50MB（注: UIでは20/50等の記載あり要確認） |
| image-cleanup | 画像ユーティリティ | /tools/image-cleanup | /guide/image-cleanup | 最大20ファイル、1ファイル20MB |
| minutes | 議事録整形 | /tools/minutes | /guide/minutes | テキスト最大20万文字 |
| seo | Web/SEOユーティリティ | /tools/seo | /guide/seo | — |

---

## 2) ページ棚卸し（URL・テンプレ・JS/CSS・セクション・制約）

### LP・コア
- **URL**: `/`  
- **テンプレ**: `landing.html`  
- **JS/CSS**: `includes/head_meta.html` → common.css, scroll-reveal.css, scroll-reveal.js。GA4, AdSense スニペット。  
- **セクション**: 製品ハブ、CTA、製品カード（products ループ）。  
- **機能**: 製品一覧表示、ツール/ガイドへの導線。

### ツール一覧
- **URL**: `/tools`  
- **テンプレ**: `tools/index.html`  
- **JS/CSS**: 共通。products を grid で表示、各 product.path へリンク。  
- **セクション**: ページヘッダー、products-grid、product-card（名前・説明・使ってみる・ガイド）。

### ツールページ（共通パターン）
- **URL**: `/tools/image-batch`, `/tools/pdf`, `/tools/image-cleanup`, `/tools/minutes`, `/tools/seo`  
- **テンプレ**: `templates/tools/<id>.html`  
- **JS**: 各ツールで script src が異なる。共通: file-validation.js, file-utils.js, zip-utils.js, tool-runner.js。  
  - image-batch: image-convert.js, image-batch-presets.js, image-batch-convert.js  
  - pdf: pdf-range.js, pdf-ops.js, pdf-render.js, pdf-compress.js, pdf-images-to-pdf.js, pdf-extract-images.js（CDN: pdf-lib, pdf.js）  
  - image-cleanup: image-load.js, image-export.js, image-cleanup.js, image-background-removal.js, image-aspect.js（+ image-style.js は feature/image-style-v1 で追加、main 未マージ）  
  - minutes: minutes-parse.js, minutes-normalize.js, minutes-date.js, minutes-extract.js, minutes-templates.js, minutes-export.js, minutes-export-v2.js  
  - seo: seo-ogp-presets.js, seo-ogp-canvas.js, seo-ogp-export.js 他  
- **CSS**: 共通 common.css + 各ページ内 style。  
- **セクション**: ヘッダー、ファイル選択（dropzone/file input）、処理設定（オプション群）、実行/キャンセル、進捗、ダウンロード、エラー。  
- **制約**:  
  - image-batch: maxFiles 50, maxFileSize 20MB（templates/tools/image-batch.html 572–573行付近）  
  - pdf: maxFiles 10/20（ツールによる）, maxFileSize 50MB（604–617行付近）  
  - image-cleanup: maxFiles 20（背景除去時）/50, maxFileSize 20MB, maxTotalSize 100/200MB（519–528行付近）。MAX_PIXELS 80,000,000（image-cleanup.js）  
  - minutes: MAX_TEXT_LENGTH 200,000（minutes.html 等）  
  - seo: ファイル数・サイズは validateFiles で未確認の可能性（要コード確認）

### ガイド
- **URL**: `/guide`, `/guide/getting-started`, `/guide/excel-format`, `/guide/troubleshooting`, `/guide/complete`, `/guide/comprehensive-guide`, `/guide/image-batch`, `/guide/pdf`, `/guide/image-cleanup`, `/guide/minutes`, `/guide/seo`  
- **テンプレ**: `templates/guide/index.html`, `templates/guide/<id>.html`  
- **JS/CSS**: 共通。ガイドは静的コンテンツ。  
- **セクション**: タイトル、できること/課題、主要機能、使い方の流れ、入出力仕様、制限、データ取扱い、FAQ（faq_list）、トラブルシューティング、関連リンク。  
- **FAQPage JSON-LD**: image-batch, pdf, image-cleanup, minutes, seo の各ガイドで `faq_list` を定義し `guide/_partials/guide_faq_jsonld.html` を include（根拠: 各 guide/*.html 内の {% set faq_list %} と include）。

### Autofill
- **URL**: `/autofill`  
- **テンプレ**: `autofill.html`  
- **機能**: Jobcan 自動入力の説明・導線。Excel アップロードは `/upload`（POST）でサーバーに送信・保存される（app.py 1250–1315行）。

### FAQ
- **URL**: `/faq`  
- **テンプレ**: `faq.html`  
- **セクション**: ガイド導線、Jobcan AutoFill、ツール別FAQへのリンク（/guide/image-batch#faq 等）、カテゴリ別Q&A。

### Policy・その他
- **URL**: `/privacy`, `/terms`, `/contact`, `/about`  
- **テンプレ**: `privacy.html`, `terms.html`, `contact.html`, `about.html`  
- **役割**: プライバシー、利用規約、お問い合わせ、サイト概要。AdSense/ポリシー要件に対応。

### ブログ
- **URL**: `/blog`, `/blog/<slug>`（16本）  
- **テンプレ**: `blog/index.html`, `blog/<slug>.html`  
- **セクション**: 記事本文、著者バイオ（author_bio.html 等）。  
- **薄いページリスク**: 記事ごとに本文量は要確認。同一テーマの重複記事はSEOで整理を検討可能。

### サイトマップ
- **URL**: `/sitemap.html`, `/sitemap.xml`  
- **テンプレ**: sitemap.html（HTML）。sitemap.xml は app.py 1607–1685 行で動的生成。PRODUCTS から /tools/*, /guide/* を追加。  
- **網羅性**: 固定URLリスト + PRODUCTS 由来。guide 個別・tools 個別は sitemap.xml に含まれる（要 app.py 1676–1685 行確認）。

---

## 3) UI/UX クオリティ監査（1〜5、根拠）

評価軸: 一貫性 / 視認性 / 体験 / 現代性 / モバイル。主要ページのみ簡易採点。

| ページ | 一貫性 | 視認性 | 体験 | 現代性 | モバイル | 備考 |
|--------|--------|--------|------|--------|----------|------|
| / (LP) | 4 | 4 | 4 | 4 | 4 | 共通デザイン、カード導線明確。 |
| /tools | 4 | 4 | 4 | 4 | 4 | grid、カード hover。 |
| /tools/image-cleanup | 4 | 3 | 4 | 4 | 3 | オプション多、初見で「枠・余白・角丸」の位置が分かりにくい可能性（feature で追加済みなら改善）。 |
| /guide/image-cleanup | 4 | 4 | 4 | 4 | 4 | ステップ・FAQ・制限が明記。 |
| /faq | 4 | 4 | 4 | 4 | 4 | カテゴリ・ガイド導線あり。 |
| /privacy, /terms | 4 | 3 | 3 | 3 | 4 | 本文のみ、デザインはシンプル。 |
| /blog (1記事) | 3 | 4 | 3 | 3 | 4 | 記事により長さ・価値にばらつきの可能性。 |

**改善候補トップ10（実装はしない）**
1. ツールページの「処理設定」内で、機能ブロックに短いラベルやアンカー（例: 枠・余白・角丸）を付け、初見で探しやすくする。  
2. /tools のカードに「New」や機能タグを一時表示し、新機能の認知を促す。  
3. エラー表示を共通コンポーネント化し、文言・スタイルを統一。  
4. フォームの必須/任意、maxFiles/maxFileSize を同一表記でツール間統一。  
5. ガイドの「制限事項」を一覧表にし、ツール別比較をしやすくする。  
6. ブログ記事のメタ description を記事ごとに最適化（重複・短すぎ防止）。  
7. モバイルでツールのオプションが縦に長い場合、アコーディオンやタブで折りたたみ検討。  
8. プライバシー/利用規約に「ツールはブラウザ内処理でサーバーにファイルを送らない」を明記し、ガイドと整合。  
9. FAQ の「ツール別FAQ」への導線を上部にも配置し、スクロール前に見えるようにする。  
10. 構造化データ（SoftwareApplication）をツールページで不足していないか再確認し、必要なら追加。

---

## 4) SEO/AdSense readiness 監査

- **薄いページ**: ブログの一部・case-study が短いと薄いと判定されうる。本文量・独自価値の確認を推奨。  
- **policy**: privacy, terms, contact, about あり（app.py + templates）。  
- **構造化データ**: Organization, WebSite, BreadcrumbList（structured_data.html）。ツールページで SoftwareApplication（product 渡し時、tools/*.html で include）。FAQPage は guide/image-batch, pdf, image-cleanup, minutes, seo で faq_list + guide_faq_jsonld.html。  
- **sitemap**: sitemap.xml は app.py で動的生成。固定リスト + PRODUCTS から /tools/*, /guide/* を追加。sitemap.html は手動リスト。  
- **title/description/canonical**: head_meta.html で page_title, {% block description_meta %}, canonical（https://jobcan-automation.onrender.com{{ request.path }}）を共通で使用。noindex は必要ページのみ block で上書き可能。  
- **要修正**: 特になし。sitemap.xml に guide/* が全て入っているか app.py の PRODUCTS ループで確認推奨。ブログの重複 title/description がないか点検推奨。

---

## 5) 実装方式・データ取扱い整理

| 対象 | 方式 | 根拠 |
|------|------|------|
| /tools/*（5ツール） | 原則ブラウザ内完結 | app.py に /tools 向け POST ファイル受信なし。各ツールは script で FileReader/Canvas/PDF.js 等を使用。 |
| /api/minutes/format | 501 Not Implemented | app.py 799–802 行。テキストは送信されない。 |
| /api/seo/crawl-urls | サーバーでクロール | app.py 850 行付近。start_url を受け、サーバー側で URL 取得。ファイルアップロードではない。 |
| /upload | サーバーで受信・保存 | app.py 1250–1315 行。request.files, file.save(file_path)。Jobcan AutoFill 用 Excel のみ。allowed_file で .xlsx/.xls 制限。 |
| 外部送信 | ツールからはなし（CDN除く） | 背景除去は CDN から @imgly/background-removal 等を読み込み、ブラウザ内実行。画像は当サーバーへ送らない。 |

**ユーザー向け明示**: 各ツールガイドに「アップロードなし」「ブラウザ内処理」を記載。プライバシーポリシーと整合させるとより明確。

---

## 6) 追加推奨サービスの検討（結論含む）

候補は `docs/feature-reports/feature-gap-prioritization.md` に基づく。

| 候補 | 既存との差分 | 実装方式 | 依存候補 | リスク | 記事化 |
|------|--------------|----------|----------|--------|--------|
| PDFテーブル抽出 | ない | ブラウザ（pdf.js getTextContent + 表推定） | pdf.js 既存 | 低（アップロードなし） | 高 |
| OCR | ない | ブラウザ Tesseract.js または サーバー Python | Tesseract.js / pytesseract | 中（サーバーなら負荷） | 高 |
| PDF黒塗り・マスク | ない | ブラウザ（pdf-lib 矩形描画） | pdf-lib 既存 | 低 | 中 |
| Markdown→docx | ない | ブラウザ（docx ライブラリ） | docx 等 | 低 | 中 |
| 画像一括強化 | 既存あり | ブラウザ既存拡張 | — | 低 | 中 |
| 枠・角丸・比率 | 一部あり（比率・トリム） | ブラウザ（image-style.js） | 既存 Canvas | 低 | 中（feature で v1 実装済み・main 未マージ） |

**次にやるべき上位3〜5**
1. **画像一括の既存強化** — プリセット・解像度上限明示・バッチ調整。コスト低・リスク低。  
2. **PDFテーブル抽出（最小版）** — 表形式テキスト→CSV。需要・SEO高。まずブラウザで最小版。  
3. **Markdown→docx** — 議事録と相性良。ブラウザで docx ライブラリ導入。  
4. **枠・角丸（image-style v1）** — 実装済みブランチを main にマージし本番反映。  
5. **PDF黒塗り・マスク** — 個人情報保護ニーズ。領域指定＋矩形で実装可能。

---

## 7) 付録: ChatGPT に渡すための要約ブロック

以下をコピーして ChatGPT に貼り付け、クオリティ評価・UI改善方針・追加推奨サービス・実装用プロンプト生成を依頼する。

```
【プロダクト概要】
- Jobcan 勤怠自動入力（AutoFill）と、画像一括・PDF・画像クリーンアップ・議事録整形・Web/SEO の 5 つのブラウザ内ツールを提供する Flask/Jinja2 サイト。
- 本番: https://jobcan-automation.onrender.com 。main ブランチをデプロイ想定。

【現状の強み】
- ツールは原則ブラウザ内完結で、ファイルをサーバーに送らない（アップロードは Jobcan 用 /upload のみ）。
- 各ツールにガイドと FAQ があり、FAQPage JSON-LD をガイド 5 本で出力。
- プライバシー・利用規約・お問い合わせ・サイトマップ（HTML/XML）あり。共通で title/description/canonical、構造化データ（Organization, WebSite, BreadcrumbList）、AdSense スニペットを配置。

【現状の弱み】
- ツールの処理設定が多く、初見で「枠・余白・角丸」など機能の場所が分かりにくい可能性。
- ブログ・case-study の一部が薄いと判定されうる。ツール間で maxFiles/maxFileSize の表記がばらつく。
- 枠・余白・角丸（image-style v1）は feature ブランチにあり main 未マージのため本番に未反映。

【直近の課題】
- image-style v1 を main にマージし本番で表示すること。
- 画像一括の既存強化、PDFテーブル抽出（最小版）、Markdown→docx の優先度検討と実装方針の具体化。

【推奨の次アクション】
- UI: ツールページの処理設定にラベル/アンカーを付け発見性を向上。エラー表示と制限表記の統一。ガイドとプライバシーの「ブラウザ内処理・送信なし」の整合。
- 機能: (1) image-style v1 のマージ・リリース、(2) 画像一括強化、(3) PDFテーブル抽出の最小版設計、(4) Markdown→docx の技術選定。
```

---

*本レポートは docs/status-reports/2026-02-06_product_ui_and_feature_audit.md として保存。根拠は app.py, lib/products_catalog.py, templates/** および docs/feature-reports/feature-gap-prioritization.md に基づく。*
