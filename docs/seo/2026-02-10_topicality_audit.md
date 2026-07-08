# トピカリティ（トピック網羅性・一貫性・内部リンク）監査レポート

**作成日**: 2026-02-10  
**対象**: リポジトリ内の事実のみ。コード改修は行っていない。外部調査（Search Console / GA / Web検索）は未実施。

---

## 1. 対象と前提

- **目的**: トピカリティを中心に、現状を事実ベースで診断する。
- **制約**: 本フェーズではコード改修禁止（挙動変更・UI変更・依存追加・設定変更・リファクタ・コミット禁止）。レポート作成のみ。
- **根拠**: リポジトリ内のファイル・行番号・実行コマンド結果のみ。断定できないことは「推測」と明記する。
- **確証の取得方法**: 必要に応じて「実運用の sitemap.xml の取得」「デプロイ後 HTML の確認」等をレポート内に記載。

---

## 2. サイト構造の把握

### 2.1 プロジェクト種別

| 項目 | 内容 |
|------|------|
| **フレームワーク** | Flask（Python）。`app.py` でルーティング。 |
| **ルーティング** | `app.py` の `@app.route(...)` で定義。主要セクション: `/`, `/autofill`, `/guide/*`, `/tools`, `/tools/*`, `/blog`, `/blog/*`, `/case-study/*`, `/faq`, `/glossary`, `/about`, `/contact`, `/privacy`, `/terms`, `/sitemap.html`, `/robots.txt`, `/sitemap.xml`。 |
| **テンプレート** | `templates/` 配下。`landing.html`（トップ `/`）、`guide/`（ガイド）、`tools/`（ツール）、`blog/`（ブログ）、静的な固定ページ（privacy, terms, contact, faq, glossary, about, best-practices, sitemap.html）、事例（case-study-*.html）。 |
| **公開URL** | コード上は `https://jobcan-automation.onrender.com` が canonical・OG・sitemap・robots にハードコード（`templates/includes/head_meta.html` 28行、`app.py` 2002行等）。 |
| **サイトマップ生成** | `app.py` 1989行〜 `sitemap()` で XML を動的生成。固定URLリスト + `lib.routes.PRODUCTS`（`lib.products_catalog.PRODUCTS`）から `path` / `guide_path` を追加。lastmod は当日日付。 |
| **多言語対応** | なし。`hreflang` や locale 切り替えのコードは見当たらない。全テンプレート `lang="ja"`。 |

### 2.2 主要セクションと生成方式

- **トップ**: `/` → `landing.html`（製品カード一覧。products は context_processor + `lib.products_catalog.PRODUCTS`）。
- **AutoFill**: `/autofill` → `autofill.html`（メイン機能）。
- **ガイド**: `/guide` → `guide/index.html`。サブは `/guide/getting-started`, `/guide/autofill`, `/guide/excel-format`, `/guide/troubleshooting`, `/guide/complete`, `/guide/comprehensive-guide`, `/guide/image-batch`, `/guide/pdf`, `/guide/image-cleanup`, `/guide/minutes`, `/guide/seo`。ツール別ガイドは PRODUCTS の `guide_path` で一覧に表示。
- **ツール**: `/tools` → `tools/index.html`。各ツールは `/tools/image-batch`, `/tools/pdf`, `/tools/image-cleanup`, `/tools/minutes`, `/tools/seo`。PRODUCTS の `path` と対応。
- **ブログ**: `/blog` → `blog/index.html`。記事は固定ルート（例: `/blog/implementation-checklist`）で個別テンプレート。
- **導入事例**: `/case-study/contact-center`, `/case-study/consulting-firm`, `/case-study/remote-startup`。
- **API**: `/api/pdf/unlock`, `/api/pdf/lock`, `/api/minutes/format`, `/api/seo/crawl-urls` は POST 主体でインデックス対象想定外。

---

## 3. 技術SEOの現状

### 3.1 robots.txt

