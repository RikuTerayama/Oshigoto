# フォローアップ2: PDF lock/unlock 全PDF対応・compress「PdfCompress is not defined」解消

## 発生していた症状

1. **PDF unlock が失敗**: ロック解除に失敗しました。 (request_id: 6a4b61c191d6)
2. **PDF lock が失敗**（別のPDFでは成功）: ロック付与に失敗しました。PDFの形式やサイズを確認してください。 (request_id: c7288867fdde)
3. **PDF 圧縮が動かない**: PdfCompress is not defined

---

## フェーズA: 事実確認

### A-1 PdfCompress is not defined の原因断定

| 確認項目 | 結果（ファイル:行） |
|----------|----------------------|
| **script の読み込み** | `templates/tools/pdf.html` **535行**で `<script src="{{ url_for('static', filename='js/pdf-compress.js') }}">`。defer/async なし・キャッシュバスターなし。順序は pdf-render.js の次・pdf-images-to-pdf.js の前。 |
| **定義と露出** | `static/js/pdf-compress.js` **15行**で `class PdfCompress {` として定義。**ファイル末尾に globalThis.PdfCompress / window.PdfCompress への代入が無い**。 |
| **参照箇所** | 同テンプレート **885行**で **bare の `PdfCompress.compressPdfByRasterize`** を参照。 |
| **断定** | **ロードはされているがグローバル露出が無い**（または bare 識別子がスコープで解決されない）可能性が高い。ImageCleanup と同様、古典 script でクラスは定義されるが、インライン script から bare の `PdfCompress` が参照できない環境がある。**解消**: pdf-compress.js 末尾で `globalThis.PdfCompress = PdfCompress` を設定し、pdf.html の compress 分岐では `const PC = globalThis.PdfCompress` を使い、未定義時はユーザー向けメッセージ＋console.error で案内。 |

### A-2 lock/unlock が特定PDFで落ちる原因（request_id から想定）

| request_id | モード | 想定原因（サーバログで例外型・スタックを確認すること） |
|------------|--------|--------------------------------------------------------|
| 6a4b61c191d6 | unlock | **decrypt_failed** として 400 が返っている場合、pypdf の `reader.pages` または `writer.write(out)` で例外（構造が非標準・破損・互換性）の可能性。パスワード型以外の暗号は **unsupported_encryption** としたい。 |
| c7288867fdde | lock | **encrypt_failed** として 400 が返っている場合、(1) **既に暗号化されているPDF** を lock しようとしている（already_encrypted）、(2) pypdf の `writer.add_page` / `writer.encrypt` / `writer.write` で例外（互換性・構造問題）の可能性。 |

**現状の error_code の返り方**: unlock は need_password, incorrect_password, decrypt_failed, file_required, read_failed, file_too_large, unsupported(500)。lock は missing_password, file_required, read_failed, file_too_large, encrypt_failed, unsupported(500)。

**どの段階で落ちているか**（ログで確認）:
- 受信ファイルがPDFとして読めない → PdfReader 構築時例外 → **corrupt_pdf**
- 読めるが writer 書き出しで落ちる → **decrypt_failed** / **encrypt_failed**（より細かく **unsupported_pdf** / **corrupt_pdf** を返すよう改善）
- 既に暗号化されているPDFを lock → **already_encrypted** を返す（事前チェックで回避）
- 暗号方式が証明書型など非対応 → **unsupported_encryption**（pypdf で判別できる範囲で返す）

---

## フェーズB: 修正方針・実装差分の要点

### B-1 compress: PdfCompress is not defined の解消

- **static/js/pdf-compress.js**: 末尾で `globalThis.PdfCompress = PdfCompress` および `window.PdfCompress = PdfCompress` を設定。
- **templates/tools/pdf.html**: compress 分岐の実行直前に `const PC = globalThis.PdfCompress` を取得。`!PC` のときは「圧縮機能の読み込みに失敗しました。ページを再読み込みしてください。」を throw し、console.error で script パスと `typeof globalThis.PdfCompress` を出力（パスワード・個人情報は出さない）。

### B-2 lock/unlock をより多くのPDFで動かす

