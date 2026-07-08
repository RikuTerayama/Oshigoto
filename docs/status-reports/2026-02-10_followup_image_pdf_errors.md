# フォローアップ: 画像・PDF 3エラー解消 — 原因断定・修正・検証

前回修正後も以下が再現したため、原因を証拠付きで断定し最小修正を行った。

- **PDF ロック付与**: エラー: ロック付与に失敗しました。PDFの形式やサイズを確認してください。
- **PDF ロック解除**: エラー: ロック解除に失敗しました。
- **画像ユーティリティ**: xxx.png: 画像クリーンアップ機能の読み込みに失敗しました。ページを再読み込みしてください。

---

## フェーズA: 事実確認（原因の断定）

### A-1 画像ユーティリティ

| 確認項目 | 結果（ファイル:行） |
|----------|----------------------|
| **type="module" の有無** | `templates/tools/image-cleanup.html` の script タグに **type="module" は付与されていない**（529行は通常の `<script src="...">`）。インライン script（533行〜）も module ではない。 |
| **bare identifier の参照箇所** | 同ファイル **757行** `typeof ImageCleanup`、**763行** `ImageCleanup.generateFilename`、**766行** `ImageCleanup.runCleanupPipeline` で **bare の `ImageCleanup`** を参照。 |
| **script の読み込み** | **529行**で `url_for('static', filename='js/image-cleanup.js')` を指定。defer/async なし・同期読み込み。 |
| **断定** | **参照スコープの問題**。インライン script が何らかの理由で bare の `ImageCleanup` を解決できないスコープで評価されている場合、`window.ImageCleanup` に代入していても **bare identifier は見えない**。そのため `globalThis.ImageCleanup` を明示的に参照する必要がある。加えて、**JS が 404 等で読み込まれていない**可能性の切り分けのため、DOMContentLoaded 時に `globalThis.ImageCleanup` の有無を console に出す。 |

### A-2 PDF lock / unlock

| 確認項目 | 結果（ファイル:行） |
|----------|----------------------|
| **エンドポイント** | `app.py` **994行** `POST /api/pdf/unlock`、**1030行** `POST /api/pdf/lock`。 |
| **FormData の field 名** | `templates/tools/pdf.html` **933–934行**（unlock）、**965–966行**（lock）で `form.append('file', file)` と `form.append('password', password)`。 |
| **サーバ側の受け取り** | `app.py` で `request.files.get('file')` と `request.form.get('password')`。**field 名は一致**。 |
| **pypdf** | `requirements.txt` に `pypdf>=4.0.0` あり。`lib/pdf_lock_unlock.py` で import。 |
| **エラー時のAPIレスポンス** | 修正前は `jsonify(success=False, error='...')` のみで、**error_code も request_id もなかった**。また 500 時は HTML が返り得るため、フロントで `res.json()` が失敗し `data` が `{}` になり、**常に「ロック解除に失敗しました」「ロック付与に失敗しました」の固定文言**になっていた。 |
| **非暗号化PDFの unlock** | `lib/pdf_lock_unlock.py` **23–25行**で `reader.is_encrypted` が False なら `return pdf_bytes` としており、**非暗号化ならそのまま返す**実装になっている。それでも「ロック解除に失敗しました」が出る場合は、**サーバが 500 を返している**（例外で traceback 等）か、**レスポンスが JSON でない**ことが原因。 |

**断定**: エラー判別のために **error_code と request_id を必ず返す**ようにし、500 時も JSON で返す。サーバログには request_id と例外型・スタックを出す（パスワードは出さない）。

---

## error_code と状況の対応

### unlock（ロック解除）

| error_code | 状況 |
|------------|------|
| need_password | 暗号化PDFでパスワード未入力 |
| incorrect_password | 暗号化PDFでパスワード誤り |
| file_required | ファイル未選択 |
| file_too_large | 50MB超過 |
| read_failed | ファイル読み込み例外 |
| decrypt_failed | 復号処理の例外（not_encrypted_but_failed 以外） |
| not_encrypted_but_failed | 非暗号化だが何らかで失敗した場合（将来用） |
| unsupported | サーバ側の予期しない例外（500） |

### lock（ロック付与）

