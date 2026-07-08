# RailwayからRenderへの移行ガイド

## なぜRenderを推奨するか

### Railwayの制約
- ❌ ブラウザドライバー（Playwright/Selenium）の実行が制限
- ❌ GUI環境の不在によりヘッドレスブラウザの制限
- ❌ システムレベルの操作が制限

### Renderの利点
- ✅ 完全なDocker環境でブラウザドライバーが利用可能
- ✅ Playwright/Seleniumの完全対応
- ✅ 無料プランで月750時間利用可能
- ✅ 自動デプロイとGitHub連携

## 移行手順

### 1. Renderアカウントの作成
1. [Render.com](https://render.com)にアクセス
2. GitHubアカウントでサインアップ
3. 無料プランを選択

### 2. 新しいリポジトリの作成
```bash
# 新しいリポジトリを作成
git remote add render https://github.com/your-username/jobcan-automation-render.git
git push render main
```

### 3. Renderでのデプロイ
1. Renderダッシュボードで「New Web Service」をクリック
2. GitHubリポジトリを選択
3. 以下の設定を行う：
   - **Name**: jobcan-automation
   - **Environment**: Docker
   - **Plan**: Free
   - **Branch**: main

### 4. 環境変数の設定
Renderダッシュボードで以下の環境変数を設定：
- `SECRET_KEY`: アプリケーションの秘密鍵
- `PORT`: 10000（自動設定）

## 完全な自動化の実現

### Render環境での動作確認
```python
# 実際のJobcan自動化が可能
from playwright.sync_api import sync_playwright

def test_automation():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # 実際のJobcan操作
        page.goto("https://id.jobcan.jp/users/sign_in")
        page.fill('#user_email', 'test@example.com')
        page.fill('#user_password', 'password')
        page.click('input[type="submit"]')
        
        print("✅ 自動化テスト成功")
        browser.close()
```

## 料金比較

| サービス | 無料プラン | ブラウザ自動化 | 制約 |
|---------|-----------|---------------|------|
| Railway | 月500時間 | ❌ 制限あり | ブラウザドライバー制限 |
| Render | 月750時間 | ✅ 完全対応 | 15分非アクティブでスリープ |
| Heroku | なし | ✅ 完全対応 | 有料のみ |
| Fly.io | 月250時間 | ✅ 完全対応 | クレジットカード必要 |

## 推奨事項

**Renderへの移行を強く推奨します**：

1. **完全な自動化**: Playwrightによる実際のJobcan操作が可能
2. **無料利用**: 月750時間の無料プラン
3. **簡単な移行**: Docker環境で既存コードがそのまま動作
4. **信頼性**: 安定したインフラストラクチャ

## 移行後の確認事項

1. ✅ テンプレートファイルダウンロード機能
2. ✅ 実際のJobcanログイン処理
3. ✅ 勤怠データの実際の入力処理
4. ✅ 詳細な進捗状況の表示
5. ✅ エラーハンドリングと診断機能 