- **pypdf の strict=False**: `PdfReader(BytesIO(pdf_bytes), strict=False)` で読める範囲を広げる。
- **lock で既暗号化を拒否**: `encrypt_pdf` 内で `reader.is_encrypted` なら `ValueError("already_encrypted")` を投げ、API で **already_encrypted** を返す。
- **例外の分類**（lib 内）:
  - 読込失敗（PdfReader 構築や decrypt 以外の例外）→ **corrupt_pdf** または **unsupported_pdf**
  - 復号失敗（パスワード誤りは既存の invalid_password）→ その他は **decrypt_failed** のまま、必要に応じて **unsupported_encryption**
  - 暗号化失敗（encrypt/write）→ **encrypt_failed**、既暗号化は **already_encrypted**
- **error_code の追加**: lock に **already_encrypted**。unlock に **corrupt_pdf**, **unsupported_encryption**（判別可能な場合）。既存の decrypt_failed / encrypt_failed は維持。
- **API**: 上記 ValueError を app.py で受け、error_code と request_id のみ返す（例外文字列は返さない）。サーバログには request_id と例外型・スタックのみ（パスワードは絶対に出さない）。
- **フロント**: already_encrypted, corrupt_pdf, unsupported_pdf, unsupported_encryption に応じた文言を追加。「形式やサイズを確認」は **encrypt_failed** のときのみとし、already_encrypted / corrupt_pdf / unsupported_pdf ではより具体的な案内に出す。

**pikepdf / qpdf フォールバック**: 今回は **実装していない**。pypdf の `strict=False` と `already_encrypted` チェック・error_code の整理で対応。必要に応じて別タスクで pikepdf または qpdf CLI のフォールバックを検討する。

**実装済み**: PdfReader(..., strict=False)、encrypt_pdf で is_encrypted なら already_encrypted、読込/書き出し失敗で corrupt_pdf / unsupported_pdf。unlock の msgMap に corrupt_pdf, unsupported_encryption を追加。lock の msgMap に already_encrypted, corrupt_pdf, unsupported_pdf を追加。「形式やサイズを確認」は encrypt_failed のときのみ表示。

---

## 実装差分の要点（変更ファイル）

| ファイル | 変更内容 |
|----------|----------|
| static/js/pdf-compress.js | 末尾に globalThis.PdfCompress と window.PdfCompress を代入。 |
| templates/tools/pdf.html | compress 分岐で globalThis.PdfCompress を参照し、未定義時はユーザー向けエラー＋console.error。unlock/lock の msgMap に already_encrypted, corrupt_pdf, unsupported_pdf, unsupported_encryption を追加。 |
| lib/pdf_lock_unlock.py | PdfReader(..., strict=False)。encrypt_pdf で is_encrypted なら ValueError("already_encrypted")。読込・書き出し失敗で ValueError("corrupt_pdf") または既存の decrypt/encrypt 例外のまま。 |
| app.py | unlock: ValueError("corrupt_pdf"), ("unsupported_encryption") を _pdf_api_error で返却。lock: ValueError("already_encrypted") を _pdf_api_error で返却。ログは request_id と例外型・スタックのみ。 |

---

## フェーズC: 手動テスト手順

### compress
- compress モードで **PdfCompress is not defined が出ない**こと。
- 小さいPDFで圧縮が **成功**すること。

### lock
- これまで lock が **成功していたPDF** で再テストし、従来どおり成功すること。
- これまで lock が **失敗していたPDF** で再テストし、少なくとも同じ不明瞭な失敗にならないこと（already_encrypted や encrypt_failed で request_id 付きになること）。
- 既に暗号化されているPDFで lock を試すと **already_encrypted** のメッセージで止まること。

### unlock
- **非暗号化PDF**でパスワード空のまま実行し、成功すること。
- **暗号化PDF**でパスワード空 → need_password。
- 暗号化PDFで **誤パスワード** → incorrect_password。
- 暗号化PDFで **正しいパスワード** → 成功すること。

### パスワード非露出
- ブラウザ Console・Network・サーバログに **パスワードが含まれていない**こと。

---

以上。
