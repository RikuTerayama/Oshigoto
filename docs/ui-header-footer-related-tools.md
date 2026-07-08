# ヘッダー構造化・関連ツール位置修正 実装メモ

## 変更ファイル一覧（パス付き）

| パス | 種別 |
|------|------|
| `lib/nav.py` | 新規：ナビ構造の一元定義 |
| `app.py` | 修正：context_processor に nav_sections / footer_columns 注入、autofill に related_products 渡し |
| `templates/includes/header.html` | 修正：4大項目＋ドロップダウン化 |
| `templates/includes/footer.html` | 修正：footer_columns で描画、フォールバックあり |
| `templates/includes/related_tools.html` | 新規：関連ツールセクション共通化 |
| `templates/autofill.html` | 修正：related_tools include 追加、`</main>` 位置修正 |
| `templates/tools/pdf.html` | 修正：関連ツールをフッター直前に移動、include 化 |
| `templates/tools/image-batch.html` | 同上 |
| `templates/tools/image-cleanup.html` | 同上 |
| `templates/tools/minutes.html` | 同上 |
| `templates/tools/seo.html` | 同上 |

## 実装内容の要約

### ① ヘッダー構造（4大項目＋ドロップダウン）

- **Home**: 単一リンク（`/`）。children なし。
- **Tools**: ドロップダウン。「すべてのツール」＋ products の利用可能ツール一覧。
- **Guide**: ドロップダウン。完全ガイド／はじめての使い方／Excel／トラブルシューティング＋ツール別ガイド（products の guide_path）。
- **Resource**: ドロップダウン。FAQ／用語集／ブログ／サイトについて／プライバシー／利用規約／お問い合わせ。

挙動:

- PC: ホバーでドロップダウン表示。
- モバイル: ボタンクリックで開閉。外クリック・Esc で閉じる。
- `request.path` は `request is defined and request` を確認した上で `request.path|default('/')` を使用（未定義耐性あり）。
- `nav_sections` が未注入のときは従来の Home / AutoFill / Tools / Guide リンクを表示。

### ② ナビの共通化

- **lib/nav.py**
  - `get_nav_sections()`: ヘッダー用の 4 項目（label, path, children）。children は `{ name, path, icon? }` のリスト。
  - `get_footer_columns()`: フッター用の 4 カラム（title, links）。ツール一覧・ガイド・リソース・法的情報。
  - `get_nav_sections_fallback()`: PRODUCTS 未読込時用の最小ナビ。
- **app.py context_processor**
  - 成功時: `get_nav_sections()` と `get_footer_columns()` を実行し、`nav_sections` と `footer_columns` をテンプレートに渡す。
  - 失敗時: `get_nav_sections_fallback()` と `get_footer_columns()` を渡す（products は空でもカラムは出る）。
- フッターは `footer_columns` を for で回して描画。`footer_columns` が空のときは従来の products ベースのマークアップにフォールバック。

### ③ 関連ツールの位置修正

- **原因**: ツール詳細ページで「関連ツール」ブロックが `{% include 'includes/footer.html' %}` および大量の `<script>` の**後**にあり、DOM 上フッターより下に表示されていた。
- **対応**:
  - `templates/includes/related_tools.html` を新設。`related_products` があればセクションを描画。
  - 各ツール詳細ページで「本文の閉じ div」→ **関連ツール include** → **フッター include** → スクリプト、の順に変更。
- **対象**: `tools/pdf.html`, `tools/image-batch.html`, `tools/image-cleanup.html`, `tools/minutes.html`, `tools/seo.html`, `autofill.html`。
- **autofill**: 従来は related_products なし。`app.py` の autofill ルートで `get_available_products()` から「autofill を除く最大4件」を `related_products` で渡すようにし、`autofill.html` に `related_tools` include を追加。`</main>` を関連ツールの直前に配置。

## 簡易動作確認手順

1. **LP・一覧・ツール詳細・about**
   - `/` → 200、ヘッダーに Home / Tools / Guide / Resource が出る。
   - `/tools` → 200、同様。
   - `/autofill` → 200、関連ツールがフッターの上に表示される。
   - `/tools/pdf`, `/tools/image-batch` など → 200、関連ツールがフッターの上に表示される。
   - `/about`, `/guide/getting-started` など → 200。

2. **ヘッダードロップダウン**
   - PC: Tools / Guide / Resource にホバーでドロップダウン表示。
   - モバイル幅: 同じ項目をクリックで開閉。外クリックまたは Esc で閉じる。

3. **関連ツールの位置**
   - 各ツール詳細ページ（`/autofill`, `/tools/pdf` 等）で「関連ツール」がフッターより上にあること。
   - 開発者ツールで DOM を確認: `related-tools-section` が `footer` より前にあること。

4. **request 未定義耐性**
   - ヘッダーでは `_current_path = request.path|default('/') if (request is defined and request) else '/'` を使用しているため、request が無くても落ちない。

## ルーティング・URL

- 変更なし（UI・テンプレのみ）。
