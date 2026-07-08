# トップページエラー修正実装サマリー

**作成日**: 2026-02-05  
**目的**: トップページが断続的にエラーページを表示する問題の修正

---

## 1. 原因特定

### 現象
- トップページ（`/`）にアクセスすると、断続的に「⚠️ エラーが発生しました」というエラーページが表示される
- 正常にHTMLが返されるケースも観測されるため、恒常的な404ではなく「断続的な500」または「特定条件で落ちる」可能性が高い

### 根本原因

#### 仮説1: context_processorでのPRODUCTSインポート失敗（最有力）

**証跡**:
- `app.py:258-295`の`inject_env_vars()`関数で`from lib.routes import PRODUCTS`を実行
- エラーが発生した場合、空のリスト`[]`を返す（285-295行目）
- しかし、テンプレートレンダリング時に`products`が未定義になる可能性がある

**該当コード**:
- `app.py:258-295`: `inject_env_vars()`関数
- `templates/landing.html:268`: `{% for product in products %}`
- `templates/includes/footer.html:9, 25, 28`: `{% if products %}`と`{% for product in products %}`

#### 仮説2: テンプレート変数の未定義参照

**証跡**:
- `templates/includes/structured_data.html:43`で`request.path`を使用
- `request`が未定義の場合、エラーが発生する可能性がある

---

## 2. 修正内容

### 2.1 テンプレート変数の安全な参照

#### `templates/landing.html`
- `products`が未定義の場合のフォールバックを追加（`|default([])`）
- 各プロパティにデフォルト値を設定（`|default(...)`）
- `{% else %}`ブロックを追加して、productsが空の場合のメッセージを表示

#### `templates/includes/footer.html`
- `products`が未定義の場合のフォールバックを追加（`|default([])`）
- 各プロパティにデフォルト値を設定（`|default(...)`）

#### `templates/includes/structured_data.html`
- `request`が未定義の場合のチェックを追加（`{% if request and request.path != '/' %}`）
- `request.path`を`current_path`変数に格納して安全に参照

### 2.2 context_processorのエラーハンドリング改善

#### `app.py:258-295`
- `logger.exception()`を使用してスタックトレースを確実に記録
- エラー発生時も空のリストを返してテンプレートエラーを防ぐ

### 2.3 エラーハンドラのログ強化

#### `app.py:192-210, 240-255`
- `logger.exception()`を使用してスタックトレースを確実に記録
- すべての例外で詳細なログを出力

### 2.4 起動時の検証機能追加

#### `app.py:51-90`
- アプリケーション起動時に主要テンプレートの存在を確認
- `PRODUCTS`のインポートを起動時に検証
- エラーがあっても起動は続行（本番環境で起動できないのを防ぐ）

---

## 3. 変更ファイル一覧

1. `app.py` - エラーハンドリング改善、起動時検証追加
2. `templates/landing.html` - テンプレート変数の安全な参照
3. `templates/includes/footer.html` - テンプレート変数の安全な参照
4. `templates/includes/structured_data.html` - requestの安全な参照
5. `tests/test_index_page.py` - 簡易テスト追加（新規）
6. `docs/root-cause-analysis.md` - 原因特定レポート（新規）
7. `docs/verification-procedures.md` - 検証手順書（新規）
8. `docs/fix-implementation-summary.md` - 実装サマリー（本ファイル）

---

## 4. 実装パッチ（主要な変更）

### 4.1 app.py

```python
# 起動時の検証機能追加
def validate_startup():
    """アプリケーション起動時に主要リソースの存在を確認"""
    # テンプレートとPRODUCTSの存在確認

# context_processorのエラーハンドリング改善
@app.context_processor
def inject_env_vars():
    try:
        # ...
    except Exception as e:
        logger.exception(...)  # logger.exception()を使用

# エラーハンドラのログ強化
@app.errorhandler(500)
def internal_error(error):
    logger.exception(...)  # logger.exception()を使用

@app.errorhandler(Exception)
def handle_exception(e):
    logger.exception(...)  # logger.exception()を使用
```

### 4.2 templates/landing.html