- **有無**: あり。`static/robots.txt` に実体。`app.py` 1971行で `/robots.txt` に `send_file('static/robots.txt')` で配信。
- **内容**: `User-agent: *` / `Googlebot` / `AdsBot-Google` いずれも `Allow: /`。`Sitemap: https://jobcan-automation.onrender.com/sitemap.xml`。
- **根拠**: `static/robots.txt` 1〜12行、`app.py` 1971〜1988行。

### 3.2 sitemap.xml

- **有無**: あり。動的生成。
- **生成処理**: `app.py` 1989〜2104行。固定URLリスト（主要・ガイド・ツール・ブログ・事例・sitemap.html）＋ PRODUCTS の `path` / `guide_path`（status=available のみ）を重複排除して追加。`lastmod` は `datetime.now().strftime('%Y-%m-%d')` で当日。
- **重複**: 固定リストと PRODUCTS で同じ path が定義されていれば `seen_urls` で除外（2059〜2079行）。
- **確認方法**: デプロイ環境で `GET /sitemap.xml` を取得し、想定URLが含まれるか・lastmod が期待どおりか確認。

### 3.3 canonical

- **設定**: 全ページ共通で `templates/includes/head_meta.html` 28行。  
  `href="https://jobcan-automation.onrender.com{% if request and request.path %}{{ request.path }}{% else %}/{% endif %}"`  
  末尾スラッシュは付与していない。
- **例外**: `templates/tools/seo.html` 内のサンプル表示用ブロック（1083, 1118行）に `canonical` の例（`https://example.com/sample`）があり、本番ページの canonical には影響しない（ブロック内のデモ用）。

### 3.4 noindex

- **混入**: `templates/error.html` 6行のみ。`<meta name="robots" content="noindex, nofollow">`。エラー表示用のため妥当。
- その他テンプレートに noindex はなし（grep 結果: `templates/error.html` のみ）。

### 3.5 重複URLの可能性

- **末尾スラッシュ**: リダイレクトや正規化のコードは見当たらない（`app.py` で redirect/trailing/slash 検索でヒットなし）。サーバやプロキシで `/path` と `/path/` の両方が 200 を返す場合、重複コンテンツになり得る。**断定は要デプロイ確認**。
- **クエリパラメータ**: トップの `potentialAction`（structured_data.html 33行）に `urlTemplate` で `?q={search_term_string}` が含まれる。検索機能の有無は未確認。パラメータ付きURLの canonical 方針は未実装。
- **ページネーション**: ブログ一覧は単一ページの想定。ページネーション用の `?page=` 等のルートはなし。

### 3.6 タイトル・meta description

- **タイトル**: `head_meta.html` 26行。`<title>{{ page_title|default('Jobcan AutoFill - 勤怠データ自動入力ツール') }}</title>`。各テンプレートで `{% set page_title = '...' %}` を定義（grep で 40件以上のテンプレートで設定を確認）。
- **meta description**: `head_meta.html` 27行で `{% block description_meta %}{% endblock %}`。各ページで `{% block description_meta %}<meta name="description" content="...">{% endblock %}` を定義しているテンプレートが多数。未定義の場合は空になる可能性あり（default の記述なし）。
- **OG/Twitter**: 33〜42行で `page_title` と block で og_description / twitter_description を利用。

### 3.7 構造化データ

- **種類**: `templates/includes/structured_data.html` で JSON-LD を 3 種出力。
  - Organization（名称・url・logo・description・contactPoint）。
  - WebSite（名称・url・description・publisher・potentialAction に SearchAction）。
  - BreadcrumbList（`request.path` に応じて動的生成。`/` 以外で block `extra_structured_data` 内）。
- **BreadcrumbList**: `/tools/*`, `/guide/*`, `/blog/*`, `/case-study/*` 等を分岐で item 構築（41〜66行）。`breadcrumb_title` / `page_title` の fallback あり。

---

## 4. コンテンツ棚卸し

インデックス対象になりうるページを、ルート・title（テンプレート上の設定）・H1・主トピック・検索意図・内部リンク送出数の概算で整理。本文文字数はリポジトリのみでは正確に出せないため「—」とする。

