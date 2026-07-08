# 検証手順書

**作成日**: 2026-02-05  
**目的**: トップページエラー修正の検証

---

## 1. ローカル環境での検証

### 1.1 アプリケーションの起動

```bash
# 仮想環境をアクティベート（必要に応じて）
# python -m venv venv
# source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# アプリケーションを起動
python app.py
# または
flask run
```

### 1.2 起動ログの確認

起動時に以下のログが表示されることを確認：

```
INFO startup_validation_passed all checks OK
```

エラーがある場合：

```
ERROR startup_validation_failed errors=[...]
```

### 1.3 トップページの確認（curl）

```bash
# Windows PowerShellの場合
$response = Invoke-WebRequest -Uri "http://localhost:5000/" -UseBasicParsing
Write-Host "Status: $($response.StatusCode)"
Write-Host "Content-Type: $($response.Headers['Content-Type'])"

# レスポンスボディにエラーページ固有の文言が含まれないことを確認
$body = $response.Content
if ($body -notmatch "⚠️ エラーが発生しました") {
    Write-Host "✓ 正常なランディングページが表示されています"
} else {
    Write-Host "✗ エラーページが表示されています"
}
```

### 1.4 複数回リクエストの確認

```powershell
# PowerShell
for ($i=1; $i -le 5; $i++) {
    Write-Host "`n=== Attempt $i ==="
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:5000/" -UseBasicParsing
        Write-Host "Status: $($response.StatusCode)"
        if ($response.StatusCode -eq 200 -and $response.Content -notmatch "⚠️ エラーが発生しました") {
            Write-Host "✓ OK"
        } else {
            Write-Host "✗ Error"
        }
    } catch {
        Write-Host "✗ Exception: $_"
    }
    Start-Sleep -Seconds 1
}
```

### 1.5 404エラーの確認

```bash
# 存在しないページが404を返すことを確認
$response = Invoke-WebRequest -Uri "http://localhost:5000/this-page-does-not-exist" -UseBasicParsing
Write-Host "Status: $($response.StatusCode)"
# 期待結果: 404

# エラーページが表示されることを確認
$body = $response.Content
if ($body -match "⚠️ エラーが発生しました") {
    Write-Host "✓ エラーページが表示されています"
}
if ($body -match "エラーID") {
    Write-Host "✓ エラーIDが表示されています"
}
```

### 1.6 簡易テストの実行（オプション）

```bash
# pytestがインストールされている場合
pytest tests/test_index_page.py -v

# pytestがインストールされていない場合
python tests/test_index_page.py
```

---

## 2. 本番環境での検証

### 2.1 トップページの確認（複数回実行）

```powershell
# PowerShell
for ($i=1; $i -le 10; $i++) {
    Write-Host "`n=== Attempt $i ==="
    try {
        $response = Invoke-WebRequest -Uri "https://jobcan-automation.onrender.com/" -UseBasicParsing
        Write-Host "Status: $($response.StatusCode)"
        Write-Host "Request-ID: $($response.Headers['X-Request-ID'])"
        
        if ($response.StatusCode -eq 200) {
            $body = $response.Content
            if ($body -notmatch "⚠️ エラーが発生しました") {
                Write-Host "✓ OK - 正常なランディングページ"
            } else {
                Write-Host "✗ Error - エラーページが表示されています"
                # エラーIDを抽出
                if ($body -match "エラーID[:\s]+([a-f0-9]{8})") {
                    $errorId = $matches[1]
                    Write-Host "Error ID: $errorId"
                }
            }
        } else {
            Write-Host "✗ Unexpected status: $($response.StatusCode)"
        }
    } catch {
        Write-Host "✗ Exception: $_"
    }
    Start-Sleep -Seconds 2
}
```

### 2.2 他のページの確認

```powershell
# /tools
$response = Invoke-WebRequest -Uri "https://jobcan-automation.onrender.com/tools" -UseBasicParsing
Write-Host "/tools Status: $($response.StatusCode)"

# /about
$response = Invoke-WebRequest -Uri "https://jobcan-automation.onrender.com/about" -UseBasicParsing
Write-Host "/about Status: $($response.StatusCode)"

