# エラーハンドリング修正サマリー

**作成日**: 2026-02-05  
**目的**: トップページ（/）がエラーページを表示してしまう問題の解消

---

## 変更ファイル

### 1. `app.py`
- **エラーハンドラの改善**
  - `_generate_error_id()`: エラーID生成関数を追加
  - `_render_error_page()`: エラーページレンダリング共通関数を追加
  - `@app.errorhandler(404)`: JSONからHTMLエラーページに変更、error_id追加
  - `@app.errorhandler(500)`: JSONからHTMLエラーページに変更、error_idとスタックトレース追加
  - `@app.errorhandler(503)`: JSONからHTMLエラーページに変更、error_id追加
  - `@app.errorhandler(Exception)`: HTTPExceptionの適切な処理、HTMLエラーページ返却

- **トップページルート関数の修正**
  - `@app.route('/')`: 例外を握りつぶさず、エラーハンドラに委譲するように変更
  - `@app.route('/autofill')`: 同様に修正

- **context_processorの改善**
  - `inject_env_vars()`: エラーハンドリングを追加、エラー時は空のリストを返す（テンプレートエラーを防ぐ）

### 2. `templates/error.html`
- エラーID表示セクションを追加
- エラーIDが存在する場合に表示

---

## 主な変更点

### 1. エラーハンドラの統一
- **変更前**: 404/500/503はJSONを返していた
- **変更後**: すべてHTMLエラーページ（error.html）を返すように統一

### 2. エラーIDの追加
- すべてのエラーに一意のエラーID（8文字のUUID）を生成
- ログと画面の両方にエラーIDを出力
- ユーザーが問い合わせ時にエラーIDを伝えられるように

### 3. ログ強化
- 500エラー時にスタックトレースをログに記録
- エラーID、リクエストID、パス、メソッドをログに含める

### 4. 例外処理の改善
- トップページのルート関数で例外を握りつぶさない
- 例外を再発生させて、エラーハンドラに処理させる
- HTTPException（Flaskの標準例外）を適切に処理

### 5. context_processorの堅牢化
- PRODUCTSのインポートエラーを捕捉
- エラー時は空のリストを返してテンプレートエラーを防ぐ

---

## 検証手順

### 1. ローカル環境での検証

#### 1.1 正常系の確認
```bash
# トップページが200を返すことを確認
curl -i http://localhost:5000/

# レスポンスボディにエラーページ固有の文言（「⚠️ エラーが発生しました」）が含まれないことを確認
curl http://localhost:5000/ | grep -v "⚠️ エラーが発生しました"
```

#### 1.2 404エラーの確認
```bash
# 存在しないページが404を返すことを確認
curl -i http://localhost:5000/this-page-does-not-exist

# レスポンスボディにエラーページが含まれることを確認
curl http://localhost:5000/this-page-does-not-exist | grep "⚠️ エラーが発生しました"
```

#### 1.3 エラーIDの確認
```bash
# 404エラーページにエラーIDが含まれることを確認
curl http://localhost:5000/this-page-does-not-exist | grep "エラーID"
```

### 2. 本番環境での検証

#### 2.1 トップページの確認（複数回実行）
```bash
# 複数回実行して、常に200を返すことを確認
for i in {1..5}; do
  echo "=== Attempt $i ==="
  curl -i https://jobcan-automation.onrender.com/ 2>&1 | head -20
  sleep 2
done
```

#### 2.2 他のページの確認
```bash
# /tools が200を返すことを確認
curl -i https://jobcan-automation.onrender.com/tools

# /about が200を返すことを確認
curl -i https://jobcan-automation.onrender.com/about
```

#### 2.3 404エラーの確認
```bash
# 存在しないページが404を返すことを確認
curl -i https://jobcan-automation.onrender.com/this-page-does-not-exist
```

### 3. ログの確認

#### 3.1 Renderログの確認
- Renderダッシュボードでログを確認
- エラーIDがログに出力されていることを確認
- 500エラー時にスタックトレースが出力されていることを確認

#### 3.2 エラーIDの追跡
- エラーページに表示されたエラーIDを記録
- ログで同じエラーIDを検索して、詳細なエラー情報を確認

---

## 期待される動作

### 正常系
- `/` は常に200を返し、正しいランディングページを表示
- エラーページ固有の文言（「⚠️ エラーが発生しました」）が含まれない

### エラー系
- 404エラーは404ステータスでHTMLエラーページを返す
- 500エラーは500ステータスでHTMLエラーページを返す
- すべてのエラーページにエラーIDが表示される
- ログにエラーID、リクエストID、スタックトレースが記録される

---

## 注意事項

1. **context_processorのエラー**
   - PRODUCTSのインポートに失敗した場合、空のリストを返す
   - これにより、テンプレートエラーを防ぐが、productsが空になる可能性がある
   - 本番環境でproductsが空になる場合は、lib/routes.pyのインポートエラーを確認

2. **エラーテンプレートのレンダリング失敗**
   - error.htmlのレンダリングに失敗した場合、シンプルなHTMLを返す
   - この場合もエラーIDは表示される

3. **HTTPステータスコード**
   - 正常系では200を返す（エラーページを200で返さない）
   - エラー時は適切なステータスコード（404/500/503）を返す

---

## トラブルシューティング

### トップページがまだエラーページを表示する場合

1. **ログを確認**
   - RenderログでエラーIDを検索
   - スタックトレースを確認して原因を特定

2. **context_processorの確認**
   - PRODUCTSのインポートが成功しているか確認
   - lib/routes.pyに構文エラーがないか確認

3. **テンプレートの確認**
   - landing.htmlに構文エラーがないか確認
   - テンプレート変数が正しく定義されているか確認

### エラーIDが表示されない場合

1. **error.htmlの確認**
   - error_id変数が正しく渡されているか確認
   - テンプレートの構文エラーがないか確認

---

## 関連ファイル

- `app.py` - エラーハンドラとルート関数
- `templates/error.html` - エラーページテンプレート
- `lib/routes.py` - PRODUCTS定義（context_processorで使用）