| 想定URL | title（設定値） | H1 | 主トピック | 検索意図 | 送出リンク概算 |
|---------|-----------------|-----|------------|----------|-----------------|
| / | 業務効率化ツール集 | 業務効率化ツール集 | ハブ・ツール一覧 | 比較・入口 | 少（landing は 1、ヘッダー・フッターは共通） |
| /autofill | Jobcan勤怠自動入力ツール | （sr-only）Jobcan勤怠データ自動入力ツール | AutoFill | 使い方・導入 | 11 |
| /tools | ツール一覧 - 業務効率化ツール集 \| Automation Hub | ツール一覧 | ツール一覧 | 比較・選択 | 1（ツール本体は product ループ） |
| /tools/image-batch | 画像一括変換ツール - ... | 画像一括変換ツール | 画像変換 | 使い方・機能 | 1 |
| /tools/pdf | PDFユーティリティ - ... | PDFユーティリティ | PDF | 使い方・機能 | 1 |
| /tools/image-cleanup | 画像ユーティリティ - ... | 画像ユーティリティ | 画像 | 使い方・機能 | 1 |
| /tools/minutes | 議事録整形ツール - ... | 議事録整形 | 議事録 | 使い方・機能 | 1 |
| /tools/seo | Web/SEOユーティリティ - ... | Web/SEOユーティリティ | SEO | 使い方・機能 | 1 |
| /guide | ガイド一覧 \| Automation Hub | ガイド一覧 | ガイドハブ | 入口・比較 | 9 |
| /guide/getting-started | はじめての使い方 \| Jobcan AutoFill | はじめての使い方 | AutoFill | 使い方・情報 | 15 |
| /guide/autofill | Jobcan AutoFill ガイド \| ... | Jobcan AutoFill ガイド | AutoFill | 使い方 | 15 |
| /guide/excel-format | Excelファイルの作成方法 \| ... | Excelファイルの作成方法 | AutoFill・Excel | 作り方・情報 | 5 |
| /guide/troubleshooting | トラブルシューティング \| ... | トラブルシューティング | AutoFill | トラブル解決 | 11 |
| /guide/complete | （complete-guide.html） | Jobcan AutoFill 完全ガイド | AutoFill | 総合情報 | 28 |
| /guide/comprehensive-guide | ... | Jobcan勤怠管理を効率化する総合ガイド | AutoFill | 情報・導入 | 14 |
| /guide/image-batch | 画像一括変換ツールガイド \| ... | 画像一括変換ツールガイド | 画像変換 | 使い方 | 5 |
| /guide/pdf | PDFユーティリティガイド \| ... | PDFユーティリティガイド | PDF | 使い方 | 5 |
| /guide/image-cleanup | 画像ユーティリティガイド \| ... | 画像ユーティリティガイド | 画像 | 使い方 | 5 |
| /guide/minutes | 議事録整形ツールガイド \| ... | 議事録整形ツールガイド | 議事録 | 使い方 | 5 |
| /guide/seo | Web/SEOユーティリティガイド \| ... | Web/SEOユーティリティガイド | SEO | 使い方 | 4 |
| /blog | ブログ \| Jobcan AutoFill | Jobcan AutoFill ブログ | ブログハブ | 入口・情報 | 28 |
| /blog/implementation-checklist | （各記事で個別） | （各記事H1） | 導入・勤怠 | 情報・導入 | 7〜12程度 |
| （他ブログ記事 14本） | 同上 | 同上 | 勤怠・自動化・Jobcan | 情報・トラブル・導入 | 5〜12程度 |
| /faq | よくある質問（FAQ） \| ... | よくある質問（FAQ） | FAQ | トラブル・情報 | 40 |
| /glossary | 用語集 \| ... | 勤怠管理・Jobcan用語集 | 用語 | 情報 | 7 |
| /about | サイトについて \| ... | Jobcan AutoFillについて | 会社・サービス | 情報 | 16 |
| /contact | お問い合わせ \| ... | お問い合わせ | お問い合わせ | コンバージョン | 6 |
| /best-practices | ベストプラクティスガイド \| ... | ベストプラクティスガイド | 運用 | 情報 | 10 |
| /privacy | プライバシーポリシー \| ... | プライバシーポリシー | 法的 | 情報 | 2 |
| /terms | 利用規約 \| ... | 利用規約 | 法的 | 情報 | 5 |
| /sitemap.html | サイトマップ \| ... | サイトマップ | ナビ | 入口 | 36 |
| /case-study/contact-center | 導入事例：コンタクトセンター... | （H1同文） | 事例 | 導入検討 | 2 |
| /case-study/consulting-firm | 月次締めの"残業30時間"から... | （H1同文） | 事例 | 導入検討 | 3 |
| /case-study/remote-startup | フルリモート環境での... | （H1同文） | 事例 | 導入検討 | 4 |

