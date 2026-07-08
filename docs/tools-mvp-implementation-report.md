# ツール実装MVP設計レポート

> **目的**: 「準備中」表示を解除し、各ツールを最低限動くMVPとして実装するための現状監査と設計レポート

**対象サイト**: https://jobcan-automation.onrender.com/  
**作成日**: 2026-02-03  
**技術スタック**: Flask + Jinja2、バニラJS（ブラウザ内処理）

---

## 0. エグゼクティブサマリー

### 現状のボトルネック

1. **表示ロジックの不整合**: `lib/routes.py`では全ツールが`status: 'available'`だが、`templates/landing.html`ではハードコードで「準備中」表示
2. **フロントエンド実装は完了**: 各ツールページのテンプレートとJS実装は既に存在し、ブラウザ内処理で動作可能
3. **バックエンドAPI不要**: 全ツールがブラウザ内完結設計のため、サーバー側API実装は不要
4. **情報設計の最適化余地**: ツール間の回遊導線、CTA配置、ナビゲーション構造の改善が必要

### 最優先で直すべきこと（P0）

1. **表示ロジックの統一**: `landing.html`を`lib/routes.py`の`PRODUCTS`データに基づいて動的に表示
2. **ステータス表示の整合性**: `tools/index.html`と`landing.html`で同じデータソースを使用
3. **「準備中」バッジの削除**: `lib/routes.py`の`status`を`'available'`に統一（既に設定済み）

### 実装の優先順位

- **P0（即時）**: 表示ロジック修正のみ（1-2時間）
- **P1（短期）**: 各ツールの動作確認とバグ修正（各ツール1-2日）
- **P2（中期）**: 情報設計最適化、回遊導線強化（1週間）

---

## 1. 現状棚卸し

### 1.1 ページとルートの対応表

| URLパス | ルート定義 | テンプレート | ステータス | 備考 |
|---------|-----------|------------|----------|------|
| `/` | `app.py:341` | `landing.html` | ✅ 実装済み | 製品一覧（ハードコード） |
| `/autofill` | `app.py:356` | `autofill.html` | ✅ 利用可能 | 唯一の稼働ツール |
| `/tools` | `app.py:436` | `tools/index.html` | ✅ 実装済み | 動的製品一覧（`PRODUCTS`使用） |
| `/tools/image-batch` | `app.py:411` | `tools/image-batch.html` | ⚠️ 準備中表示 | フロント実装済み |
| `/tools/pdf` | `app.py:416` | `tools/pdf.html` | ⚠️ 準備中表示 | フロント実装済み |
| `/tools/image-cleanup` | `app.py:421` | `tools/image-cleanup.html` | ⚠️ 準備中表示 | フロント実装済み |
| `/tools/minutes` | `app.py:426` | `tools/minutes.html` | ⚠️ 準備中表示 | フロント実装済み |
| `/tools/seo` | `app.py:431` | `tools/seo.html` | ⚠️ 準備中表示 | フロント実装済み |

**根拠**: `app.py`のルート定義（411-434行目）、`lib/routes.py`の`PRODUCTS`定義（10-74行目）

---

### 1.2 「準備中」表示の発生箇所

#### A. `templates/landing.html`（ハードコード）

**該当箇所**: 264-288行目

```html
<span class="status coming-soon">準備中</span>
```

**問題**: 5つのツール全てが「準備中」としてハードコードされている

**根拠**: 
- 264行目: 画像一括変換
- 270行目: PDFユーティリティ
- 276行目: 画像ユーティリティ
- 282行目: 議事録整形
- 288行目: Web/SEOユーティリティ

#### B. `templates/tools/index.html`（動的表示）

**該当箇所**: 170-175行目

```jinja2
{% if product.status == 'available' %}
    <span style="background: rgba(76, 175, 80, 0.2); color: #4CAF50; padding: 3px 8px; border-radius: 6px; font-size: 0.8em;">Local</span>
{% else %}
    準備中
{% endif %}
```

**問題**: `lib/routes.py`の`PRODUCTS`では全ツールが`status: 'available'`だが、`landing.html`では反映されていない

**根拠**: `lib/routes.py:25, 36, 47, 58, 69` - 全ツールが`'status': 'available'`

#### C. `templates/includes/product_card.html`（未使用？）

**該当箇所**: 10行目

```jinja2
{% if product.status == 'available' %}利用可能{% else %}準備中{% endif %}
```

**確認**: このファイルが実際に使用されているか要確認

---

### 1.3 コード構造の棚卸し

#### ルート定義（`app.py`）

**該当箇所**: 411-434行目

```python
@app.route('/tools/image-batch')
def tools_image_batch():
    """画像一括変換ツール（準備中）"""
    return render_template('tools/image-batch.html')

@app.route('/tools/pdf')
def tools_pdf():
    """PDFユーティリティ（準備中）"""
    return render_template('tools/pdf.html')
# ... 同様に3つ
```

