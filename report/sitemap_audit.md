# Sitemap.xml 監査レポート

**作成日**: 2026-02-04  
**対象サイト**: https://jobcan-automation.onrender.com  
**監査目的**: 現状のサイト構造に対して「すべての公開ページがクローリングされる状態」になっているかを確認

---

## 1. 現状把握

### 1.1 Sitemap.xmlの実体と配信方法

- **実体**: `app.py` の `/sitemap.xml` ルートで動的生成
- **配信方法**: Flaskの `Response` で `application/xml` として返却
- **実装箇所**: `app.py:1186-1271`
- **Content-Type**: `application/xml` ✅

### 1.2 Robots.txtの確認

- **ファイル**: `static/robots.txt`
- **Sitemap記載**: ✅ `Sitemap: https://jobcan-automation.onrender.com/sitemap.xml`
- **Disallow**: なし（全ページ許可）

### 1.3 クロール可能性チェック

#### ✅ GET 200を返す設計
- すべての公開ページは `render_template()` でHTMLを返す設計

#### ✅ noindexの確認
- `templates/includes/head_meta.html` を確認：`noindex` メタタグなし
- 全ページでインデックス可能

#### ✅ canonicalの確認
- `templates/includes/head_meta.html:28` で正しく設定
- `https://jobcan-automation.onrender.com{{ request.path }}` 形式

#### ✅ robots.txtのDisallow確認
- `static/robots.txt` で全ページ許可（`Allow: /`）

---

## 2. 公開ページ一覧の抽出

### 2.1 app.pyから抽出した公開ページ（GET、HTML返却）

#### 主要ページ
- `/` - ランディングページ
- `/autofill` - Jobcan自動入力ツール
- `/tools` - ツール一覧
- `/about` - サイトについて
- `/contact` - お問い合わせ
- `/privacy` - プライバシーポリシー
- `/terms` - 利用規約
- `/faq` - よくある質問
- `/glossary` - 用語集
- `/best-practices` - ベストプラクティス
- `/sitemap.html` - HTMLサイトマップ

#### ツールページ（PRODUCTSから自動抽出可能）
- `/tools/image-batch` - 画像一括変換
- `/tools/pdf` - PDFユーティリティ
- `/tools/image-cleanup` - 画像ユーティリティ
- `/tools/minutes` - 議事録整形
- `/tools/seo` - Web/SEOユーティリティ

#### ガイドページ
- `/guide/getting-started` - はじめての使い方
- `/guide/excel-format` - Excelファイルの作成方法
- `/guide/troubleshooting` - トラブルシューティング
- `/guide/complete` - 完全ガイド
- `/guide/comprehensive-guide` - 総合ガイド
- `/guide/image-batch` - 画像一括変換ガイド ⚠️ **sitemapに未記載**
- `/guide/pdf` - PDFユーティリティガイド ⚠️ **sitemapに未記載**
- `/guide/image-cleanup` - 画像ユーティリティガイド ⚠️ **sitemapに未記載**
- `/guide/minutes` - 議事録整形ガイド ⚠️ **sitemapに未記載**
- `/guide/seo` - Web/SEOユーティリティガイド ⚠️ **sitemapに未記載**

#### ブログページ
- `/blog` - ブログ一覧
- `/blog/implementation-checklist`
- `/blog/automation-roadmap`
- `/blog/workstyle-reform-automation`
- `/blog/excel-attendance-limits`
- `/blog/playwright-security`
- `/blog/month-end-closing-hell-and-automation`
- `/blog/excel-format-mistakes-and-design`
- `/blog/convince-it-and-hr-for-automation`
- `/blog/playwright-jobcan-challenges-and-solutions`
- `/blog/jobcan-auto-input-tools-overview`
- `/blog/reduce-manual-work-checklist`
- `/blog/jobcan-month-end-tips`
- `/blog/jobcan-auto-input-dos-and-donts`
- `/blog/month-end-closing-checklist`

#### 導入事例
- `/case-study/contact-center`
- `/case-study/consulting-firm`
- `/case-study/remote-startup`

### 2.2 除外対象（sitemapに含めない）

- `/upload` - POST専用API
- `/status/<job_id>` - 動的パラメータ
- `/sessions` - 内部API
- `/cleanup-sessions` - 内部API
- `/healthz`, `/livez`, `/readyz`, `/ping`, `/health`, `/ready` - ヘルスチェック
- `/health/memory` - デバッグ用
- `/test` - テスト用
- `/download-template`, `/download-previous-template` - ダウンロード専用
- `/ads.txt` - 広告用
- `/robots.txt` - 静的ファイル

---

## 3. ギャップ分析

### 3.1 Sitemapに記載されているが実在しない/404の可能性

