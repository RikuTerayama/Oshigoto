# トピカリティ監査 Phase B 実装レポート（2026-02-10）

**ブランチ**: `seo/topicality-phase-b`  
**根拠**: `docs/seo/2026-02-10_topicality_audit.md` の P0・P1 指摘に基づく実装。コード改修のみ。外部調査（Search Console / GA）は未実施。

---

## 1. 何を直したか

| 項目 | 内容 |
|------|------|
| **P0-1** | 末尾スラッシュの正規化。**存在するルートのみ** 301 で `/path` へリダイレクト。末尾スラッシュを除いたパスが Flask の `url_map` で解決できない場合は何もしない（404 のまま）。`/path/`（存在しないURL）を `/path` に飛ばさない。ルート `/` と `/static/`・`/api/` は除外。GET/HEAD のみ対象。 |
| **P0-2** | 動的・一時的URLに `X-Robots-Tag: noindex, nofollow` を付与。対象は `/status/*`、`/api/*`、`/download-template`、`/download-previous-template`、`/sessions`、`/cleanup-sessions`。 |
| **P1-1** | `head_meta.html` の `description_meta` ブロックにデフォルトの `<meta name="description">` を追加。ブロック未定義ページで description が空になるのを防止。 |
| **P1-2** | ツール詳細ページからガイドへの導線を共通パーツ化し、アンカーを「〇〇の使い方ガイド」に変更。`product.guide_path` がある場合のみ表示。 |

---

## 2. 変更したファイル一覧

| ファイル | 変更内容 |
|----------|----------|
| `app.py` | `redirect` と `werkzeug.exceptions.NotFound, MethodNotAllowed` を import。`@app.before_request` で末尾スラッシュ時、`url_map.bind_to_environ` でルート存在確認し、存在する場合のみ 301。GET/HEAD のみ対象。`_NOINDEX_PATHS` と `@app.after_request` で X-Robots-Tag 付与。 |
| `templates/includes/head_meta.html` | `{% block description_meta %}` 内にデフォルトの meta description を記述。 |
| `templates/includes/tool_guide_link.html` | **新規**。`product` と `product.guide_path` があるときのみ「📚 {{ product.name }}の使い方ガイド」リンクを出力。 |
| `templates/tools/pdf.html` | ガイドリンクを `{% include 'includes/tool_guide_link.html' %}` に変更。 |
| `templates/tools/image-batch.html` | 同上。 |
| `templates/tools/image-cleanup.html` | 同上。 |
| `templates/tools/minutes.html` | 同上。 |
| `templates/tools/seo.html` | 同上。 |

---

## 2.1 Phase A 事実確認結果

- **実施メモ**: `docs/seo/2026-02-10_phaseA_fact_check.md` に URL ステータス確認表・ツールのガイドリンク有無・meta description の確認内容を記載。
- **本番・ローカル**: 上記ドキュメントの表の「本番 ステータス」「ローカル ステータス」は手動確認で記入する。
- **実装後の期待**:
  - 存在するページの末尾スラッシュ（例: `/tools/pdf/`）→ 301 で `/tools/pdf` へ。
  - 存在しない URL（例: `/path/`）→ **301 にしない。404 のまま。**

---

## 3. 手動テスト手順と確認内容

### P0-1 末尾スラッシュ（安全なリダイレクト）

- **GET /tools/pdf/** → 301、Location: `/tools/pdf`（クエリがあれば `?...` 付き）。ブラウザで /tools/pdf/ にアクセスし、アドレスバーが /tools/pdf になること。
- **GET /guide/pdf/** → 301、Location: `/guide/pdf`。
- **GET /blog/** → 301、Location: `/blog`（ルートが存在する場合）。
- **GET /path/** → **404 のまま。301 で /path にリダイレクトされないこと**（存在しない URL はリダイレクトしない）。
- **GET /** → 200 のまま。リダイレクトされないこと。
- **POST /tools/pdf/** → リダイレクト対象外（GET/HEAD のみ）。ルートが POST を許可していなければ 404 等のまま。
- **静的・API**: `/static/`・`/api/` は除外対象。通常の静的・API アクセスに影響しないこと。
- **canonical**: 主要ページ（例: /tools/pdf）の HTML で `<link rel="canonical" href=".../tools/pdf">` となり、末尾にスラッシュが付いていないこと。

### P0-2 X-Robots-Tag

- **curl -I http://localhost:5000/status/dummy** → レスポンスに `X-Robots-Tag: noindex, nofollow` が含まれること（ルートが存在する場合。404 でもヘッダーは付与される）。
- **curl -I -X POST http://localhost:5000/api/seo/crawl-urls** など、対象 API のレスポンスに `X-Robots-Tag` が付くこと（対象に含めた場合）。
- **GET /tools/pdf** → 通常ページのレスポンスに `X-Robots-Tag` が**含まれない**こと。

### P1-1 デフォルト description

- `description_meta` を定義していないテンプレート（存在する場合）で、レンダリングされた HTML に `<meta name="description" content="...">` が 1 つ以上あること。
- もともと `description_meta` を定義しているページ（例: /tools/pdf）では、従来どおりその content が表示されること。

### P1-2 ツール→ガイド導線

- **/tools/pdf** を開き、「📚 PDFユーティリティの使い方ガイド」のようなリンクが表示され、クリックで /guide/pdf に遷移すること。
- **/tools/image-batch**、**/tools/image-cleanup**、**/tools/minutes**、**/tools/seo** も同様に、ツール名入りのガイドリンクが表示され、正しいガイドページへ遷移すること。
- `product` や `guide_path` が無い場合（想定外の遷移）でも、リンクが表示されずエラーにならないこと。

---

## 4. X-Robots-Tag noindex を付与した対象一覧

- **パスプレフィックス**
  - `/status/` で始まるパス（例: `/status/abc123`）
  - `/api/` で始まるパス（例: `/api/pdf/unlock`、`/api/seo/crawl-urls`）
- **固定パス**
  - `/download-template`
  - `/download-previous-template`
  - `/sessions`
  - `/cleanup-sessions`

※ `/upload` は POST 専用のため、レスポンスを返す同一 URL の GET が無ければ一覧には含めていない。必要に応じて追加可能。

---

## 5. 差分の要点と次の P2 メモ

### 差分の要点

- **app.py**: before_request で末尾スラッシュ時のみ 301、after_request で上記パスに X-Robots-Tag を付与。既存ルートの挙動は変えず、ミドルウェアで付加。
- **head_meta.html**: description_meta ブロックにデフォルト 1 文を記述。既存ページでブロックを上書きしている場合はそのまま優先。
- **ツールページ**: ガイドリンクを共通 include にし、アンカーを「〇〇の使い方ガイド」に統一。product は既存の `get_product_by_path` から渡されているため追加の view 変更なし。

### 次にやると良い P2（短いメモ）

- **トップのテーマ別まとめ**: landing で製品を「勤怠」「ファイル変換」等のテーマでグループ化して表示し、ハブ性を強化。
- **ブログからツール・ガイドへの関連リンク**: ブログ記事の本文またはサイドに「関連ツール」「関連ガイド」を出し、トピックの一貫性を高める。

---

以上。