**問題**: コメントに「準備中」と記載されているが、実際にはテンプレートは存在し、JS実装も完了している

#### 製品情報定義（`lib/routes.py`）

**該当箇所**: 10-74行目

```python
PRODUCTS = [
    {
        'id': 'image-batch',
        'name': '画像一括変換',
        'status': 'available',  # ← 既に'available'
        ...
    },
    # ... 全ツールが'available'
]
```

**発見**: データ定義では既に`'available'`だが、`landing.html`が参照していない

#### テンプレート構造

**共通レイアウト**:
- `templates/includes/header.html`: ナビゲーション
- `templates/includes/footer.html`: フッター
- `templates/includes/head_meta.html`: メタタグ

**各ツールページ**: 既に完全実装済み
- `templates/tools/image-batch.html`: 927行（完全実装）
- `templates/tools/pdf.html`: 945行（完全実装）
- `templates/tools/image-cleanup.html`: 770行（完全実装）
- `templates/tools/minutes.html`: 796行（完全実装）
- `templates/tools/seo.html`: 1032行（完全実装）

#### 静的リソース（`static/js/`）

**既存JS実装**:
- `image-batch-convert.js`: 画像一括変換ロジック
- `pdf-ops.js`: PDF操作（pdf-lib使用）
- `image-cleanup.js`: 画像処理
- `minutes-parse.js`, `minutes-extract.js`: 議事録処理
- `seo-ogp-canvas.js`, `seo-html-inspector.js`: SEOツール
- `tool-runner.js`: 共通処理ランナー（並列処理、進捗管理）

**外部ライブラリ**（CDN経由）:
- `pdf-lib`: PDF操作
- `pdf.js`: PDFレンダリング
- `jszip`: ZIP作成
- `@imgly/background-removal`: 背景除去（画像ユーティリティ）

**根拠**: 各ツールページの`<script>`タグ（例: `image-batch.html:478-487`）

---

### 1.4 ファイル処理の共通化余地

#### 既存の共通関数（`utils.py`）

**該当箇所**: `utils.py`

```python
def allowed_file(filename):
    """許可されたファイル拡張子かチェック"""
    # Excel専用（.xlsx, .xls）
```

**問題**: 画像/PDF用のバリデーション関数がない

#### アップロード処理（`app.py`）

**該当箇所**: `app.py:704-863` - `/upload`エンドポイント

**問題**: AutoFill専用（Excelファイルのみ）。ツールはブラウザ内処理のため不要

**設計方針**: ツールは全てブラウザ内完結のため、サーバー側アップロード処理は不要

---

## 2. 「準備中」解除の実現方法

### 2.1 表示ロジックの修正

#### 修正ファイル1: `templates/landing.html`

**現状**: 製品カードがハードコード（255-290行目）

**修正方針**: `lib/routes.py`の`PRODUCTS`を参照するように変更

**変更内容**:
```jinja2
{# 修正前（255-290行目） #}
<a href="/autofill" class="product-card">
    <h3>🕒 Jobcan AutoFill</h3>
    <p>...</p>
    <span class="status available">利用可能</span>
</a>
<a href="/tools/image-batch" class="product-card">
    <h3>🖼️ 画像一括変換</h3>
    <p>...</p>
    <span class="status coming-soon">準備中</span>  {# ← ハードコード #}
</a>
# ... 同様に4つ

{# 修正後 #}
{% from 'lib.routes' import PRODUCTS %}
{% for product in PRODUCTS %}
    <a href="{{ product.path }}" class="product-card">
        <h3>{{ product.icon }} {{ product.name }}</h3>
        <p>{{ product.description }}</p>
        <span class="status {{ product.status }}">
            {% if product.status == 'available' %}利用可能{% else %}準備中{% endif %}
        </span>
    </a>
{% endfor %}
```

**ただし**: Jinja2では`from`でPythonモジュールを直接インポートできないため、`app.py`のルートで`PRODUCTS`を渡す必要がある

**正しい修正方法**:
1. `app.py:341`の`/`ルートを修正して`PRODUCTS`を渡す
2. `landing.html`で`products`変数を使用

```python
# app.py:341
@app.route('/')
def index():
    """メインページ"""
    from lib.routes import PRODUCTS
    return render_template('landing.html', products=PRODUCTS)
```

```jinja2
{# landing.html:255-290 #}
{% for product in products %}
    <a href="{{ product.path }}" class="product-card">
        <h3>{{ product.icon }} {{ product.name }}</h3>
        <p>{{ product.description }}</p>
        <span class="status {{ product.status }}">
            {% if product.status == 'available' %}利用可能{% else %}準備中{% endif %}
        </span>
    </a>
{% endfor %}
```

#### 修正ファイル2: `app.py`のルートコメント

**該当箇所**: 411-434行目

