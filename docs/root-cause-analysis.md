# トップページエラー原因特定レポート

**作成日**: 2026-02-05  
**対象URL**: https://jobcan-automation.onrender.com/  
**現象**: トップページが断続的にエラーページ（error.html）を表示する

---

## 1. 原因特定

### 現象
- トップページ（`/`）にアクセスすると、断続的に「⚠️ エラーが発生しました」というエラーページが表示される
- 正常にHTMLが返されるケースも観測されるため、恒常的な404ではなく「断続的な500」または「特定条件で落ちる」可能性が高い

### 原因（推定）

#### 仮説1: context_processorでのPRODUCTSインポート失敗（最有力）

**証跡**:
- `app.py:221-270`の`inject_env_vars()`関数で`from lib.routes import PRODUCTS`を実行
- エラーが発生した場合、空のリスト`[]`を返す（255-270行目）
- しかし、エラーログは記録されるが、テンプレートレンダリング時に別のエラーが発生する可能性がある

**該当コード**:
```python
@app.context_processor
def inject_env_vars():
    try:
        from lib.routes import PRODUCTS
        # ...
        return {'products': PRODUCTS, ...}
    except Exception as e:
        # エラー時は空のリストを返す
        return {'products': [], ...}
```

**問題点**:
- `lib/routes.py`のインポートに失敗した場合、循環参照やモジュール初期化の問題が発生する可能性がある
- エラーがログに記録されるが、テンプレートレンダリング時に`products`が空のリストになる
- `landing.html:268`で`{% for product in products %}`を使用しているが、`products`が未定義の場合にエラーが発生する可能性がある

#### 仮説2: テンプレート変数の未定義参照

**証跡**:
- `templates/landing.html:268`で`{% for product in products %}`を使用
- `templates/includes/footer.html:9, 25, 28`で`{% if products %}`と`{% for product in products %}`を使用
- `templates/includes/structured_data.html:43`で`request.path`を使用

**問題点**:
- `context_processor`でエラーが発生した場合、`products`が空のリストになるが、テンプレートで`products`が未定義になる可能性がある
- `request`が未定義の場合、`structured_data.html:43`でエラーが発生する可能性がある

#### 仮説3: ルート関数でのPRODUCTSインポート失敗

**証跡**:
- `app.py:472-492`の`index()`関数で`from lib.routes import PRODUCTS`を実行
- エラーが発生した場合、例外を再発生させてエラーハンドラに委譲（492行目）

**問題点**:
- `lib/routes.py`のインポートに失敗した場合、例外が発生してエラーページが表示される
- しかし、エラーログは記録されるため、原因は追跡可能

---

## 2. 修正方針

### 最小修正案（即効性重視）

1. **テンプレート変数の安全な参照**
   - `landing.html`で`products`が未定義の場合のフォールバックを追加
   - `footer.html`で`products`が未定義の場合のフォールバックを追加
   - `structured_data.html`で`request`が未定義の場合のフォールバックを追加

2. **context_processorのエラーハンドリング改善**
   - エラー発生時に空のリストではなく、デフォルト値を返す
   - エラーログをより詳細に記録

### 恒久対策案（再発防止）

1. **ログ強化**
   - すべての例外で`app.logger.exception()`を使用してスタックトレースを記録
   - `request_id`をエラーページに表示して、ユーザー報告とログを紐付ける

2. **テンプレートの堅牢化**
   - すべてのテンプレート変数にデフォルト値を設定
   - `|default`フィルタを使用して未定義変数を安全に処理

3. **起動時の検証**
   - アプリケーション起動時に主要テンプレートの存在を確認
   - `PRODUCTS`のインポートを起動時に検証

4. **簡易テストの追加**
   - Flask test clientでトップページが200を返すことをテスト
   - エラーハンドラが例外を握りつぶさずログされることをテスト

---

## 3. 実装パッチ

以下の修正を実装します：

1. `app.py`: context_processorのエラーハンドリング改善、ログ強化
2. `templates/landing.html`: productsが未定義の場合のフォールバック追加
3. `templates/includes/footer.html`: productsが未定義の場合のフォールバック追加
4. `templates/includes/structured_data.html`: requestが未定義の場合のフォールバック追加
5. 起動時のテンプレート検証機能追加