- **送出数**: 同一テンプレート内の `href="/..."` の出現数（共通の header/footer は含む）。実際の被リンク数は全テンプレートを集計しないと出せないため、本表では「送出」のみ概算。
- **API・動的URL**: `/status/<job_id>`, `/sessions`, `/download-template`, `/upload`, `/test`, `/healthz` 等は sitemap に含まれておらず、ナビやフッターからもリンクされていない想定。autofill のフローから遷移する場合は「孤立しつつクロールされうるURL」になり得る。

---

## 5. トピカリティ診断

### 5.1 サイトの主テーマ（要約）

1. **Jobcan 勤怠自動入力（AutoFill）** — メインサービス。使い方・Excel形式・トラブル・導入事例・ブログの多くがここに紐づく。
2. **業務効率化ツール群（画像・PDF・議事録・SEO）** — ツール一覧と各ツール＋ガイド。ブラウザ内処理・アップロード不要が共通訴求。
3. **導入・信頼（FAQ・用語集・事例・ベストプラクティス）** — 導入検討・理解深化・トラブル解決。

### 5.2 サブトピック地図（トピックマップ）

**既存ページでカバーできている項目**

- AutoFill: 使い方、Excel形式、トラブル、完全ガイド、総合ガイド。
- ツール別: 画像一括変換、PDF、画像クリーンアップ、議事録、Web/SEO。各「ツール本体 + 1本ガイド」のペアあり。
- 導入: FAQ、用語集、事例 3 本、ベストプラクティス、ブログ（導入・月末・Playwright・情シス等）。
- 法的: プライバシー、利用規約、お問い合わせ。

**不足しているが同テーマ内で自然に追加できる項目**

- **ツール共通**: 「ブラウザ内処理とは」「アップロードしない理由」など、全ツールに共通する説明ページ（ハブ的1本）があるとトピックの一貫性が増す。
- **ツール別の深掘り**: 各ツールの「よくある失敗」「他のツールとの使い分け」など、ガイドからツール・他ガイドへの導線を増やせる。
- **ブログとツールの紐づけ**: ブログ記事から「該当するツール」「関連ガイド」への本文中リンクが少ないと、トピックのつながりが弱い（未カウントのため要サンプル確認）。

**ハブページ候補とスポーク**

- **既存ハブ**: `/`（landing）、`/tools`、`/guide`、`/blog`。ガイド一覧（`/guide`）はツール別ガイド＋AutoFill サブガイドを一覧化できている。
- **ハブが弱い可能性**: `/` は「業務効率化ツール集」で製品カードを並べているが、テーマ別のまとめ（例: 「勤怠自動化」「ファイル変換」）がなく、トピックの階層が薄い。
- **スポーク候補**: 上記「ツール共通の説明」「ツール別の深掘り」を、既存ガイドやブログからリンクするスポークとして追加する余地あり。

### 5.3 トピックの一貫性