```python
# 修正前
@app.route('/tools/image-batch')
def tools_image_batch():
    """画像一括変換ツール（準備中）"""
    return render_template('tools/image-batch.html')

# 修正後
@app.route('/tools/image-batch')
def tools_image_batch():
    """画像一括変換ツール"""
    return render_template('tools/image-batch.html')
```

---

### 2.2 ステータス表示の整合性確保

**現状の問題**:
- `lib/routes.py`: 全ツールが`'available'`
- `landing.html`: ハードコードで「準備中」
- `tools/index.html`: `PRODUCTS`を正しく参照

**解決策**: `landing.html`を`tools/index.html`と同様に`PRODUCTS`を参照するように修正

---

## 3. ツール別MVP設計

### 3.1 画像一括変換（`/tools/image-batch`）

#### ユーザーがやりたいこと
- 複数の画像ファイル（png/jpg/webp）を一括で形式変換
- リサイズ（幅指定、縦横比維持）
- 品質圧縮
- 複数サイズの同時出力（例: オリジナル、サムネイル、中サイズ）
- ZIPで一括ダウンロード

#### 入力と出力

**入力**:
- 対応拡張子: `.png`, `.jpg`, `.jpeg`, `.webp`
- 制約: 最大ピクセル数 80,000,000（`image-batch-convert.js:9`）
- ファイル数: 制限なし（メモリ依存）

**出力**:
- 形式: png/jpg/webp（選択可能）
- リサイズ: 幅指定（0でリサイズなし）
- 品質: 0-100（jpg/webp）
- ZIP: 複数ファイル時は自動でZIP化

#### 画面構成

**既存実装**: `templates/tools/image-batch.html`（927行）

**セクション**:
1. ページヘッダー（タイトル、説明）
2. ファイル選択エリア（ドラッグ&ドロップ対応）
3. 変換オプション（出力形式、リサイズ、品質、プリセット）
4. 実行ボタン
5. 進捗表示（プログレスバー、タスクリスト）
6. ダウンロードパネル（個別/ZIP）

**フォーム要素**:
- ファイル入力（`<input type="file" multiple>`）
- 出力形式選択（`<select>`: png/jpg/webp）
- リサイズ幅入力（`<input type="number">`）
- 品質スライダー（`<input type="range">`）
- プリセット選択（`<select>`: SNS用、Web用等）

**結果表示**:
- タスクリスト（各ファイルの状態: queued/running/success/error）
- ダウンロードボタン（個別/ZIP）

**エラー表示**:
- ファイルサイズ超過
- 対応形式外
- ピクセル数超過

#### バックエンド設計

**エンドポイント**: 不要（ブラウザ内処理）

**処理フロー**:
1. ファイル選択 → `FileReader`で読み込み
2. `ImageConverter`クラスで変換（`image-convert.js`）
3. `ImageBatchConvert`クラスでバッチ処理（`image-batch-convert.js`）
4. `ToolRunner`で並列処理・進捗管理（`tool-runner.js`）
5. `ZipUtils`でZIP化（`zip-utils.js`）
6. ダウンロード（`Blob` + `URL.createObjectURL`）

**主要関数**:
- `ImageBatchConvert.convertWithVariant()`: 変換処理
- `ToolRunner.run()`: 並列実行
- `ZipUtils.createZip()`: ZIP作成

#### 実装ライブラリ候補

**既存実装**: ブラウザAPIのみ（`Canvas API`, `FileReader API`）

**外部ライブラリ**: なし（CDN不要）

**導入リスク**: なし（既に実装済み）

#### セキュリティと運用

**サイズ制限**:
- ピクセル数: 80,000,000（`image-batch-convert.js:9`）
- ファイルサイズ: ブラウザメモリ依存（明示的制限なし）

**MIME検証**: `file-validation.js`で実装済み

**並列処理**: `ToolRunner`で最大2並列（`tool-runner.js:8`）

**タイムアウト**: なし（ブラウザ処理のため）

**削除**: メモリ内のみ、処理後は自動GC

**監査ログ**: 不要（ブラウザ内処理）

#### テスト観点

**正常系**:
- 単一ファイル変換
- 複数ファイル一括変換
- 複数サイズ同時出力
- ZIPダウンロード

**異常系**:
- ファイルサイズ超過
- 対応形式外
- ピクセル数超過
- メモリ不足

**負荷**:
- 大量ファイル（100ファイル以上）
- 高解像度画像（4K以上）

**境界値**:
- ピクセル数: 80,000,000
- 品質: 0, 50, 100

#### 最小実装のスコープ

**MVP範囲**:
- ✅ 形式変換（png/jpg/webp）
- ✅ リサイズ（幅指定）
- ✅ 品質調整
- ✅ 複数ファイル処理
- ✅ ZIPダウンロード

**次の一手（拡張案）**:
- 複数サイズ同時出力（バリアント機能）
- プリセット（SNS用、Web用等）
- メタデータ保持

**現状**: 既に全て実装済み

---

