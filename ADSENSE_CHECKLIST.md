# 📋 Google AdSense 申請前チェックリスト

このチェックリストを印刷して、1つずつ確認してください。

## ✅ 必須確認事項

### 1. スリープ問題の確認（最重要）

- [ ] 20分間サイトに一切アクセスせずに放置
- [ ] シークレットモードで再アクセス
- [ ] 起動時間を測定：**5秒以内** = 合格
- [ ] 起動時間が15秒以上の場合、UptimeRobot設定を再確認

**測定コマンド（PowerShell）:**
```powershell
Measure-Command { Invoke-WebRequest -Uri "https://<your-domain>/" }
```

---

### 2. 環境変数の確認

- [ ] Render環境変数に `ADSENSE_ENABLED=true` が設定されている
- [ ] Renderダッシュボードで確認済み
- [ ] 値が小文字の `true` になっている（`True` や `TRUE` ではない）

---

### 3. AdSenseスクリプトの確認

- [ ] トップページで `Ctrl+U` を押してソースを表示
- [ ] `<head>` 内に以下のスクリプトが **1回のみ** 存在する:
  ```html
  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-4232725615106709" crossorigin="anonymous"></script>
  ```
- [ ] スクリプトが重複していない（複数回挿入されていない）

---

### 4. 全ページの動作確認

各ページにアクセスして、正常に表示されることを確認：

- [ ] `https://<your-domain>/` - トップページ
- [ ] `https://<your-domain>/guide/getting-started` - はじめての使い方
- [ ] `https://<your-domain>/guide/excel-format` - Excelファイルの作成方法
- [ ] `https://<your-domain>/guide/troubleshooting` - トラブルシューティング
- [ ] `https://<your-domain>/faq` - よくある質問
- [ ] `https://<your-domain>/glossary` - 用語集
- [ ] `https://<your-domain>/about` - サイトについて
- [ ] `https://<your-domain>/privacy` - プライバシーポリシー
- [ ] `https://<your-domain>/terms` - 利用規約
- [ ] `https://<your-domain>/contact` - お問い合わせ

---

### 5. 特殊ファイルの確認

- [ ] `https://<your-domain>/ads.txt` が以下の内容を返す:
  ```
  google.com, pub-4232725615106709, DIRECT, f08c47fec0942fa0
  ```
- [ ] `https://<your-domain>/robots.txt` が正しい内容を返す
- [ ] `https://<your-domain>/sitemap.xml` が正しく表示される

---

### 6. HTTPS/SSL の確認

- [ ] ブラウザのアドレスバーに 🔒 マークが表示される
- [ ] 「この接続は保護されています」と表示される
- [ ] 証明書エラーがない
- [ ] 混在コンテンツ警告がない

---

### 7. モバイル対応の確認

ブラウザの開発者ツール（F12 → デバイスツールバー）で確認:

- [ ] iPhone SE (375x667) で正常に表示される
- [ ] iPhone 14 Pro (393x852) で正常に表示される
- [ ] iPad (768x1024) で正常に表示される
- [ ] 横スクロールが発生していない
- [ ] テキストが読みやすい
- [ ] ボタンがタップしやすい

---

### 8. ブラウザ互換性の確認

以下のブラウザで動作確認:

- [ ] Google Chrome（最新版）
- [ ] Microsoft Edge（最新版）
- [ ] Firefox（最新版）
- [ ] Safari（可能であれば）

---

### 9. UptimeRobot の設定確認

- [ ] UptimeRobot にログイン
- [ ] Monitor が作成されている
- [ ] Monitor URL: `https://<your-domain>/healthz`（推奨）または `/ping`
- [ ] Monitoring Interval: `5 minutes`
- [ ] Monitor Status が **Up** になっている
- [ ] 過去1時間のアップタイム: 100%
- [ ] Response Time: 平均 < 500ms

**SRE推奨:**
- メインモニター: `/healthz`（超軽量、<10ms）
- サブモニター: `/ping`（バックアップ）