- **名称**: 「Jobcan AutoFill」「Automation Hub」「業務効率化ツール集」が混在（title や H1 で使い分け）。サイト全体の「サービス名」をどう出すかの方針が揃っていると一貫性が増す。
- **ガイドとツール**: 各ツールに 1 本のガイドが対応しており、トピック単位の対応は取れている。ガイド一覧の「Jobcan AutoFill 詳細ガイド（サブガイド）」と「ツール別ガイド」の2系統が、入口でやや分かれている。

---

## 6. 内部リンク診断

### 6.1 孤立ページ（入リンクが極端に少ない可能性）

- **ツール本体ページ**（`/tools/pdf`, `/tools/image-cleanup` 等）: 各テンプレート内の `href="/..."` は 1 件（ツールトップへの戻り等）のみのものが多い。**入リンク**は、`/tools` の product ループ、ヘッダーの Tools ドロップダウン、フッターの「すべてのツール」＋製品リンク、ガイドの「ツール本体」リンクに依存。フッターは `footer_columns` 未注入時は products ループでツールへリンクするため、孤立はしにくいが、**本文中**のリンクは少ない。
- **ブログ記事**: ブログ一覧（`/blog`）とヘッダー・フッターからはリンクされる。記事間の「関連記事」や「このツールを使う」のような本文導線は、テンプレートを確認した範囲では限定的（要サンプル確認）。
- **動的URL**: `/status/<job_id>` 等は sitemap に含まれず、ナビにも出ない。リンクのみで辿り着くため、意図しないインデックスを防ぐなら noindex や認証の検討が必要。

### 6.2 ハブの弱さ

- **ガイドハブ**（`/guide`）: ツール別ガイド一覧＋AutoFill サブガイドの details があり、枝は伸びている。一方で「ガイドからツール本体」は `guide_related_links.html` の「ツール本体」リンクで各ガイドから 1 本ずつ。ツール一覧（`/tools`）から各ツールの**ガイド**へのリンクが、product に `guide_path` があればカード等で出ているかは要確認（tools/index の product_card に guide_path リンクがあるか）。
- **ブログハブ**（`/blog`）: 一覧で記事へのリンクはある。ブログから「ツール」「ガイド」へのまとまった導線（サイドバーや関連リンクブロック）があるかは未確認。

### 6.3 アンカーテキスト

- **フッター**: 「すべてのツール」「よくある質問（FAQ）」「用語集」「ブログ」「サイトについて」等、意味のあるアンカーが多い。
- **ガイド関連リンク**（`guide_related_links.html`）: 「ツール本体」「ガイド一覧」「ツール一覧」「このガイド」「よくある質問（FAQ）」等、説明的。
- **product_card**: 「使ってみる」「詳細を見る」はやや汎用的。ツール名はカードの見出し（h3）で出ており、リンクのアンカー自体は短い。
- **ヘッダー**: 「Home」「AutoFill」「Tools」「Guide」は英語で短い。ドロップダウン内はアイコン＋名前で識別可能。

### 6.4 ナビと本文導線

- ナビ上は「Home / AutoFill / Tools / Guide」で近いが、**ツール詳細ページからガイド**へのリンクは、ツールテンプレートに `related_tools` や「このツールのガイド」ブロックが無ければ少ない可能性がある。ガイド→ツールは `guide_related_links` で確保されている。

---

## 7. 改善バックログ