### 3.2 PDFユーティリティ（`/tools/pdf`）

#### ユーザーがやりたいこと
- PDF結合（複数PDFを1つに）
- PDF分割（ページ範囲指定）
- ページ抽出（特定ページのみ）
- PDF→画像変換（全ページを画像zip）
- PDF圧縮（ファイルサイズ削減）
- 画像→PDF変換

#### 入力と出力

**入力**:
- 対応拡張子: `.pdf`
- 制約: ファイルサイズ制限なし（メモリ依存）

**出力**:
- PDF結合: 1つのPDF
- PDF分割: 複数のPDF（ZIP）
- ページ抽出: 抽出ページのPDF
- PDF→画像: 画像ファイル（ZIP）
- 画像→PDF: 1つのPDF

#### 画面構成

**既存実装**: `templates/tools/pdf.html`（945行）

**セクション**:
1. ページヘッダー
2. 機能タブ（結合/分割/抽出/PDF→画像/圧縮/画像→PDF）
3. ファイル選択エリア
4. オプション設定（ページ範囲、画像形式等）
5. 実行ボタン
6. 進捗表示
7. ダウンロードパネル

#### バックエンド設計

**エンドポイント**: 不要（ブラウザ内処理）

**処理フロー**:
1. ファイル選択 → `FileReader`で読み込み
2. `PdfOps`クラスで処理（`pdf-ops.js`）
3. `pdf-lib`（CDN）でPDF操作
4. `pdf.js`（CDN）でPDFレンダリング
5. `ToolRunner`で並列処理
6. ダウンロード

**主要関数**:
- `PdfOps.mergePdfs()`: 結合
- `PdfOps.splitPdf()`: 分割
- `PdfOps.extractPages()`: 抽出
- `PdfRender.renderToImages()`: PDF→画像

#### 実装ライブラリ候補

**既存実装**: 
- `pdf-lib` (CDN): PDF操作
- `pdf.js` (CDN): PDFレンダリング

**導入リスク**: 低（既に実装済み、CDN経由）

#### セキュリティと運用

**サイズ制限**: メモリ依存（明示的制限なし）

**MIME検証**: `file-validation.js`で実装済み

**並列処理**: `ToolRunner`で最大2並列

**タイムアウト**: なし

**削除**: メモリ内のみ

#### テスト観点

**正常系**:
- PDF結合（2ファイル、10ファイル）
- PDF分割（1-10ページ、11-20ページ）
- ページ抽出（1, 3, 5ページ）
- PDF→画像（全ページ）
- 画像→PDF（複数画像）

**異常系**:
- 破損PDF
- パスワード保護PDF（未対応）
- メモリ不足

#### 最小実装のスコープ

**MVP範囲**:
- ✅ PDF結合
- ✅ PDF分割
- ✅ ページ抽出
- ✅ PDF→画像
- ⚠️ PDF圧縮（要確認）
- ✅ 画像→PDF

**次の一手**:
- PDF圧縮の実装確認
- パスワード保護PDF対応
- メタデータ編集

---

### 3.3 画像ユーティリティ（`/tools/image-cleanup`）

#### ユーザーがやりたいこと
- 透過PNG→白背景JPEG変換
- 余白トリミング
- 縦横比統一（背景追加）
- 背景除去（外部API依存の場合はMVP外）

#### 入力と出力

**入力**:
- 対応拡張子: `.png`, `.jpg`, `.jpeg`, `.webp`
- 制約: メモリ依存

**出力**:
- 透過→白背景: JPEG
- 余白トリム: トリム済み画像
- 縦横比統一: 背景追加済み画像

#### 画面構成

**既存実装**: `templates/tools/image-cleanup.html`（770行）

**セクション**:
1. ページヘッダー
2. 機能選択（透過→白背景/余白トリム/縦横比統一/背景除去）
3. ファイル選択
4. オプション設定
5. 実行ボタン
6. 進捗表示
7. ダウンロードパネル

#### バックエンド設計

**エンドポイント**: 不要（ブラウザ内処理）

**処理フロー**:
1. ファイル選択 → `FileReader`で読み込み
2. `Canvas API`で画像処理
3. `ImageCleanup`クラスで処理（`image-cleanup.js`）
4. `ToolRunner`で並列処理
5. ダウンロード

**背景除去**: `@imgly/background-removal`（CDN）を使用

#### 実装ライブラリ候補

**既存実装**:
- `Canvas API`: 画像処理
- `@imgly/background-removal` (CDN): 背景除去

**導入リスク**: 低（既に実装済み）

#### セキュリティと運用

**サイズ制限**: メモリ依存

**MIME検証**: `file-validation.js`で実装済み

**並列処理**: `ToolRunner`で最大2並列

#### 最小実装のスコープ

**MVP範囲**:
- ✅ 透過→白背景
- ✅ 余白トリム
- ✅ 縦横比統一
- ✅ 背景除去（`@imgly/background-removal`使用）