# /autofill
$response = Invoke-WebRequest -Uri "https://jobcan-automation.onrender.com/autofill" -UseBasicParsing
Write-Host "/autofill Status: $($response.StatusCode)"
```

### 2.3 404エラーの確認

```powershell
try {
    $response = Invoke-WebRequest -Uri "https://jobcan-automation.onrender.com/this-page-does-not-exist" -UseBasicParsing
} catch {
    $response = $_.Exception.Response
}
Write-Host "Status: $($response.StatusCode)"
# 期待結果: 404
```

### 2.4 レスポンスヘッダの確認

```powershell
$response = Invoke-WebRequest -Uri "https://jobcan-automation.onrender.com/" -UseBasicParsing
Write-Host "X-Request-ID: $($response.Headers['X-Request-ID'])"
Write-Host "Content-Type: $($response.Headers['Content-Type'])"
```

---

## 3. Renderログの確認

### 3.1 起動ログの確認

Renderダッシュボードで、アプリケーション起動時のログを確認：

```
INFO startup_validation_passed all checks OK
```

エラーがある場合：

```
ERROR startup_validation_failed errors=[...]
```

### 3.2 エラーログの確認

エラーが発生した場合、以下のログが記録されることを確認：

```
ERROR context_processor_error rid=xxxx error=...
ERROR landing_page_error rid=xxxx error=...
ERROR internal_server_error error_id=xxxxxxxx rid=xxxx ...
ERROR unhandled_exception error_id=xxxxxxxx rid=xxxx ...
```

### 3.3 エラーIDの追跡

エラーページに表示されたエラーIDを記録し、ログで検索：

```
error_id=xxxxxxxx
```

同じエラーIDがログに記録されていることを確認。

---

## 4. ブラウザでの確認

### 4.1 トップページの表示

1. ブラウザで `https://jobcan-automation.onrender.com/` を開く
2. 正常なランディングページが表示されることを確認
3. 「⚠️ エラーが発生しました」が表示されないことを確認

### 4.2 開発者ツールでの確認

1. ブラウザの開発者ツール（F12）を開く
2. Networkタブでリクエストを確認
3. ステータスコードが200であることを確認
4. レスポンスヘッダに`X-Request-ID`が含まれることを確認

### 4.3 エラーページの確認

1. 存在しないページ（例: `/this-page-does-not-exist`）にアクセス
2. 404エラーページが表示されることを確認
3. エラーIDが表示されることを確認

---

## 5. 期待される結果

### 正常系
- `/` は常に200を返し、正常なランディングページを表示
- エラーページ固有の文言（「⚠️ エラーが発生しました」）が含まれない
- レスポンスヘッダに`X-Request-ID`が含まれる

### エラー系
- 404エラーは404ステータスでHTMLエラーページを返す
- 500エラーは500ステータスでHTMLエラーページを返す
- すべてのエラーページにエラーIDが表示される
- ログにエラーID、リクエストID、スタックトレースが記録される

---

## 6. トラブルシューティング

### トップページがまだエラーページを表示する場合

1. **ログを確認**
   - RenderログでエラーIDを検索
   - スタックトレースを確認して原因を特定

2. **context_processorの確認**
   - `context_processor_error`のログを確認
   - `lib/routes.py`のインポートエラーがないか確認

3. **テンプレートの確認**
   - `landing.html`に構文エラーがないか確認
   - テンプレート変数が正しく定義されているか確認

### エラーIDが表示されない場合

1. **error.htmlの確認**
   - `error_id`変数が正しく渡されているか確認
   - テンプレートの構文エラーがないか確認

---

## 7. 検証チェックリスト

- [ ] ローカル環境で `/` が200を返す
- [ ] ローカル環境で `/` のレスポンスボディにエラーページが含まれない
- [ ] ローカル環境で `/this-page-does-not-exist` が404を返す
- [ ] 本番環境で `/` が200を返す（複数回実行）
- [ ] 本番環境で `/` のレスポンスボディにエラーページが含まれない
- [ ] 本番環境で `/tools` が200を返す
- [ ] 本番環境で `/about` が200を返す
- [ ] 本番環境で `/this-page-does-not-exist` が404を返す
- [ ] エラーページにエラーIDが表示される
- [ ] ログにエラーIDが記録される
- [ ] 起動時に検証ログが表示される