| 優先度 | 項目 | 理由・期待効果 | 修正箇所の当たり |
|--------|------|----------------|-------------------|
| **P0** | 末尾スラッシュの重複対策 | `/path` と `/path/` の両方が 200 だと重複コンテンツになり得る。 | Flask で `strict_slashes=False` の挙動確認、またはリダイレクトでどちらかに統一。`app.py` のルート定義・ミドルウェア。 |
| **P0** | 動的URLのインデックス制御 | `/status/<job_id>` 等がクロールされると、無数URLがインデックスされる可能性。 | 該当ルートで `X-Robots-Tag: noindex` または meta noindex、または sitemap に含めない＋robots でブロック。`app.py` 該当ハンドラ。 |
| **P1** | meta description の未定義フォールバック | ブロック未定義時、description が空になる可能性。 | `templates/includes/head_meta.html` の `description_meta` ブロックに default または共通短文を検討。 |
| **P1** | ツールページからガイドへの導線 | ツール詳細から「このツールの使い方ガイド」へのリンクが無いと、トピックのつながりが弱い。 | 各 `templates/tools/*.html` に product.guide_path へのリンクブロック追加。または `includes/related_tools.html` の拡張。 |
| **P1** | トップのテーマ別まとめ | 現在はカード羅列のみ。テーマ（勤怠・ファイル変換等）でグループ化するとハブ性が上がる。 | `templates/landing.html` の構成。products を category 等でグループ化して表示。 |
| **P2** | ブログ記事からのツール・ガイドリンク | 記事本文やサイドに「関連ツール」「関連ガイド」を出すとトピックの一貫性が増す。 | ブログテンプレート共通パーツ、または記事ごとの関連リンク。 |
| **P2** | アンカー「使ってみる」の補強 | 可能なら「〇〇ツールを使う」など説明的に。 | `templates/includes/product_card.html` のリンクテキスト。 |
| **P2** | サイト名・サービス名の統一表記 | 「Jobcan AutoFill」「Automation Hub」の使い分けを方針化し、title 等で統一。 | 各テンプレートの `page_title`、head_meta の default。 |

---

## 8. 根拠（参照したファイル・行番号・コマンド）

| 内容 | 参照 |
|------|------|
| ルート一覧 | `app.py` 763〜1334, 1883〜1989 行付近の `@app.route` |
| テンプレート配置 | `templates/` 以下ディレクトリ・ファイル一覧 |
| robots.txt | `static/robots.txt` 全文、`app.py` 1971〜1988 |
| sitemap 生成 | `app.py` 1989〜2104 |
| canonical | `templates/includes/head_meta.html` 28 行 |
| noindex | `templates/error.html` 6 行（grep: noindex は当該のみ） |
| title / description | `templates/includes/head_meta.html` 26〜27 行、各テンプレートの `{% set page_title %}` と `{% block description_meta %}`（grep 結果 40 件以上） |
| 構造化データ | `templates/includes/structured_data.html` 全文 |
| PRODUCTS（path / guide_path） | `lib/products_catalog.py` 8〜227 行、`lib/routes.py` 6 行 |
| ヘッダー・フッター・ガイド関連リンク | `templates/includes/header.html`（7〜54 行）、`templates/includes/footer.html`（1〜65 行）、`templates/guide/_partials/guide_related_links.html` |
| H1 一覧 | 各テンプレートの `<h1` を grep（結果 50 件程度） |
| 内部リンク送出数（概算） | `grep -r 'href="/' templates --include="*.html"` のファイル別カウント |

**実行したコマンド（再現用）**

- `grep -r "href=\"/" templates --include="*.html"`（PowerShell 等では要エスケープ調整）
- `grep -r "noindex" templates --include="*.html"`
- `grep -r "canonical\|noindex\|meta.*robots" templates --include="*.html"`

**確証を得るために推奨する確認**

- 本番で `GET /sitemap.xml` を取得し、想定URLが含まれるか・lastmod が日付になっているか確認。
- 本番で `GET /robots.txt` を取得し、Sitemap URL が正しいか確認。
- 本番で主要ページの HTML を取得し、`<title>`・`<meta name="description">`・`<link rel="canonical">` が期待どおりか確認。
- `/path` と `/path/` の両方にアクセスし、両方 200 か・リダイレクトになるかを確認。

---

## 要点サマリ（P0 を先に分かる形）

- **P0**
  - **末尾スラッシュ**: `/path` と `/path/` の重複を防ぐため、リダイレクトまたは strict_slashes の確認が必要。
  - **動的URL**: `/status/<job_id>` 等を noindex または robots でブロックする検討が必要。
- **P1**
  - meta description のフォールバック、ツール→ガイドの導線追加、トップのテーマ別まとめ。
- **P2**
  - ブログからツール・ガイドへのリンク、アンカー文言の強化、サイト名の統一。

以上。