---

### 10. 内部リンクの確認

フッターの全リンクをクリックして動作確認:

**ガイドセクション:**
- [ ] はじめての使い方 → `/guide/getting-started`
- [ ] Excelファイルの作成方法 → `/guide/excel-format`
- [ ] トラブルシューティング → `/guide/troubleshooting`

**リソースセクション:**
- [ ] よくある質問（FAQ） → `/faq`
- [ ] 用語集 → `/glossary`
- [ ] サイトについて → `/about`

**法的情報セクション:**
- [ ] プライバシーポリシー → `/privacy`
- [ ] 利用規約 → `/terms`
- [ ] お問い合わせ → `/contact`

---

### 11. コンテンツの質の確認

- [ ] 各ページに500文字以上のオリジナルコンテンツがある
- [ ] スペルミスや文法エラーがない
- [ ] 画像や図形が正しく表示される
- [ ] レイアウトが崩れていない

---

### 12. Googleボットのシミュレーション

コマンドプロンプトで以下を実行:

```bash
curl -A "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)" https://<your-domain>/
```

- [ ] HTTPステータスコード `200 OK` が返される
- [ ] HTMLコンテンツが正常に表示される
- [ ] エラーメッセージがない

---

## 🎯 推奨確認事項（オプション）

### 13. Google Search Console への登録

- [ ] Google Search Console にアクセス
- [ ] プロパティを追加（URLプレフィックス）
- [ ] 所有権を確認
- [ ] サイトマップを送信: `https://<your-domain>/sitemap.xml`

---

### 14. ページ読み込み速度の確認

Google PageSpeed Insights で確認:
- URL: https://pagespeed.web.dev/
- [ ] モバイルスコア: **50以上**
- [ ] デスクトップスコア: **70以上**

---

### 15. 最終動作テスト

実際のユースケースをシミュレーション:

- [ ] テンプレートファイルをダウンロード
- [ ] ファイルが正常にダウンロードされる
- [ ] ファイルを開いて確認
- [ ] （オプション）ダミーデータで自動入力をテスト

---

## ✅ 申請前の最終確認

すべてのチェックボックスにチェックが入ったら:

- [ ] 24時間以上サイトが安定稼働している
- [ ] UptimeRobotのアップタイムが98%以上
- [ ] すべてのページが5秒以内に表示される
- [ ] モバイルでも正常に表示される
- [ ] AdSenseスクリプトが正しく配置されている

### **SRE追加確認（503防止）**

- [ ] Renderログに `Worker timeout` や `Killed` がない（過去24時間）
- [ ] メモリ使用率が85%以下（Render Dashboard → Metrics）
- [ ] `/healthz` が100回連続で200 OKを返す
- [ ] CPU使用率が70%以下
- [ ] バックグラウンドジョブが正常完了している（ログ確認）

**連続ヘルスチェック（推奨）:**
```bash
# 100回連続テスト
for i in {1..100}; do
  curl -f https://<your-domain>/healthz || echo "FAIL at $i"
done
# 期待: すべて成功、FAILなし
```

**レスポンスタイム確認:**
```bash
# 10回測定して平均を確認
for i in {1..10}; do
  curl -o /dev/null -s -w "%{time_total}s\n" https://<your-domain>/healthz
done
# 期待: すべて 0.1秒以下
```

---

## 🚀 申請手順

すべての確認が完了したら:

1. Google AdSense管理画面にログイン
2. 「サイト」→「サイトを追加」
3. サイトURL を入力: `https://<your-domain>/`
4. 「審査を申請」をクリック
5. 結果を待つ（通常2～3日）

---

## 📝 メモ欄

問題が見つかった場合、ここにメモ:

```
問題点:


対処方法:


再確認日時:

```

---

**作成日:** 2025/10/10  
**バージョン:** 1.0  
**最終更新:** デプロイ直前に再確認すること

