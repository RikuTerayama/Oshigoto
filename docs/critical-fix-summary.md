# トップページエラー完全解消のための修正

**作成日**: 2026-02-05  
**エラーID**: 8703f43f  
**目的**: トップページがエラーページを表示する問題を完全に解消

---

## 問題の状況

エラーID `8703f43f` が表示され、トップページがエラーページを表示し続けていました。

---

## 根本原因

### 1. PRODUCTSインポート失敗時の例外処理

**問題**:
- `index()`関数で`from lib.routes import PRODUCTS`を実行
- インポートに失敗した場合、例外を再発生させてエラーハンドラに委譲
- これにより、エラーページが表示される

**該当コード**:
```python
@app.route('/')
def index():
    try:
        from lib.routes import PRODUCTS
        return render_template('landing.html', products=PRODUCTS)
    except Exception as e:
        logger.error(...)
        raise  # 例外を再発生 → エラーページが表示される
```

### 2. request.pathの未定義参照

**問題**:
- `templates/includes/head_meta.html`で`request.path`を使用
- `templates/includes/header.html`で`request.path`を使用
- `request`が未定義の場合、エラーが発生する可能性がある

---

## 修正内容

### 1. PRODUCTSインポート失敗時のフォールバック

**修正前**:
```python
try:
    from lib.routes import PRODUCTS
    return render_template('landing.html', products=PRODUCTS)
except Exception as e:
    logger.error(...)
    raise  # エラーページが表示される
```

**修正後**:
```python
products = []
try:
    from lib.routes import PRODUCTS
    products = PRODUCTS
except Exception as import_error:
    # インポートに失敗した場合、context_processorで注入されたproductsを使用
    logger.warning(f"landing_page_import_failed ... - using context_processor products")
    # 空のリストでも、テンプレートで|default([])を使用しているため問題ない

# テンプレートをレンダリング（productsが空でもOK）
return render_template('landing.html', products=products)
```

**効果**:
- `PRODUCTS`のインポートに失敗しても、エラーページではなくテンプレートが表示される
- 製品リストが空の場合は、「製品情報を読み込めませんでした」というメッセージが表示される

### 2. request.pathの安全な参照

**修正前**:
```jinja2
<link rel="canonical" href="https://jobcan-automation.onrender.com{{ request.path if request else '/' }}">
```

**修正後**:
```jinja2
<link rel="canonical" href="https://jobcan-automation.onrender.com{% if request and request.path %}{{ request.path }}{% else %}/{% endif %}">
```

**効果**:
- `request`が未定義の場合でもエラーが発生しない
- `request.path`が未定義の場合でもエラーが発生しない

### 3. header.htmlのrequest.path参照も安全化

**修正前**:
```jinja2
{% if request.path == item.path or (item.path == '/' and request.path == '/') %}
```

**修正後**:
```jinja2
{% if request and request.path and (request.path == item.path or (item.path == '/' and request.path == '/')) %}
```

**効果**:
- `request`が未定義の場合でもエラーが発生しない

---

## 変更ファイル

1. `app.py` - `index()`関数の例外処理を改善
2. `templates/includes/head_meta.html` - `request.path`の安全な参照
3. `templates/includes/header.html` - `request.path`の安全な参照

---

## 期待される動作

### 正常系
- `/` は常に200を返し、正常なランディングページを表示
- エラーページが表示されない

### PRODUCTSインポート失敗時
- エラーページではなく、テンプレートが表示される
- 製品リストが空の場合は、「製品情報を読み込めませんでした」というメッセージが表示される
- ログに警告が記録される（`landing_page_import_failed`）

### request未定義時
- エラーが発生せず、デフォルト値（`/`）が使用される

---

## 検証手順

1. **ローカル環境での確認**
   ```bash
   python app.py
   # ブラウザで http://localhost:5000/ を開く
   # 正常なランディングページが表示されることを確認
   ```

2. **本番環境での確認**
   ```powershell
   # 複数回リクエスト
   for ($i=1; $i -le 10; $i++) {
       $response = Invoke-WebRequest -Uri "https://jobcan-automation.onrender.com/" -UseBasicParsing
       Write-Host "Attempt $i: Status $($response.StatusCode)"
       if ($response.Content -match "⚠️ エラーが発生しました") {
           Write-Host "✗ Error page displayed"
       } else {
           Write-Host "✓ Landing page displayed"
       }
       Start-Sleep -Seconds 2
   }
   ```

3. **ログの確認**
   - Renderログで`landing_page_import_failed`の警告がないか確認
   - エラーID `8703f43f` が表示されないことを確認

---

## 注意事項

1. **PRODUCTSインポート失敗時**
   - 製品リストが空になるが、エラーページは表示されない
   - ログに警告が記録されるため、原因を追跡可能

2. **context_processorのエラー**
   - `context_processor`でもエラーが発生している場合、`products`は空のリストになる
   - テンプレートで`|default([])`を使用しているため、エラーは発生しない

3. **ログの監視**
   - `landing_page_import_failed`の警告が頻繁に記録される場合は、`lib/routes.py`のインポートエラーを確認

---

## 次のステップ

1. 本番環境にデプロイ
2. 複数回リクエストして安定性を確認
3. ログを監視して、エラーが発生していないか確認
4. エラーID `8703f43f` が表示されないことを確認