**なし** ✅  
すべてのURLは `app.py` で定義されており、テンプレートも存在する。

### 3.2 実在するのにSitemapに無いページ

#### 🔴 高優先度（ツール別ガイド - 5ページ）
1. `/guide/image-batch` - 画像一括変換ガイド
2. `/guide/pdf` - PDFユーティリティガイド
3. `/guide/image-cleanup` - 画像ユーティリティガイド
4. `/guide/minutes` - 議事録整形ガイド
5. `/guide/seo` - Web/SEOユーティリティガイド

**理由**: これらのガイドページは最近追加されたもので、sitemap.xmlが更新されていない。

---

## 4. クロール可能性チェック結果

### ✅ すべての公開ページがクロール可能

- **GET 200**: すべてのページは `render_template()` でHTMLを返す
- **noindexなし**: `head_meta.html` に `noindex` メタタグなし
- **canonical正しい**: 正しいURLを指している
- **robots.txt**: 全ページ許可
- **Content-Type**: `application/xml` で正しく配信

---

## 5. 更新方針の提案

### 推奨: **B. Flaskで動的生成する案（改善版）**

**理由**:
1. 現在既に動的生成されているが、手動リスト管理になっている
2. `lib/routes.py` の `PRODUCTS` データを活用して自動化できる
3. ツール別ガイド（`guide_path`）も自動列挙可能
4. `lastmod` を現在日付に自動更新できる
5. 新しいツールやガイドを追加した際に自動で反映される

### 5.1 実装方針

#### 自動生成するURLカテゴリ

1. **主要ページ（固定リスト）**
   - `/`, `/autofill`, `/tools`, `/about`, `/contact`, `/privacy`, `/terms`, `/faq`, `/glossary`, `/best-practices`, `/sitemap.html`

2. **ツールページ（PRODUCTSから自動生成）**
   - `PRODUCTS` の各 `path` を列挙（`status == 'available'` のみ）

3. **ガイドページ（自動生成）**
   - 固定ガイド: `/guide/getting-started`, `/guide/excel-format`, `/guide/troubleshooting`, `/guide/complete`, `/guide/comprehensive-guide`
   - ツール別ガイド: `PRODUCTS` の各 `guide_path` を列挙（存在する場合）

4. **ブログページ（固定リスト）**
   - 既存のブログ記事一覧を維持

5. **導入事例（固定リスト）**
   - `/case-study/contact-center`, `/case-study/consulting-firm`, `/case-study/remote-startup`

#### 優先度と更新頻度の設定

- **主要ページ・ツール**: `changefreq='weekly'`, `priority='0.9'`
- **ガイドページ**: `changefreq='monthly'`, `priority='0.8'`
- **ブログ**: `changefreq='monthly'`, `priority='0.7'`
- **導入事例**: `changefreq='monthly'`, `priority='0.8'`
- **静的ページ（privacy/terms）**: `changefreq='yearly'`, `priority='0.5'`

#### lastmodの扱い

- **推奨**: 現在日付を自動設定（`datetime.now().strftime('%Y-%m-%d')`）
- または、固定日付を維持（手動更新不要）

---

## 6. 実装コード（差分）

### 6.1 app.py の `/sitemap.xml` ルートを更新

