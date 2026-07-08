# UI刷新 - 開発ガイド

## 開発の進め方

### Gitブランチ戦略

```bash
# メインブランチから作業ブランチを作成
git checkout main
git pull origin main
git checkout -b feature/ui-refresh-p0

# 作業完了後、コミット
git add .
git commit -m "feat(ui): P0 - 絵文字をSVGアイコンに置換、角丸・影の縮小"

# プッシュ
git push origin feature/ui-refresh-p0
```

### ブランチ命名規則

- `feature/ui-refresh-p0`: P0タスク用
- `feature/ui-refresh-p1`: P1タスク用
- `feature/ui-refresh-p2`: P2タスク用
- `fix/ui-refresh-{issue}`: バグ修正用

### コミットメッセージの粒度

#### P0: 即時プロ化
```
feat(ui): P0 - 絵文字をSVGアイコンに置換
feat(ui): P0 - 角丸を縮小（コンテナ8px、カード6px、ボタン4px）
feat(ui): P0 - 影を縮小（控えめな影に統一）
feat(ui): P0 - グラデーション背景を単色に変更
feat(ui): P0 - ブランド名を"RT Tools"から"Automation Hub"に変更
```

#### P1: 視覚階層の再構築
```
feat(ui): P1 - タイポグラフィ体系化（h1-h3のサイズ統一）
feat(ui): P1 - letter-spacingを0.01-0.02emに統一
feat(ui): P1 - セクション間隔を48pxに統一
feat(ui): P1 - フォーム内余白を24px/8pxに統一
feat(ui): P1 - CTAボタンの主従を明確化（プライマリ/セカンダリ）
```

#### P2: 構造のクリーンアップ
```
refactor(ui): P2 - common.cssを作成し、CSS変数を一元管理
refactor(ui): P2 - インラインスタイルをクラスベースに移行
refactor(ui): P2 - ボタンコンポーネントをJinja2マクロ化
refactor(ui): P2 - カードコンポーネントをJinja2マクロ化
```

#### スクロールリビール
```
feat(ui): スクロールリビール機能を実装（IntersectionObserver）
feat(ui): scroll-reveal.jsとscroll-reveal.cssを作成
feat(ui): data-reveal属性を主要ページに適用
feat(ui): prefers-reduced-motion対応を追加
```

---

## ファイル構成

### 新規作成ファイル

```
static/
  css/
    common.css          # デザインシステムの基盤
    scroll-reveal.css   # スクロールリビール用CSS
  js/
    scroll-reveal.js    # スクロールリビール用JS
templates/
  includes/
    icons.html          # SVGアイコン用マクロ
```

### 修正ファイル

```
templates/
  includes/
    head_meta.html      # CSS/JSの読み込み追加
    header.html         # 絵文字→SVG、名前変更
  autofill.html        # スタイル移行、角丸・影の縮小
  landing.html          # 同様の修正（今後）
  faq.html             # 同様の修正（今後）
  guide_getting_started.html  # 同様の修正（今後）
```

---

## 実装手順

### Phase 0: 準備（完了）
1. ✅ common.cssを作成
2. ✅ scroll-reveal.jsとscroll-reveal.cssを作成
3. ✅ icons.htmlを作成
4. ✅ head_meta.htmlにCSS/JSを追加

### Phase 1: P0 - 即時プロ化（進行中）
1. ✅ header.htmlを修正（絵文字→SVG、名前変更）
2. ✅ autofill.htmlを修正（スタイル移行、角丸・影の縮小）
3. [ ] landing.htmlを修正
4. [ ] その他主要ページを修正

### Phase 2: P1 - 視覚階層の再構築
1. [ ] タイポグラフィ体系化
2. [ ] 余白の統一
3. [ ] CTAボタンの主従明確化

### Phase 3: P2 - 構造のクリーンアップ
1. [ ] インラインスタイルの移行
2. [ ] コンポーネント化

### Phase 4: スクロールリビール適用
1. [ ] 主要ページにdata-reveal属性を追加
2. [ ] 動作確認

---

## SVGアイコンの使用方法

### 基本的な使用方法

```jinja2
{% from 'includes/icons.html' import icon %}

{# 単純なアイコン #}
{{ icon('home', 20) }}

{# クラスを追加 #}
{{ icon('clock', 18, 'my-icon-class') }}

{# ナビゲーション内で使用 #}
<a href="/" class="nav-link">
    {{ icon('home', 18, 'nav-icon') }}
    <span>Home</span>
</a>
```

### 利用可能なアイコン

- `home`: ホーム
- `clock`: 時計（AutoFill用）
- `tools`: ツール
- `book`: ガイド
- `check`: チェック
- `x`: クローズ
- `alert`: 警告
- `upload`: アップロード
- `download`: ダウンロード
- `file`: ファイル
- `arrow-left`: 左矢印
- `arrow-right`: 右矢印

### 新しいアイコンの追加

`templates/includes/icons.html`の`icon_map`に追加：

```jinja2
{% set icon_map = {
    'home': '<path d="..."></path>',
    'new-icon': '<path d="..."></path>',  # 追加
} %}
```

---

## スクロールリビールの使用方法

### 基本的な使用方法

```jinja2
{# 単一要素 #}
<div data-reveal>
    <h2>セクションタイトル</h2>
    <p>コンテンツ</p>
</div>

{# リスト（stagger効果） #}
<ul data-reveal-stagger>
    <li>項目1</li>
    <li>項目2</li>
    <li>項目3</li>
</ul>

{# カードグリッド（stagger効果） #}
<div class="products-grid" data-reveal-stagger>
    <div class="product-card">カード1</div>
    <div class="product-card">カード2</div>
    <div class="product-card">カード3</div>
</div>
```

### 適用しない場所

- フォーム入力領域（即時操作が必要）
- プログレスパネル（動的更新）
- ログ表示（動的更新）
- エラーメッセージ（即時表示が必要）

---

## トラブルシューティング

### CSS変数が効かない

**原因**: common.cssが読み込まれていない

**解決方法**:
1. `templates/includes/head_meta.html`でCSSが読み込まれているか確認
2. ブラウザの開発者ツールでNetworkタブを確認
3. キャッシュをクリア

### スクロールリビールが動作しない

**原因**: scroll-reveal.jsが読み込まれていない、またはIntersectionObserverがサポートされていない

**解決方法**:
1. `templates/includes/head_meta.html`でJSが読み込まれているか確認
2. ブラウザのConsoleでエラーを確認
3. `data-reveal`属性が正しく設定されているか確認

### アイコンが表示されない

**原因**: icons.htmlのマクロが正しくインポートされていない

**解決方法**:
1. `{% from 'includes/icons.html' import icon %}`が記述されているか確認
2. アイコン名が正しいか確認（icon_mapに存在するか）
3. SVGのパスが正しいか確認

---

## 参考資料

- [UI監査レポート](./ui-audit/professional-ui-audit-report.md)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [MDN - IntersectionObserver](https://developer.mozilla.org/en-US/docs/Web/API/Intersection_Observer_API)
- [Lucide Icons](https://lucide.dev/)（アイコンデザインの参考）
