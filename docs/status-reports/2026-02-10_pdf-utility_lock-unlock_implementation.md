# PDFユーティリティ「保護付与」「保護解除」実装 — 変更一覧・テスト手順

## 設計判断（案B 採用）

- **採用**: 案B（サーバ併用）
- **理由**: 保護付与は pdf-lib ではクライアント実装が困難なため、サーバで pypdf により確実に実装する。保護解除も同一方針で、パスワードをログ・永続化に出さず一時メモリのみで処理する。
- **詳細**: `lib/pdf_lock_unlock.py` 冒頭コメントおよび `app.py` の `/api/pdf/unlock`, `/api/pdf/lock` 付近に記載。

---

## 変更ファイル一覧

| ファイル | 変更内容 |
|----------|----------|
| `requirements.txt` | `pypdf>=4.0.0` 追加 |
| `lib/pdf_lock_unlock.py` | 新規。`decrypt_pdf`, `encrypt_pdf`（pypdf 使用）。パスワードはログに出さない。 |
| `app.py` | `POST /api/pdf/unlock`, `POST /api/pdf/lock` 追加。50MB 上限。form で file + password 受付。パスワードはログに出さない。 |
| `templates/tools/pdf.html` | mode に unlock-pdf / lock-pdf 追加。入力・出力パスワード欄・同意チェック追加。`updateModeOptions` で表示切替。`updateRunButton` で unlock/lock の実行条件。`runOperation` で to-images/compress/extract-images に password 渡し、unlock-pdf/lock-pdf で API 呼び出しとダウンロード表示。キャンセル用 AbortController。handleError でパスワードエラー時に入力欄フォーカス。 |
| `static/js/pdf-render.js` | `getDocument` に `password: options.password` 渡し。暗号化エラー時はメッセージのみ throw（パスワードは console に出さない）。 |
| `static/js/pdf-compress.js` | 同上。 |
| `static/js/pdf-extract-images.js` | 同上。 |

※ 既存モード（merge / extract / split / to-images / compress / images-to-pdf / extract-images）は、options に `password` を追加しただけであり、既存挙動は維持。

---

## 手動テスト手順

### 前提

- 暗号化PDFを1つ用意（パスワードを把握しているもの）
- 非暗号化PDFを1つ以上用意
- Flask サーバ起動済み（`python app.py` 等）、`/tools/pdf` を開いていること

### 1. 既存モードが壊れていないか

- **merge**: 非暗号化PDFを2つ以上選択 → 結合できること。
- **extract**: 非暗号化PDF1つ＋ページ範囲 → 抽出できること。
- **split**: 非暗号化PDF1つ＋ページ範囲 → 分割できること。
- **to-images**: 非暗号化PDF1つ → 画像が出力されること。
- **compress**: 非暗号化PDF1つ → 圧縮PDFが出力されること。
- **images-to-pdf**: 画像ファイルを選択 → PDFが出力されること。
- **extract-images**: 非暗号化PDF1つ → 埋め込み画像が抽出されること。

### 2. 暗号化PDFで to-images / compress / extract-images（正しいパスワード）

- モードを **to-images** にし、暗号化PDFを1つ選択。
- 「入力PDF用パスワード」に正しいパスワードを入力 → 実行。
- 画像が出力されること。
- 同様に **compress**、**extract-images** で正しいパスワードを入力 → それぞれ成功すること。

### 3. 暗号化PDFでパスワード未入力・誤り

- モードを **to-images** にし、暗号化PDFを1つ選択。パスワード欄は空のまま実行。
- 「このPDFはパスワード保護されています。正しいパスワードを入力してください。」等のメッセージが出ること。入力パスワード欄にフォーカスが当たること。
- 誤ったパスワードを入力して実行 → 同様にエラーになること。
- パスワードがコンソールログ・ネットワークログのURL/クエリに出ていないことを確認（DevTools で確認）。

### 4. ロック解除（unlock-pdf）

- モードを **「ロック解除（パスワード必須）」** に切り替え。
- 入力PDF用パスワード欄と同意チェックが表示されること。
- 同意にチェックせず実行ボタンが押せないこと（無効のまま）。
- 同意にチェックし、暗号化PDFを1つ選択。正しいパスワードを入力 → 実行。
- 保護なしのPDFがダウンロードできること。
- パスワードを空で実行 → サーバから「パスワードを入力してください。」等のエラーになること。
- 誤ったパスワードで実行 → 「パスワードが違います。」等のメッセージになること。

### 5. ロック付与（lock-pdf）

- モードを **「ロック付与（暗号化して出力）」** に切り替え。
- 出力PDF用パスワード欄が表示されること。パスワード未入力では実行ボタンが無効であること。
- 非暗号化PDFを1つ選択し、出力用パスワードを入力 → 実行。
- 暗号化されたPDFがダウンロードできること。別ツールまたは同じツールの「ロック解除」で、そのパスワードを入力すると開けること。

### 6. パスワードが永続化・露出していないこと

- 入力・出力パスワード欄に入力した値が、LocalStorage / Cookie / URL / クエリ文字列 / HTML に含まれていないことを DevTools で確認。
- サーバログにパスワードやPDFの中身が出力されていないことを確認（ログレベルに注意）。

### 7. キャンセル

- ロック解除またはロック付与実行中に「キャンセル」を押すと、処理が止まり「キャンセルされました」と表示されること。

---

以上で、既存モードの維持・暗号化PDFのパスワード対応・unlock-pdf / lock-pdf の動作・倫理配慮（同意チェック・メッセージ）・パスワードの非露出を確認できる。
