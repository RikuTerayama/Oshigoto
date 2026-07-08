# Guide / Resources 情報設計 現状監査レポート

---

## 0. 目的と結論（1ページで分かる）

### 現状の問題の要約

- **構造の偏り**: `/guide` 配下は **Jobcan AutoFill（勤怠自動入力）向けが5ページ**（getting-started, excel-format, troubleshooting, complete, comprehensive-guide）、**他ツール向けは各1ページのみ**（image-batch, pdf, image-cleanup, minutes, seo）。
- **重複・配置の不統一**: Jobcan 向けガイドの実体が **templates 直下**（`guide_getting_started.html` 等）と **templates/guide/**（`complete-guide.html`, `comprehensive-guide.html`）に分散している。
- **「resources」の定義**: URL に `/resources` は存在しない。ナビの「Resource」は **FAQ・用語集・ブログ・About・法務・お問い合わせ** へのドロップダウンラベル（lib/nav.py で定義）。
- **欠け**: 各ツールごとの FAQ / トラブルシュート / データ取扱い の専用ページはなく、Jobcan 向けにのみトラブルシューティング・Excel形式ガイドがある。

### 最重要の観察結果（証拠付き）

1. **Jobcan 向け Guide が5件、他ツールは各1件** — app.py に `/guide/getting-started` 等 5 ルート + `/guide/image-batch` 等 5 ルート。sitemap.xml の固定リスト（app.py 1630–1634行）には Jobcan 向け5件のみが明示列挙され、ツール別ガイドは PRODUCTS の guide_path から動的追加。
2. **テンプレート配置が二系統** — Jobcan: `guide_getting_started.html`, `guide_excel_format.html`, `guide_troubleshooting.html`（直下）と `guide/complete-guide.html`, `guide/comprehensive-guide.html`（guide/ 配下）。他ツール: すべて `guide/<id>.html`。
3. **Resource は URL ではなくナビ区分** — lib/nav.py の `resource_links` に /faq, /glossary, /blog, /about, /privacy, /terms, /contact が列挙。ダウンロード系は /download-template, /download-previous-template で別ルート。

## 1. 現在の情報設計（サイトマップ）

### 公開URLと実体ファイル

| URL | 実体テンプレート | 備考 |
|-----|------------------|------|
| /guide/getting-started | guide_getting_started.html | Guide |
| /guide/excel-format | guide_excel_format.html | Guide |
| /guide/troubleshooting | guide_troubleshooting.html | Guide |
| /guide/complete | guide/complete-guide.html | Guide |
| /guide/comprehensive-guide | guide/comprehensive-guide.html | Guide |
| /guide/image-batch | guide/image-batch.html | Guide |
| /guide/pdf | guide/pdf.html | Guide |
| /guide/image-cleanup | guide/image-cleanup.html | Guide |
| /guide/minutes | guide/minutes.html | Guide |
| /guide/seo | guide/seo.html | Guide |
| /faq | faq.html | Resource（ナビ） |
| /glossary | glossary.html | Resource |
| /about | about.html | Resource |
| /blog | blog/index.html | Resource |
| /privacy | privacy.html | 法的情報 |
| /terms | terms.html | 法的情報 |
| /contact | contact.html | 法的情報 |
| /download-template | （Excel生成） | ダウンロード |
| /download-previous-template | （Excel生成） | ダウンロード |
| / | landing.html | LP |
| /autofill | autofill.html | Jobcan AutoFill |
| /tools | tools/index.html | ツール一覧 |
| /tools/image-batch 他 | tools/<id>.html | 各ツール |

### Guide 階層（親子の整理）

- **Jobcan AutoFill 系（フラット）**: /guide/getting-started, /guide/excel-format, /guide/troubleshooting, /guide/complete, /guide/comprehensive-guide — いずれも同一階層。親ディレクトリなし。
- **他ツール（フラット）**: /guide/image-batch, /guide/pdf, /guide/image-cleanup, /guide/minutes, /guide/seo — 各サービス1ページのみ。

## 2. Guide の現状棚卸し（定量・定性）

- **ページ数**: Guide 全 **10 ページ**。うち Jobcan 向け **5**、他ツール向け **5**（1ツール1ページ）。
- **階層**: すべて1階層（/guide/<slug>）。サブパス（例 /guide/jobcan/overview）はなし。
- **作成方式**: すべて Jinja2 テンプレート直書き。Markdown 読み込みは未使用。
- **内部リンク（リンク元）**: ツールページ（image-batch, pdf, minutes, seo, image-cleanup）から「ガイドを読む」→ 各 /guide/<id>。FAQ・ブログ・事例からは /guide/getting-started, /guide/excel-format, /guide/troubleshooting が多数。sitemap.html は Jobcan 向け3件のみ列挙。
- **Jobcan だけ複数ある根拠**: app.py 698–721 行に 5 ルート定義。lib/nav.py の guide_links に「完全ガイド」「はじめての使い方」「Excelファイルの作成方法」「トラブルシューティング」を固定で先に並べ、その後に products の guide_path を付加。
- **他ツールが1ページしかない根拠**: products_catalog の各 product に guide_path が1つずつ（例 /guide/image-batch）。app.py に /guide/image-batch 等 1 ルートずつのみ。

## 3. resources の現状棚卸し（定量・定性）

- **定義**: 「resources」は **URL プレフィックスではなく**、ヘッダー/フッターの「Resource」ドロップダウンに含まれるページ群（lib/nav.py: resource_links）。
- **ページ数・種類**: FAQ（/faq）、用語集（/glossary）、ブログ一覧・記事（/blog, /blog/xxx）、サイトについて（/about）、プライバシーポリシー（/privacy）、利用規約（/terms）、お問い合わせ（/contact）。テンプレートはすべて HTML。ダウンロードは /download-template, /download-previous-template（Excel 生成）。
- **サービス紐付け**: FAQ は主に Jobcan AutoFill の利用質問。用語集・ブログはサイト全体。各ツール専用の FAQ ページは存在しない。
- **欠けている要素**: 各ツールの「使い方」「制約」「データ取扱い」「トラブルシュート」の専用ページ。画像一括変換・PDF・議事録・SEO 用の FAQ/比較/ユースケースページ。

## 4. 重複/分断/欠落の分析

- **重複**: 「はじめての使い方」「Excel形式」の説明が、guide_getting_started / guide_excel_format / guide/complete-guide / guide/comprehensive-guide に分散。ブログ記事からも同じガイドへ多数リンク。
- **分断**: ツールページからは各 /guide/<tool> へは繋がる。一方、Guide ドロップダウンは「完全ガイド」等が上で、ツール別ガイドが下。Landing から Guide への導線はナビのみ。
- **欠落**: 各ツールの FAQ、トラブルシュート、用語説明、データ取扱い（ローカル処理の明記）の専用ページ。サイトマップ（sitemap.html）にツール別ガイドが未列挙（sitemap.xml には PRODUCTS から動的追加）。

## 5. 「構造化して整える」ための設計案（3案）

### A案: サービス別にガイド階層を統一
- 例: /guide/<service>/overview, /guide/<service>/how-to, /guide/<service>/faq, /guide/<service>/troubleshooting
- **メリット**: 全サービスで同じ構造。拡張しやすい。
- **デメリット**: 既存URLが全て変わる。リダイレクトが大量に必要。
- **既存URL**: 301 リダイレクトで新パスへ。slug は service=jobcan|image-batch|pdf|... に統一。
- **実装難易度**: High

### B案: Guide と resources を統合し /docs に一本化
- 例: /docs/<service>/..., /docs/faq, /docs/glossary
- **メリット**: 「ナレッジは /docs」と一本化。
- **デメリット**: 現行の「Guide」ブランドとナビを全面変更。既存リンク・ブックマークが無効。
- **既存URL**: 301 で /docs へ。Resource 系は /docs/faq 等に移行。
- **実装難易度**: High

### C案: Guide はナレッジ、resources はダウンロード/テンプレに特化
- Guide: 現状の /guide を維持しつつ、中身だけ「各ツール1本＋Jobcan は複数」を整理（重複削減・テンプレ配置統一）。
- Resource: FAQ/用語集/ブログ/About/法務は「ナビの Resource」のまま。ダウンロードは /download-template 等のまま。責任範囲を明文化（Guide=使い方・手順、Resource=サポート・法務・コンテンツ）。
- **メリット**: URL 変更が最小。段階的に整理できる。
- **デメリット**: 「他ツールも複数ページに」する場合は C の延長で A に近づける必要あり。
- **既存URL**: 維持。必要に応じて 301 は最小限（例 comprehensive-guide を complete に統合する場合のみ）。
- **実装難易度**: Medium

## 6. 具体的な整備ToDo（次ステップの実装タスク化）

1. **まずやること**: 情報設計の決定（A/B/C のいずれかまたはハイブリッド）。slug と階層の定義。ナビ（lib/nav.py）の「Guide」「Resource」ラベルと一覧の見直し。
2. **次にやること**: 既存ガイドのテンプレート配置統一（Jobcan をすべて guide/ 配下に移すか、直下を残すか）。重複コンテンツの統合（complete と comprehensive の役割分担または統合）。各ツールに FAQ セクションまたは1ページ追加の要否検討。
3. **最後にやること**: 廃止URL の 404 または 301 設定。sitemap.xml / sitemap.html の更新。内部リンクの一括置換。

## 7. エビデンス（調査ログ）

### 参照したファイル一覧

- app.py（ルート定義・render_template）
- lib/nav.py（Guide / Resource ナビ定義）
- lib/products_catalog.py（guide_path の定義）
- templates/（guide/, guide_*.html, faq.html, glossary.html 等）

### 重要なルート定義の抜粋（app.py）

```
@app.route('/guide/getting-started') -> guide_getting_started.html
@app.route('/guide/excel-format') -> guide_excel_format.html
@app.route('/guide/troubleshooting') -> guide_troubleshooting.html
@app.route('/guide/complete') -> guide/complete-guide.html
@app.route('/guide/comprehensive-guide') -> guide/comprehensive-guide.html
@app.route('/guide/image-batch') -> guide/image-batch.html  (他ツール同様)
```

### ナビ定義（lib/nav.py 要約）

- guide_links: 完全ガイド・はじめての使い方・Excelファイルの作成方法・トラブルシューティング（固定）のあと、PRODUCTS の guide_path を追加。
- resource_links: FAQ, 用語集, ブログ, サイトについて, プライバシー, 利用規約, お問い合わせ。

### 生成スクリプトの走査ルール

- app.py を読み、@app.route と直後の render_template で /guide および Resource 系 URL とテンプレートを対応付け。
- templates 配下を再帰的にリストし、guide 関連テンプレート（guide/*.html, guide_*.html）を列挙。
- templates 内の href="/guide/..." および href="/faq" 等を正規表現で抽出し、リンク元ファイルを集計。
- 本レポートは上記に加え、手動でナビ・sitemap の記述を補足。

---

*Generated by scripts/generate-ia-guide-resources-report.mjs*