```jinja2
{% for product in products|default([]) %}
    <a href="{{ product.path|default('#') }}" class="product-card">
        <h3>{{ product.icon|default('📦') }} {{ product.name|default('製品') }}</h3>
        <p>{{ product.description|default('説明がありません') }}</p>
        <span class="status {{ 'available' if product.status|default('coming-soon') == 'available' else 'coming-soon' }}">
            {% if product.status|default('coming-soon') == 'available' %}利用可能{% else %}準備中{% endif %}
        </span>
    </a>
{% else %}
    <p>製品情報を読み込めませんでした。しばらく待ってから再試行してください。</p>
{% endfor %}
```

### 4.3 templates/includes/footer.html

```jinja2
{% if products|default([]) %}
    {% for product in products %}
        {% if product.status|default('coming-soon') == 'available' %}
            <a href="{{ product.path|default('#') }}">{{ product.icon|default('📦') }} {{ product.name|default('製品') }}</a>
        {% endif %}
    {% endfor %}
{% endif %}
```

### 4.4 templates/includes/structured_data.html

```jinja2
{% if request and request.path != '/' %}
    {% set current_path = request.path|default('/') %}
    {% if current_path.startswith('/tools/') and current_path != '/tools' %}
        ...
    {% endif %}
{% endif %}
```

---

## 5. 検証手順

詳細は `docs/verification-procedures.md` を参照。

### ローカル環境
1. アプリケーションを起動
2. 起動ログで検証結果を確認
3. `curl`または`Invoke-WebRequest`でトップページを確認
4. 複数回リクエストして安定性を確認
5. 404エラーの確認

### 本番環境
1. トップページを複数回リクエスト（10回以上）
2. 他のページ（/tools, /about, /autofill）の確認
3. 404エラーの確認
4. レスポンスヘッダの確認（X-Request-ID）

### Renderログ
1. 起動ログの確認（`startup_validation_passed`）
2. エラーログの確認（`context_processor_error`, `landing_page_error`等）
3. エラーIDの追跡

---

## 6. 監視/デバッグ強化

### 6.1 ログ強化
- すべての例外で`logger.exception()`を使用してスタックトレースを記録
- エラーIDをログと画面の両方に出力
- リクエストIDをレスポンスヘッダに付与

### 6.2 起動時検証
- 主要テンプレートの存在確認
- `PRODUCTS`のインポート確認
- エラーがあっても起動は続行（本番環境で起動できないのを防ぐ）

### 6.3 簡易テスト
- Flask test clientでトップページが200を返すことをテスト
- エラーページが表示されないことをテスト
- 404エラーが正しく処理されることをテスト

---

## 7. 再発防止策

1. **テンプレート変数の安全な参照**
   - すべてのテンプレート変数に`|default`フィルタを使用
   - 未定義変数を安全に処理

2. **例外ログの強化**
   - `logger.exception()`を使用してスタックトレースを確実に記録
   - エラーIDをログと画面の両方に出力

3. **起動時の検証**
   - アプリケーション起動時に主要リソースの存在を確認
   - エラーがあっても起動は続行（本番環境で起動できないのを防ぐ）

4. **簡易テストの追加**
   - Flask test clientで基本的な動作をテスト
   - CI/CDパイプラインに組み込むことを推奨

---

## 8. 注意事項

1. **context_processorのエラー**
   - `PRODUCTS`のインポートに失敗した場合、空のリストを返す
   - これにより、テンプレートエラーを防ぐが、productsが空になる可能性がある
   - 本番環境でproductsが空になる場合は、`lib/routes.py`のインポートエラーを確認

2. **起動時検証**
   - エラーがあっても起動は続行する（本番環境で起動できないのを防ぐ）
   - エラーはログに記録されるため、原因を追跡可能

3. **テンプレートの互換性**
   - 既存のテンプレートとの互換性を維持
   - `|default`フィルタを使用することで、後方互換性を確保

---

## 9. 次のステップ

1. **本番環境へのデプロイ**
   - 変更をコミット・プッシュ
   - Renderでデプロイ

2. **検証の実施**
   - `docs/verification-procedures.md`に従って検証
   - 複数回リクエストして安定性を確認

3. **ログの監視**
   - Renderログでエラーが発生していないか確認
   - エラーIDを追跡して原因を特定

4. **継続的な改善**
   - 簡易テストをCI/CDパイプラインに組み込む
   - 定期的にログを確認して問題を早期発見