```python
@app.route('/sitemap.xml')
def sitemap():
    """XMLサイトマップを動的生成（PRODUCTSから自動生成）"""
    from flask import Response
    from datetime import datetime
    from lib.routes import PRODUCTS
    
    base_url = 'https://jobcan-automation.onrender.com'
    today = datetime.now().strftime('%Y-%m-%d')
    
    urls = []
    
    # 主要ページ（固定リスト）
    main_pages = [
        ('/', 'weekly', '1.0'),
        ('/autofill', 'weekly', '1.0'),
        ('/tools', 'weekly', '0.9'),
        ('/about', 'monthly', '0.9'),
        ('/contact', 'monthly', '0.8'),
        ('/faq', 'weekly', '0.8'),
        ('/glossary', 'monthly', '0.6'),
        ('/best-practices', 'monthly', '0.8'),
        ('/sitemap.html', 'monthly', '0.5'),
        ('/privacy', 'yearly', '0.5'),
        ('/terms', 'yearly', '0.5'),
    ]
    
    for path, changefreq, priority in main_pages:
        urls.append((path, changefreq, priority, today))
    
    # ツールページ（PRODUCTSから自動生成）
    for product in PRODUCTS:
        if product.get('status') == 'available':
            urls.append((product['path'], 'monthly', '0.7', today))
    
    # ガイドページ（固定 + PRODUCTSから自動生成）
    fixed_guides = [
        ('/guide/getting-started', 'weekly', '0.9'),
        ('/guide/excel-format', 'weekly', '0.9'),
        ('/guide/troubleshooting', 'weekly', '0.8'),
        ('/guide/complete', 'weekly', '0.9'),
        ('/guide/comprehensive-guide', 'weekly', '0.9'),
    ]
    
    for path, changefreq, priority in fixed_guides:
        urls.append((path, changefreq, priority, today))
    
    # ツール別ガイド（PRODUCTSから自動生成）
    for product in PRODUCTS:
        if product.get('status') == 'available' and product.get('guide_path'):
            urls.append((product['guide_path'], 'monthly', '0.8', today))
    
    # ブログページ（固定リスト）
    blog_posts = [
        '/blog',
        '/blog/implementation-checklist',
        '/blog/automation-roadmap',
        '/blog/workstyle-reform-automation',
        '/blog/excel-attendance-limits',
        '/blog/playwright-security',
        '/blog/month-end-closing-hell-and-automation',
        '/blog/excel-format-mistakes-and-design',
        '/blog/convince-it-and-hr-for-automation',
        '/blog/playwright-jobcan-challenges-and-solutions',
        '/blog/jobcan-auto-input-tools-overview',
        '/blog/reduce-manual-work-checklist',
        '/blog/jobcan-month-end-tips',
        '/blog/jobcan-auto-input-dos-and-donts',
        '/blog/month-end-closing-checklist',
    ]
    
    for path in blog_posts:
        priority = '0.8' if path == '/blog' else '0.7'
        urls.append((path, 'monthly', priority, today))
    
    # 導入事例（固定リスト）
    case_studies = [
        '/case-study/contact-center',
        '/case-study/consulting-firm',
        '/case-study/remote-startup',
    ]
    
    for path in case_studies:
        urls.append((path, 'monthly', '0.8', today))
    
    # XMLサイトマップを生成
    xml_parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]
    
    for url_path, changefreq, priority, lastmod in urls:
        full_url = base_url + url_path
        xml_parts.append('  <url>')
        xml_parts.append(f'    <loc>{full_url}</loc>')
        xml_parts.append(f'    <changefreq>{changefreq}</changefreq>')
        xml_parts.append(f'    <priority>{priority}</priority>')
        xml_parts.append(f'    <lastmod>{lastmod}</lastmod>')
        xml_parts.append('  </url>')
    
    xml_parts.append('</urlset>')
    xml_content = '\n'.join(xml_parts)
    
    return Response(xml_content, mimetype='application/xml')
```

### 6.2 変更点の要約

1. **`lib/routes` から `PRODUCTS` をインポート**
2. **ツールページを `PRODUCTS` から自動生成**（`status == 'available'` のみ）
3. **ツール別ガイドを `PRODUCTS` の `guide_path` から自動生成**
4. **`lastmod` を現在日付に自動設定**
5. **5つのツール別ガイドページを追加**

---

## 7. 手動検証手順

### 7.1 ローカル検証

1. **sitemap.xmlの確認**
   ```bash
   curl http://localhost:5000/sitemap.xml
   ```
   - XMLが正しく出力されるか
   - 5つのツール別ガイドが含まれているか
   - `lastmod` が今日の日付になっているか

2. **robots.txtの確認**
   ```bash
   curl http://localhost:5000/robots.txt
   ```
   - `Sitemap:` 行が正しく記載されているか

3. **各URLの確認**
   - ブラウザで `/sitemap.xml` を開いてXMLが表示されるか
   - 各ツール別ガイド（`/guide/image-batch` 等）が200を返すか

### 7.2 本番環境検証

1. **ブラウザで確認**
   - https://jobcan-automation.onrender.com/sitemap.xml を開く
   - XMLが正しく表示されるか
   - 5つのツール別ガイドが含まれているか

2. **Google Search Consoleで確認**
   - 「サイトマップ」セクションで `/sitemap.xml` を再送信
   - エラーがないか確認
   - インデックスされたページ数が増えているか確認

3. **XMLバリデーション**
   - https://www.xml-sitemaps.com/validate-xml-sitemap.html で検証
   - エラーがないか確認

---

## 8. まとめ

### 現状の問題点

1. **ツール別ガイド5ページがsitemapに未記載** 🔴
2. **手動リスト管理で保守性が低い** 🟡
3. **lastmodが固定日付（2025-01-26）** 🟡

### 推奨対応

- **B案（動的生成の改善）** を推奨
- `PRODUCTS` データを活用して自動化
- 新しいツールやガイドを追加した際に自動で反映
- `lastmod` を現在日付に自動設定

### 期待効果

- すべての公開ページがクローリングされる
- 保守性の向上（手動更新不要）
- SEOの改善（新しいガイドページがインデックスされる）