**次の一手**:
- 背景色のカスタマイズ
- トリム感度調整

---

### 3.4 議事録整形（`/tools/minutes`）

#### ユーザーがやりたいこと
- テキスト貼り付け → 決定事項/ToDo/担当/期限の抽出
- 見出し付き議事録テンプレート生成
- CSV/JSON出力

#### 入力と出力

**入力**:
- テキスト（テキストエリア貼り付け）
- 形式: プレーンテキスト

**出力**:
- 整形済み議事録（HTML/テキスト）
- CSV（決定事項、ToDo等）
- JSON（構造化データ）

#### 画面構成

**既存実装**: `templates/tools/minutes.html`（796行）

**セクション**:
1. ページヘッダー
2. テキスト入力エリア
3. 抽出オプション（決定事項/ToDo/担当/期限）
4. テンプレート選択
5. 実行ボタン
6. 結果表示（整形済み議事録）
7. ダウンロード（CSV/JSON）

#### バックエンド設計

**エンドポイント**: 不要（ブラウザ内処理）

**処理フロー**:
1. テキスト入力 → `MinutesParse`で解析（`minutes-parse.js`）
2. `MinutesExtract`で抽出（`minutes-extract.js`）
3. `MinutesTemplates`でテンプレート適用（`minutes-templates.js`）
4. `MinutesExport`で出力（`minutes-export.js`）

**主要関数**:
- `MinutesParse.parse()`: テキスト解析
- `MinutesExtract.extractDecisions()`: 決定事項抽出
- `MinutesExtract.extractTodos()`: ToDo抽出
- `MinutesTemplates.applyTemplate()`: テンプレート適用

#### 実装ライブラリ候補

**既存実装**: ルールベース（正規表現、キーワードマッチング）

**LLM使用**: なし（MVPではルールベース）

**導入リスク**: なし（既に実装済み）

#### セキュリティと運用

**サイズ制限**: テキスト長制限なし（メモリ依存）

**MIME検証**: 不要（テキスト入力）

**並列処理**: 不要（単一テキスト処理）

**タイムアウト**: なし

**削除**: メモリ内のみ

**監査ログ**: 不要（ブラウザ内処理）

#### テスト観点

**正常系**:
- 決定事項抽出（「決定: ...」形式）
- ToDo抽出（「TODO: ...」形式）
- 担当抽出（「担当: ...」形式）
- 期限抽出（日付形式）

**異常系**:
- 空テキスト
- 形式不明なテキスト

#### 最小実装のスコープ

**MVP範囲**:
- ✅ 決定事項抽出
- ✅ ToDo抽出
- ✅ 担当抽出
- ✅ 期限抽出
- ✅ テンプレート適用
- ✅ CSV/JSON出力

**次の一手**:
- LLM連携（より高精度な抽出）
- カスタムテンプレート
- 複数議事録の一括処理

---

### 3.5 Web/SEOユーティリティ（`/tools/seo`）

#### ユーザーがやりたいこと
- OGP画像生成（簡易）
- メタタグ検査（URL入力 → HTML取得 → メタタグ抽出）
- PageSpeedチェックリスト生成
- sitemap.xml生成
- robots.txt生成

#### 入力と出力

**入力**:
- OGP画像: タイトル、説明、画像URL
- メタタグ検査: URL
- sitemap/robots: サイト情報

**出力**:
- OGP画像: PNG/JPEG
- メタタグ検査: メタタグ一覧
- PageSpeedチェックリスト: マークダウン/HTML
- sitemap.xml: XML
- robots.txt: テキスト

#### 画面構成

**既存実装**: `templates/tools/seo.html`（1032行）

**セクション**:
1. ページヘッダー
2. 機能タブ（OGP/メタタグ/PageSpeed/sitemap/robots）
3. 入力フォーム
4. 実行ボタン
5. 結果表示
6. ダウンロード

#### バックエンド設計

**エンドポイント**: 一部必要（CORS回避のため）

**処理フロー**:
1. OGP画像: `Canvas API`で生成（`seo-ogp-canvas.js`）
2. メタタグ検査: `fetch()`でHTML取得 → パース（`seo-html-inspector.js`）
3. PageSpeed: チェックリスト生成（`seo-pagespeed-checklist.js`）
4. sitemap: XML生成（`seo-sitemap.js`）
5. robots: テキスト生成（`seo-robots.js`）

**CORS問題**: メタタグ検査で`fetch()`がCORSエラーになる可能性

**解決策**: プロキシエンドポイントが必要（`/api/fetch-html?url=...`）

#### 実装ライブラリ候補

**既存実装**:
- `Canvas API`: OGP画像生成
- バニラJS: メタタグパース

**導入リスク**: 中（CORS問題）

#### セキュリティと運用

**サイズ制限**: 不要

**MIME検証**: 不要

**並列処理**: 不要

**タイムアウト**: メタタグ検査で必要（10秒）