| error_code | 状況 |
|------------|------|
| missing_password | 出力用パスワード未入力 |
| file_required | ファイル未選択 |
| file_too_large | 50MB超過 |
| read_failed | ファイル読み込み例外 |
| encrypt_failed | pypdf の encrypt/write 等で例外（**このときだけ「形式やサイズを確認」の文言を表示**） |
| unsupported | サーバ側の予期しない例外（500） |

---

## フェーズB: 修正内容（差分の要点）

### 変更ファイル一覧

| ファイル | 変更内容 |
|----------|----------|
| `templates/tools/image-cleanup.html` | (1) **globalThis 参照に統一**: processor 内で `const Cleanup = globalThis.ImageCleanup` とし、以降は `Cleanup` のみ使用（759・762行付近の bare `ImageCleanup` を廃止）。(2) **読み込み状態の確認**: DOMContentLoaded で `console.log('[image-cleanup] load check: globalThis.ImageCleanup', typeof globalThis.ImageCleanup)` を追加（パスワードは出さない）。未定義時の console.error で「Network で /static/js/image-cleanup.js が 200 か確認」と案内。 |
| `static/js/image-cleanup.js` | **globalThis への代入を追加**: 既存の `window.ImageCleanup = ImageCleanup` に加え、`globalThis.ImageCleanup = ImageCleanup` を設定。 |
| `app.py` | (1) **_pdf_api_error(error_code, status)**: `request_id`（uuid の先頭12文字）を付与し、`jsonify(success=False, error_code=..., request_id=...)` を返す。message は返さない。(2) **unlock**: 全 400 で `_pdf_api_error` を使用。`invalid_password` → **incorrect_password** で返却。最外層で try/except し、例外時は 500 で `error_code='unsupported'` と request_id を返し、**ログに request_id と例外型・スタック**を出力（パスワードは出さない）。(3) **lock**: 同様に全 400 で `_pdf_api_error`。`password_required` → **missing_password**。encrypt 失敗時は request_id を付与し、ログに request_id・例外型・exc_info を出力。最外層で 500 時は unsupported + request_id。 |
| `templates/tools/pdf.html` | (1) **unlock**: `!res.ok` 時に `data.error_code || data.error` で code を取得し、code に応じたメッセージを表示。`data.request_id` があれば「 (request_id: xxx)」を付与。(2) **lock**: 同様に error_code と request_id を参照。「形式やサイズを確認」は **encrypt_failed のときのみ**表示。 |

### 要点

- パスワードはログ・永続化・URL・HTML・LocalStorage・Cookie・API の message に一切出さない。
- 例外の生文字列は API の message として返さない。error_code と request_id のみ返す。
- 既存の merge / extract / split / to-images / compress / extract-images は変更していない。

---

## フェーズC: 手動テスト手順

### 画像ユーティリティ

1. 問題の PNG で再実行し、**「画像クリーンアップ機能の読み込みに失敗しました」が出ずに処理が完了すること**。
2. ブラウザ Console で、**DOMContentLoaded 後に `[image-cleanup] load check: globalThis.ImageCleanup function` と出ること**（未定義なら `undefined`。その場合は Network で `/static/js/image-cleanup.js` が 200 か確認）。
3. 正常系の別画像でも従来どおり動作すること。

### PDF ロック付与（lock）

1. **小さいPDF + パスワード入力** → 成功し、暗号化された PDF がダウンロードされること。
2. **パスワード空** → `missing_password` 相当のメッセージで止まり、レスポンスに `error_code: "missing_password"` と `request_id` が含まれること。
3. 失敗時に「形式やサイズを確認」が表示されるのは **encrypt_failed のときだけ**であること。

### PDF ロック解除（unlock）

1. **非暗号化PDF** → パスワード欄は空のまま実行し、**パスワード要求が出ずに成功**（同一 PDF 返却でよい）。
2. **暗号化PDFでパスワード空** → `need_password` 相当のメッセージ。
3. **暗号化PDFでパスワード誤り** → `incorrect_password` 相当（「パスワードが違います」）。
4. **暗号化PDFで正しいパスワード** → 成功し、保護なしの PDF がダウンロードされること。

### 共通

- Network とサーバログに **パスワードが一切出ていないこと**。
- エラー時にレスポンス JSON に **error_code と request_id** が含まれ、フロントに request_id が表示されること（原因調査用）。

---

以上。
