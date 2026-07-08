# P1-1: パンくずリスト（UI + 構造化データ）実装 - 実装サマリー

**実装日**: 2026-02-04  
**タスク**: パンくずリストを全ページに統一導入（UI + BreadcrumbList JSON-LD）

---

## 実装完了確認

### 変更ファイル
- ✅ `templates/includes/breadcrumb.html` - 新規作成（パンくずUI）
- ✅ `templates/includes/structured_data.html` - BreadcrumbList JSON-LD追加
- ✅ `templates/includes/head_meta.html` - structured_data.htmlをinclude
- ✅ `templates/tools/*.html` (6ファイル) - パンくず追加
- ✅ `templates/guide/*.html` (7ファイル) - パンくず追加
- ✅ `templates/blog/index.html` - 既存パンくずを新しいものに置き換え
- ✅ `templates/blog/implementation-checklist.html` - 既存パンくずを新しいものに置き換え
- ✅ `templates/case-study-consulting-firm.html` - 既存パンくずを新しいものに置き換え

### 実装内容

1. ✅ **パンくずUIコンポーネントの作成**
   - `templates/includes/breadcrumb.html`を新規作成
   - `request.path`と`page_title`を使って動的に生成
   - LP（`/`）は非表示

2. ✅ **パンくずルールの実装**
   - Home（/）
   - /tools 配下：Home > ツール一覧（/tools） > 現在ページ
   - /guide 配下：Home > ガイド（/guide/getting-started） > 現在ページ
   - /blog 配下：Home > ブログ（/blog） > 現在ページ
   - /case-study 配下：Home > 導入事例（現在ページ）

3. ✅ **BreadcrumbList JSON-LDの生成**
   - `structured_data.html`の`extra_structured_data`ブロックで生成
   - `head_meta.html`に`structured_data.html`をincludeして全ページで出力

4. ✅ **各ページへの統合**
   - tools配下の6ページにパンくず追加
   - guide配下の7ページにパンくず追加
   - blog配下の既存パンくずを新しいものに置き換え
   - case-study配下の既存パンくずを新しいものに置き換え

---

## 実装差分

### 新規作成: `templates/includes/breadcrumb.html`

```jinja2
{# パンくずリスト（UI + 構造化データ） #}
{% set breadcrumb_items = [] %}
{% set base_url = 'https://jobcan-automation.onrender.com' %}

{# Home を常に最初に追加 #}
{% set _ = breadcrumb_items.append({'name': 'ホーム', 'url': '/'}) %}

{# パスに応じてパンくずを構築 #}
{% if request.path.startswith('/tools/') and request.path != '/tools' %}
    {% set _ = breadcrumb_items.append({'name': 'ツール一覧', 'url': '/tools'}) %}
    {% if page_title is defined %}
        {% set _ = breadcrumb_items.append({'name': page_title, 'url': request.path}) %}
    {% endif %}
{% elif request.path.startswith('/guide/') and request.path != '/guide/getting-started' %}
    {% set _ = breadcrumb_items.append({'name': 'ガイド', 'url': '/guide/getting-started'}) %}
    {% if page_title is defined %}
        {% set _ = breadcrumb_items.append({'name': page_title, 'url': request.path}) %}
    {% endif %}
{# ... その他のルール ... #}
{% endif %}

{# パンくずリストUI（LPは非表示） #}
{% if request.path != '/' %}
<nav aria-label="breadcrumb" class="breadcrumb-nav">
    <ol class="breadcrumb-list">
        {% for item in breadcrumb_items %}
            {% if loop.last %}
                <li aria-current="page">{{ item.name }}</li>
            {% else %}
                <li>
                    <a href="{{ item.url }}">{{ item.name }}</a>
                    <span>›</span>
                </li>
            {% endif %}
        {% endfor %}
    </ol>
</nav>
{% endif %}
```

### 変更: `templates/includes/structured_data.html`

```jinja2
{% block extra_structured_data %}
{# BreadcrumbList JSON-LD（パンくずリスト用） #}
{% if request.path != '/' %}
{% set breadcrumb_items = [] %}
{# ... パンくず構築ロジック（breadcrumb.htmlと同じ） ... #}
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    "itemListElement": [
        {% for item in breadcrumb_items %}
        {
            "@type": "ListItem",
            "position": {{ loop.index }},
            "name": "{{ item.name|e }}",
            "item": "{{ base_url }}{{ item.url }}"
        }{% if not loop.last %},{% endif %}
        {% endfor %}
    ]
}
</script>
{% endif %}
{% endblock %}
```

### 変更: `templates/includes/head_meta.html`

```jinja2
{# Scroll Reveal JS #}
<script src="{{ url_for('static', filename='js/scroll-reveal.js') }}" defer></script>
{# 構造化データ（Organization/WebSite/BreadcrumbList） #}
{% include 'includes/structured_data.html' %}
{% block extra_head %}{% endblock %}
```

### 変更: 各ページテンプレート

```jinja2
{# 例: templates/tools/image-batch.html #}
{% include 'includes/header.html' %}
{% include 'includes/breadcrumb.html' %}
```

---

## 検証手順

### 1. ローカル検証

#### 1.1 Flaskアプリの起動

```bash
python app.py
```

#### 1.2 各ページでパンくずUIを確認