**削除**: メモリ内のみ

**監査ログ**: 不要

#### テスト観点

**正常系**:
- OGP画像生成
- メタタグ検査（正常なURL）
- PageSpeedチェックリスト生成
- sitemap.xml生成
- robots.txt生成

**異常系**:
- CORSエラー（メタタグ検査）
- タイムアウト
- 無効なURL

#### 最小実装のスコープ

**MVP範囲**:
- ✅ OGP画像生成
- ⚠️ メタタグ検査（CORS問題あり）
- ✅ PageSpeedチェックリスト
- ✅ sitemap.xml生成
- ✅ robots.txt生成

**次の一手**:
- メタタグ検査のプロキシ実装
- OGP画像のカスタマイズ強化
- PageSpeed API連携

---

## 4. IAと導線最適化案

### 4.1 現状の導線（問題点）

```
Home (/) 
  → AutoFill (/autofill) [利用可能]
  → Tools (/tools) 
      → image-batch [準備中表示]
      → pdf [準備中表示]
      → image-cleanup [準備中表示]
      → minutes [準備中表示]
      → seo [準備中表示]
```

**問題点**:
1. `landing.html`で「準備中」表示 → ユーザーがクリックしない
2. ツール間の回遊がない（各ツールページが孤立）
3. AutoFillが主力だが、他ツールへの導線が弱い
4. ナビゲーションが限定的（Home/AutoFill/Tools/Guideのみ）

### 4.2 あるべきサイトマップ案

```
Home (/)
  ├─ Hero Section
  │   └─ CTA: "Jobcan AutoFillを使う" → /autofill
  ├─ 製品一覧（動的、PRODUCTSから生成）
  │   ├─ AutoFill [利用可能] → /autofill
  │   ├─ 画像一括変換 [利用可能] → /tools/image-batch
  │   ├─ PDFユーティリティ [利用可能] → /tools/pdf
  │   ├─ 画像ユーティリティ [利用可能] → /tools/image-cleanup
  │   ├─ 議事録整形 [利用可能] → /tools/minutes
  │   └─ Web/SEOユーティリティ [利用可能] → /tools/seo
  └─ 信頼要素（セキュリティ、プライバシー）

Tools Hub (/tools)
  ├─ 検索機能（既存）
  ├─ カテゴリフィルター（画像/文書/テキスト/Web）
  └─ 製品カード（動的、PRODUCTSから生成）

Tool Detail (/tools/{tool-id})
  ├─ 機能説明
  ├─ 使い方
  ├─ 実行エリア
  └─ 関連ツール（回遊用）

AutoFill (/autofill)
  └─ 処理完了後: "他のツールも試す" → /tools

Docs
  ├─ Guide (/guide/getting-started)
  ├─ FAQ (/faq)
  └─ Best Practices (/best-practices)

Contact (/contact)
```

### 4.3 ナビゲーション設計

**ヘッダーナビ**（`templates/includes/header.html`）:
```
[Automation Hub] | Home | AutoFill | Tools | Guide
```

**フッター導線**（`templates/includes/footer.html`）:
```
ガイド | リソース | 法的情報
├─ 完全ガイド
├─ はじめての使い方
├─ Excelファイルの作成方法
├─ トラブルシューティング
├─ FAQ
├─ 用語集
├─ ブログ
└─ サイトについて
```

**改善案**: フッターに「ツール一覧」セクションを追加

### 4.4 各ページの主要CTA

**Home (`/`)**:
- プライマリCTA: "Jobcan AutoFillを使う" → `/autofill`
- セカンダリCTA: "すべてのツールを見る" → `/tools`

**Tools Hub (`/tools`)**:
- 各ツールカード: "使ってみる" → `/tools/{tool-id}`

**Tool Detail (`/tools/{tool-id}`)**:
- プライマリCTA: "ファイルを選択"（実行）
- セカンダリCTA: "他のツールを見る" → `/tools`

**AutoFill (`/autofill`)**:
- プライマリCTA: "ファイルをアップロード"
- 処理完了後: "他のツールも試す" → `/tools`

### 4.5 ツール間回遊の設計

**各ツールページに「関連ツール」セクションを追加**:

```html
<div class="related-tools" data-reveal>
    <h3>関連ツール</h3>
    <div class="tools-grid">
        {% for related in related_tools %}
            <a href="{{ related.path }}" class="tool-card">
                <div class="tool-icon">{{ related.icon }}</div>
                <div class="tool-name">{{ related.name }}</div>
            </a>
        {% endfor %}
    </div>
</div>
```

**関連ツールの定義**（`lib/routes.py`に追加）:
```python
RELATED_TOOLS = {
    'image-batch': ['image-cleanup', 'pdf'],  # 画像一括変換 → 画像ユーティリティ、PDF
    'pdf': ['image-batch', 'image-cleanup'],  # PDF → 画像一括変換、画像ユーティリティ
    'image-cleanup': ['image-batch', 'pdf'],  # 画像ユーティリティ → 画像一括変換、PDF
    'minutes': ['seo'],  # 議事録 → SEO
    'seo': ['minutes'],  # SEO → 議事録
    'autofill': ['tools']  # AutoFill → ツール一覧
}
```

