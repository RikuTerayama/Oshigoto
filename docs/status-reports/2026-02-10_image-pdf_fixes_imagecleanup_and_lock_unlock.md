# 画像ユーティリティ・PDFユーティリティ不具合修正 — 原因断定・修正内容・テスト手順

## フェーズA: 事実確認（原因の断定）

### A-1 画像ユーティリティ「ImageCleanup is not defined」

| 項目 | 根拠（ファイル:行） |
|------|----------------------|
| **定義** | `static/js/image-cleanup.js` の **6行目**で `class ImageCleanup {` として定義。export なし・古典 script。 |
| **参照** | `templates/tools/image-cleanup.html` の **759行**（`ImageCleanup.generateFilename`）と **762行**（`ImageCleanup.runCleanupPipeline`）。 |
| **読み込み** | 同テンプレート **529行**で `<script src="{{ url_for('static', filename='js/image-cleanup.js') }}">` により読み込み。type="module" なし。 |
| **一次原因の断定** | コード上は「定義・参照・読み込み順」は一致している。**スコープ不整合**（古典 script 実行後もグローバルにクラスが露出していないケース）または **ロード失敗**（404/ネットワーク/キャッシュ）で `ImageCleanup` が未定義になる。 |
| **修正方針** | (1) `image-cleanup.js` 末尾で `window.ImageCleanup = ImageCleanup` を明示代入し、グローバル露出を保証。(2) 参照前に `typeof ImageCleanup === 'undefined'` をガードし、未定義時はユーザー向けメッセージ＋開発者向け console.error（パスワードは出さない）で終了。 |

### A-2 PDFユーティリティ（lock / unlock）

| 項目 | 根拠（ファイル:行） |
|------|----------------------|
| **unlock で「パスワードを入力してください」が非暗号化でも出る原因** | `app.py` の **1001–1002行**（修正前）で `if not password.strip(): return jsonify(..., error='password_required'), 400` としており、**常にパスワード必須**にしていた。非暗号化PDFでも空パスワードで 400 が返り、フロントが「パスワードを入力してください」と表示していた。 |
| **仕様** | 非暗号化PDFの unlock は **password 不要で、入力PDFをそのまま 200 で返す**。暗号化PDFで password 無しのときのみ `need_password` で 400。 |
| **lock「ロック付与に失敗しました」** | サーバが `except Exception: return jsonify(..., error='encrypt_failed'), 400` のみで、**例外内容を握りつぶしていた**。pypdf 4 では `encrypt()` の第一引数が `user_password` であるため、`writer.encrypt(password)` を `writer.encrypt(user_password=password)` に明示。加えてサーバで `encrypt_failed` 時に例外種別をログに出すようにし、開発者が原因追跡できるようにした。 |

---

## フェーズB/C: 修正内容（変更ファイル一覧と要点）

### 変更ファイル一覧

| ファイル | 変更内容 |
|----------|----------|
| `static/js/image-cleanup.js` | 末尾に `window.ImageCleanup = ImageCleanup` を追加（グローバル露出）。 |
| `templates/tools/image-cleanup.html` | processor 先頭で `typeof ImageCleanup === 'undefined'` をガード。未定義時は「画像クリーンアップ機能の読み込みに失敗しました。ページを再読み込みしてください。」を throw し、console.error で script 読み込み状態を出力（パスワードは含めない）。 |
| `lib/pdf_lock_unlock.py` | **decrypt_pdf**: 非暗号化はそのまま返す。暗号化かつパスワード未入力で `ValueError('need_password')`。**encrypt_pdf**: `writer.encrypt(password)` → `writer.encrypt(user_password=password)` に変更。 |
| `app.py` | **unlock**: パスワード空でも 400 にしない。`decrypt_pdf` の `need_password` / `invalid_password` を 400 で返却。**lock**: `encrypt_failed` 時に例外種別をログに記録（パスワードは出さない）。 |
| `templates/tools/pdf.html` | unlock の 400 時メッセージに `need_password` を追加（「このPDFはパスワード保護されています。パスワードを入力してください。」）。lock の 400 時に `file_too_large` / `read_failed` / `encrypt_failed` を出し分け。 |

### 要点

- **パスワード**: ログ・永続化・URL・HTML に一切出さない。例外オブジェクトにも含めない。
- **既存機能**: merge / extract / split / to-images / compress / images-to-pdf / extract-images は変更していない。
- **lock の encrypt 失敗**: サーバで `logging.warning('pdf lock encrypt_failed: %s', type(e).__name__)` のみ。レスポンス body にパスワードや生の例外メッセージは含めない。

---

## フェーズD: 手動テスト手順

### 画像ユーティリティ

1. **問題の PNG で再実行**  
   該当 PNG をドロップし「処理開始」。**「ImageCleanup is not defined」が出ずに処理が完了すること。**

2. **正常系**  
   別の画像（例: 通常の JPG/PNG）でクリーンアップを実行し、従来どおり結果が得られること。

3. **読み込み失敗時**  
   （任意）`image-cleanup.js` を 404 にするなどして未読み込みにし、処理開始で「画像クリーンアップ機能の読み込みに失敗しました。ページを再読み込みしてください。」と表示され、console に読み込み状態のログが出ること。

### PDFユーティリティ

1. **非暗号化PDFで unlock**  
   保護なしの PDF を1つ選択し、**パスワード欄は空のまま**「ロック解除」を実行。同意にチェック。**パスワード要求が出ず、入力PDFと同等の PDF がダウンロードされること。**

2. **暗号化PDFで unlock**  
   - パスワード無しで実行 → 「このPDFはパスワード保護されています。パスワードを入力してください。」（または need_password 相当の表示）。  
   - 誤ったパスワード → 「パスワードが違います。」  
   - 正しいパスワード → 保護なしの PDF がダウンロードされること。

3. **lock**  
   - 出力用パスワード未入力で実行 → 「出力用パスワードを入力してください。」で止まること。  
   - パスワードを入力して実行 → 暗号化された PDF がダウンロードされ、そのパスワードで開けること。

4. **既存モード**  
   merge / extract / split / to-images / compress / images-to-pdf / extract-images をそれぞれ実行し、従来どおり動作すること。

5. **パスワードの非露出**  
   DevTools の Console / Network / サーバログに、パスワード文字列が出力されていないことを確認すること。

---

以上。