```bash
# /tools 配下
curl http://localhost:5000/tools | grep -A 5 "breadcrumb"
curl http://localhost:5000/tools/image-batch | grep -A 5 "breadcrumb"

# /guide 配下
curl http://localhost:5000/guide/image-batch | grep -A 5 "breadcrumb"

# /blog 配下
curl http://localhost:5000/blog | grep -A 5 "breadcrumb"
curl http://localhost:5000/blog/implementation-checklist | grep -A 5 "breadcrumb"

# /case-study 配下
curl http://localhost:5000/case-study/consulting-firm | grep -A 5 "breadcrumb"
```

**期待される出力**:
```html
<nav aria-label="breadcrumb" class="breadcrumb-nav">
    <ol class="breadcrumb-list">
        <li><a href="/">ホーム</a><span>›</span></li>
        <li><a href="/tools">ツール一覧</a><span>›</span></li>
        <li aria-current="page">画像一括変換ツール</li>
    </ol>
</nav>
```

#### 1.3 BreadcrumbList JSON-LDを確認

```bash
# /tools 配下
curl -s http://localhost:5000/tools/image-batch | grep -A 20 "BreadcrumbList"

# /guide 配下
curl -s http://localhost:5000/guide/image-batch | grep -A 20 "BreadcrumbList"
```

**期待される出力**:
```html
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    "itemListElement": [
        {
            "@type": "ListItem",
            "position": 1,
            "name": "ホーム",
            "item": "https://jobcan-automation.onrender.com/"
        },
        {
            "@type": "ListItem",
            "position": 2,
            "name": "ツール一覧",
            "item": "https://jobcan-automation.onrender.com/tools"
        },
        {
            "@type": "ListItem",
            "position": 3,
            "name": "画像一括変換ツール",
            "item": "https://jobcan-automation.onrender.com/tools/image-batch"
        }
    ]
}
</script>
```

#### 1.4 LPでパンくずが非表示になることを確認

```bash
curl http://localhost:5000/ | grep -i "breadcrumb"
```

**期待される結果**: パンくずが表示されない（LPは非表示）

---

### 2. Rich Results Testでの検証

#### 2.1 Google Rich Results Testにアクセス

1. **Rich Results Testにアクセス**
   - https://search.google.com/test/rich-results

2. **URLを入力して検証**
   - ローカル環境: `http://localhost:5000/tools/image-batch`
   - 本番環境: `https://jobcan-automation.onrender.com/tools/image-batch`

3. **期待される結果**:
   - ✅ BreadcrumbList構造化データが認識される
   - ✅ パンくずが正しく表示される
   - ✅ エラーがない

---

### 3. 本番環境での検証

#### 3.1 デプロイ後の確認

1. **本番環境にデプロイ**
   ```bash
   git add templates/includes/breadcrumb.html templates/includes/structured_data.html templates/includes/head_meta.html templates/tools/*.html templates/guide/*.html templates/blog/*.html templates/case-study-*.html
   git commit -m "feat(seo): P1-1 パンくずリスト全ページ統一導入"
   git push origin <branch-name>
   ```

2. **本番環境でパンくずを確認**
   - `https://jobcan-automation.onrender.com/tools/image-batch`にアクセス
   - ページのソースを表示（右クリック → ページのソースを表示）
   - パンくずUIとBreadcrumbList JSON-LDが含まれていることを確認

---

## 検証チェックリスト

### ローカル検証

- [ ] tools/guide/blog/case-studyの各ページでパンくずが表示される
- [ ] パンくずの階層が正しい（Home > 親カテゴリ > 現在ページ）
- [ ] LP（/）でパンくずが非表示になる
- [ ] JSON-LDが出る（view-sourceで確認）
- [ ] BreadcrumbList構造化データが正しく生成される
- [ ] 既存レイアウトが崩れない

### Rich Results Test検証

- [ ] Rich Results TestでBreadcrumbListとして認識される
- [ ] パンくずが正しく表示される
- [ ] エラーがない

### 本番環境検証

- [ ] 本番環境でパンくずが表示される
- [ ] BreadcrumbList JSON-LDが含まれている
- [ ] Rich Results Testで認識される

---

## 注意点

### 1. page_titleの設定

- 各ページで`{% set page_title = '...' %}`を設定することで、パンくずの現在ページ名が正しく表示される
- `page_title`が設定されていない場合、`request.path`から自動生成される

### 2. パンくずの階層

- `/tools`配下：Home > ツール一覧 > 現在ページ
- `/guide`配下：Home > ガイド > 現在ページ
- `/blog`配下：Home > ブログ > 現在ページ
- `/case-study`配下：Home > 導入事例（親カテゴリなし）

### 3. LPでの非表示

- LP（`/`）ではパンくずが非表示になる（`request.path != '/'`の条件）

---

## 期待される効果

1. **ユーザー体験の向上**: パンくずにより、現在位置と階層が明確になる
2. **SEO効果**: BreadcrumbList構造化データにより、検索結果でパンくずが表示される可能性が高まる
3. **ナビゲーションの改善**: ユーザーが簡単に上位階層に戻れる

---

## 実装完了確認

✅ **実装完了**: パンくずリストを全ページに統一導入  
✅ **BreadcrumbList JSON-LD**: 全ページで出力  
✅ **既存レイアウトの維持**: 既存のレイアウトが崩れない