### 4.6 AutoFillからの導線最適化

**処理完了後の画面**（`templates/autofill.html`）:
- 成功時: "🎉 処理が正常に完了しました"
- 追加CTA: "他のツールも試す" → `/tools`

**実装箇所**: `templates/autofill.html`の完了メッセージ部分

---

## 5. 実装計画

### 5.1 P0: 表示ロジック修正（即時、1-2時間）

**タスク**:
1. `app.py:341`の`/`ルートを修正して`PRODUCTS`を渡す
2. `templates/landing.html:255-290`を動的表示に変更
3. `app.py:411-434`のルートコメントから「準備中」を削除

**変更ファイル**:
- `app.py`（1箇所）
- `templates/landing.html`（1箇所）

**検証**:
- ブラウザで`/`にアクセスし、全ツールが「利用可能」表示されることを確認
- 各ツールリンクが正常に動作することを確認

**PR分割**: 1つのPRで対応可能

---

### 5.2 P1: 各ツールの動作確認とバグ修正（短期、各ツール1-2日）

#### 画像一括変換
**確認項目**:
- ファイル選択 → 変換 → ダウンロードの一連の流れ
- エラーハンドリング（ファイルサイズ超過、形式外）
- 進捗表示の動作
- ZIPダウンロードの動作

**想定バグ**:
- メモリ不足時のクラッシュ
- 進捗表示の不具合

#### PDFユーティリティ
**確認項目**:
- PDF結合/分割/抽出の動作
- PDF→画像変換の動作
- 画像→PDF変換の動作
- エラーハンドリング（破損PDF）

**想定バグ**:
- パスワード保護PDFのエラー
- メモリ不足

#### 画像ユーティリティ
**確認項目**:
- 透過→白背景変換
- 余白トリム
- 縦横比統一
- 背景除去（`@imgly/background-removal`の動作）

**想定バグ**:
- 背景除去のタイムアウト
- メモリ不足

#### 議事録整形
**確認項目**:
- テキスト解析の精度
- 決定事項/ToDo/担当/期限の抽出
- テンプレート適用
- CSV/JSON出力

**想定バグ**:
- 抽出精度の低さ
- テンプレート適用の不具合

#### Web/SEOユーティリティ
**確認項目**:
- OGP画像生成
- メタタグ検査（CORS問題の確認）
- PageSpeedチェックリスト生成
- sitemap.xml/robots.txt生成

**想定バグ**:
- メタタグ検査のCORSエラー
- タイムアウト

**PR分割**: ツールごとに1つのPR

---

### 5.3 P2: 情報設計最適化（中期、1週間）

#### タスク1: 関連ツールセクションの追加
**変更ファイル**:
- `lib/routes.py`: `RELATED_TOOLS`定義を追加
- `app.py`: 各ツールルートで`related_tools`を渡す
- `templates/tools/*.html`: 関連ツールセクションを追加

#### タスク2: AutoFill完了後の導線追加
**変更ファイル**:
- `templates/autofill.html`: 完了メッセージにCTA追加

#### タスク3: フッターにツール一覧追加
**変更ファイル**:
- `templates/includes/footer.html`: ツール一覧セクション追加

#### タスク4: ナビゲーション改善
**変更ファイル**:
- `templates/includes/header.html`: 必要に応じて改善

**PR分割**: 機能ごとに1つのPR（関連ツール、導線追加、フッター、ナビ）

---

### 5.4 リスクとロールバック

#### リスク1: メモリ不足
**影響**: 大量ファイル処理時にブラウザクラッシュ
**対策**: ファイル数制限の追加、進捗表示で警告
**ロールバック**: 制限値を調整

#### リスク2: CORS問題（SEOツール）
**影響**: メタタグ検査が動作しない
**対策**: プロキシエンドポイントの実装（`/api/fetch-html`）
**ロールバック**: メタタグ検査機能を一時無効化

#### リスク3: 外部ライブラリのCDN障害
**影響**: `pdf-lib`, `pdf.js`, `@imgly/background-removal`が読み込めない
**対策**: CDN障害時のフォールバック（ローカルホスト版の用意）
**ロールバック**: 該当ツールを一時無効化

---

## 6. 追加で確認したい前提

### 6.1 不明点（仮置き案付き）

1. **メタタグ検査のCORS問題**
   - **質問**: プロキシエンドポイントを実装するか、機能を無効化するか？
   - **仮置き案**: MVPでは機能を無効化し、P2でプロキシ実装

2. **ファイルサイズ制限**
   - **質問**: 各ツールで統一的なサイズ制限を設けるか？
   - **仮置き案**: ツールごとに適切な制限を設定（画像: 50MB、PDF: 100MB）

