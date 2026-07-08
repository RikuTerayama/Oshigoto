# 議事録整形（minutes）機能 削除 実装レポート

**日付**: 2026-02-10  
**ブランチ**: `cleanup/remove-minutes`  
**前提**: docs/ 配下の過去資料は削除していない（履歴として残す）。

---

## 1. 実施コミット一覧

| # | コミット | 内容 |
|---|----------|------|
| 1 | chore(minutes): route old URLs to 301/410, remove minutes from PRODUCTS and nav | app.py: /tools/minutes → 301 /tools、/guide/minutes → 301 /guide、/api/minutes/format → 410。products_catalog から minutes エントリ削除。nav フォールバックから議事録整形を削除。 |
| 2 | chore(minutes): remove minutes templates and JS; add export-utils.js for SEO tool | templates/tools/minutes.html・guide/minutes.html 削除。static/js/minutes-*.js 全8本削除。export-utils.js 新規作成（ExportUtils.copyToClipboard, showToast, downloadMarkdown）。seo.html を minutes-export.js から export-utils.js に切り替え。 |
| 3 | chore(minutes): remove minutes links and copy from all templates | head_meta, tools/index, landing, sitemap, privacy, guide/index, guide/image-cleanup, guide/autofill, faq から議事録・minutes のリンクと文言を削除。 |
| 4 | docs(minutes): add remove-minutes implementation report | 本ドキュメントを追加。 |

---

## 2. 旧URLの挙動

| URL | メソッド | 挙動 |
|-----|----------|------|
| /tools/minutes | GET | **301** → Location: `/tools` |
| /guide/minutes | GET | **301** → Location: `/guide` |
| /api/minutes/format | POST | **410 Gone**。JSON: `{"error_code":"gone"}` |

---

## 3. 検証手順

### 3.1 旧URL（curl）

```bash
# 301 確認
curl -sI -o /dev/null -w "%{http_code} %{redirect_url}\n" http://localhost:5000/tools/minutes
# 期待: 301 かつ Location: /tools（または絶対URLで /tools）

curl -sI -o /dev/null -w "%{http_code} %{redirect_url}\n" http://localhost:5000/guide/minutes
# 期待: 301 かつ Location: /guide

# 410 確認
curl -s -X POST http://localhost:5000/api/minutes/format -H "Content-Type: application/json" -d "{}" -w "\n%{http_code}\n"
# 期待: {"error_code":"gone"} と 410
```

### 3.2 sitemap

```bash
curl -s http://localhost:5000/sitemap.xml | grep -E "tools/minutes|guide/minutes"
# 期待: 何も出力されない（0件）
```

### 3.3 コード・テンプレートに意図しない参照が残っていないこと

```bash
grep -R "tools/minutes|guide/minutes|api/minutes|議事録整形|minutes-export" templates static/js app.py lib -n
```

- **期待**: app.py のルート定義（`@app.route('/guide/minutes')` 等）と docstring のみ。templates / static/js / lib からは該当なし。  
- 注: ルートパスと「旧議事録」の docstring は意図的な残存。

### 3.4 ブラウザでの確認

- GET `/tools/minutes` → アドレスバーが `/tools` に変わり、ツール一覧が表示されること。
- GET `/guide/minutes` → アドレスバーが `/guide` に変わり、ガイド一覧が表示されること。
- ヘッダー・フッター・ツール一覧・ガイド一覧に「議事録整形」または `/guide/minutes` / `/tools/minutes` のリンクが表示されないこと。

---

## 4. SEOツールの手動確認項目

- [ ] **画面が開く**: `/tools/seo` を開いてもエラーにならず、OGP・チェックリスト・メタタグ・sitemap/robots 等のUIが表示される。
- [ ] **結果をダウンロードできる**: 「Markdownをダウンロード」「画像をダウンロード」「sitemap.xmlをダウンロード」「robots.txtをダウンロード」等が動作し、ファイルが取得できる。
- [ ] **コピー・トースト**: メタタグ例のコピー、チェックリストのコピー、結果のコピーでクリップボードにコピーされ、トーストが表示される（ExportUtils.copyToClipboard / showToast の動作確認）。

以上。