3. **並列処理数**
   - **質問**: `ToolRunner`の`maxConcurrency`を調整するか？
   - **仮置き案**: 現状の2並列を維持

4. **エラーログ**
   - **質問**: ブラウザ内エラーをサーバーに送信するか？
   - **仮置き案**: MVPでは送信せず、P2で実装

5. **利用統計**
   - **質問**: 各ツールの利用状況をトラッキングするか？
   - **仮置き案**: MVPでは実装せず、P2でGoogle Analytics連携

---

## 7. 変更ファイル一覧と差分の当たり

### 7.1 P0: 表示ロジック修正

#### `app.py`
**変更箇所**: 341行目付近
```python
# 修正前
@app.route('/')
def index():
    """メインページ"""
    return render_template('landing.html')

# 修正後
@app.route('/')
def index():
    """メインページ"""
    from lib.routes import PRODUCTS
    return render_template('landing.html', products=PRODUCTS)
```

**変更箇所**: 411-434行目（コメント修正）
```python
# 修正前
@app.route('/tools/image-batch')
def tools_image_batch():
    """画像一括変換ツール（準備中）"""
    return render_template('tools/image-batch.html')

# 修正後
@app.route('/tools/image-batch')
def tools_image_batch():
    """画像一括変換ツール"""
    return render_template('tools/image-batch.html')
```

#### `templates/landing.html`
**変更箇所**: 255-290行目
```jinja2
{# 修正前: ハードコード #}
<a href="/autofill" class="product-card">
    <h3>🕒 Jobcan AutoFill</h3>
    <p>Jobcanへの勤怠データをExcelから一括入力。月次締め作業を大幅に短縮します。</p>
    <span class="status available">利用可能</span>
</a>
<a href="/tools/image-batch" class="product-card">
    <h3>🖼️ 画像一括変換</h3>
    <p>png/jpg/webpの一括変換、リサイズ、品質圧縮、複数サイズ同時出力に対応予定。</p>
    <span class="status coming-soon">準備中</span>
</a>
# ... 同様に4つ

{# 修正後: 動的表示 #}
{% for product in products %}
    <a href="{{ product.path }}" class="product-card">
        <h3>{{ product.icon }} {{ product.name }}</h3>
        <p>{{ product.description }}</p>
        <span class="status {{ product.status }}">
            {% if product.status == 'available' %}利用可能{% else %}準備中{% endif %}
        </span>
    </a>
{% endfor %}
```

---

### 7.2 P1: 動作確認とバグ修正

**変更ファイル**: 各ツールページのテンプレート、JSファイル
**差分の当たり**: エラーハンドリングの追加、進捗表示の改善、メモリ制限の追加

---

### 7.3 P2: 情報設計最適化

#### `lib/routes.py`
**追加**: `RELATED_TOOLS`定義
```python
RELATED_TOOLS = {
    'image-batch': ['image-cleanup', 'pdf'],
    'pdf': ['image-batch', 'image-cleanup'],
    'image-cleanup': ['image-batch', 'pdf'],
    'minutes': ['seo'],
    'seo': ['minutes'],
    'autofill': ['tools']
}
```

#### `app.py`
**変更**: 各ツールルートで`related_tools`を渡す
```python
@app.route('/tools/image-batch')
def tools_image_batch():
    from lib.routes import PRODUCTS, RELATED_TOOLS
    related_ids = RELATED_TOOLS.get('image-batch', [])
    related_tools = [p for p in PRODUCTS if p['id'] in related_ids]
    return render_template('tools/image-batch.html', related_tools=related_tools)
```

#### `templates/tools/*.html`
**追加**: 関連ツールセクション（各ツールページの最後に追加）

#### `templates/autofill.html`
**変更**: 完了メッセージにCTA追加
```html
<div class="completion-cta" data-reveal>
    <p>🎉 処理が正常に完了しました</p>
    <a href="/tools" class="btn btn-secondary">他のツールも試す</a>
</div>
```

#### `templates/includes/footer.html`
**追加**: ツール一覧セクション

---

## 8. まとめ

### 実装の優先順位

1. **P0（即時、1-2時間）**: 表示ロジック修正のみ
2. **P1（短期、各ツール1-2日）**: 動作確認とバグ修正
3. **P2（中期、1週間）**: 情報設計最適化

### 重要な設計判断

1. **ブラウザ内処理**: 全ツールがブラウザ内完結のため、サーバー側API実装は不要
2. **データソース統一**: `lib/routes.py`の`PRODUCTS`を唯一の情報源とする
3. **段階的リリース**: P0で表示解除 → P1で動作確認 → P2で最適化

### 次のアクション

1. P0の実装（表示ロジック修正）
2. 各ツールの動作確認
3. バグ修正
4. P2の実装（情報設計最適化）

---

**レポート作成完了**: 2026-02-03
