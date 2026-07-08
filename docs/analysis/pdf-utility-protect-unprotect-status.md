# PDFユーティリティ「保護解除（復号して出力）」と「保護付与（暗号化して出力）」現状ステータス 事実確認レポート

**目的**: 現行ブランチのコードのみを根拠に、保護解除・保護付与の対応状況を断定できる形で整理する。実装・挙動変更・UI追加・依存追加・設定変更・コミットは一切しない（レポート追加のみ）。パスワード破り/回避/推測は対象外（正しいパスワードを知っている前提の復号のみ）。

---

## 1) 対象ブランチの確定

```
git branch --show-current
analysis/pdf-utility-encrypted-support-status

git log -1 --oneline
e414efe docs: add PDF utility protect/unprotect (encrypt/decrypt) status analysis report

git status --short
?? docs/analysis/
?? docs/autofill_queue_ops_risk_report_2026-02-10.md
... (他未追跡あり)
```

- **対象ブランチ**: `analysis/pdf-utility-encrypted-support-status`
- **対象コミット**: `e414efe`
- **変更**: レポート追加以外の変更は行わない。

---

## 2) /tools/pdf の構成（参照元→参照先）

| 参照元 | 参照先 | 根拠 |
|--------|--------|------|
| Flask | app.py | **app.py:981** `@app.route('/tools/pdf')`、**app.py:985-986** `get_product_by_path('/tools/pdf')`、`return render_template('tools/pdf.html', product=product)` |
| ルート | テンプレート | **templates/tools/pdf.html**（単一エントリ） |
| テンプレート | CDN | **pdf.html:493** pdf-lib 1.17.1、**pdf.html:494** pdf.js 3.11.174、**pdf.html:501** jszip 3.10.1 |
| テンプレート | static JS | **pdf.html:504-513** の順: file-validation.js, file-utils.js, zip-utils.js, tool-runner.js, pdf-range.js, **pdf-ops.js**, **pdf-render.js**, **pdf-compress.js**, pdf-images-to-pdf.js, **pdf-extract-images.js** |

---

## 3) mode 別の処理フロー（runOperation → どの関数へ）

根拠: **templates/tools/pdf.html:771-868**（runOperation 内の mode 分岐）。

| mode | 処理の流れ | 根拠（ファイル:行） |
|------|------------|---------------------|
| merge | runOperation → runBatch → **PdfOps.mergePdfs(files, ctx)** | pdf.html:782-784 |
| extract | runOperation → **PdfOps.getPageCount(files[0])** → バリ → runBatch → **PdfOps.extractPdf(files[0], pages, ctx)** | pdf.html:786-798 |
| split | runOperation → **PdfOps.getPageCount(files[0])** → バリ → runBatch → **PdfOps.splitPdf(files[0], pageGroups, ctx)** | pdf.html:800-818 |
| to-images | runOperation → run(processor) → **PdfRender.pdfToImages(file, { format, scale, quality }, ctx)** | pdf.html:820-830 |
| compress | runOperation → runBatch → **PdfCompress.compressPdfByRasterize(files[0], { quality, scale, maxLongEdge }, ctx)** | pdf.html:833-842 |
| images-to-pdf | runOperation → runBatch → **PdfImagesToPdf.imagesToPdf(files, { pageSize, fit, margin, background }, ctx)** | pdf.html:845-854 |
| extract-images | runOperation → run(processor) → **PdfExtractImages.extractEmbeddedImages(file, { format, quality, maxPerPdf, includePageIndexInName: true }, ctx)** | pdf.html:857-868 |

---

## 4) 「保護解除（復号）」観点の事実確認

### PDF.js（pdfjs.getDocument）呼び出しと password 系の有無

**getDocument 呼び出しの全列挙**

| ファイル | 行番号 | コード断片 |
|----------|--------|------------|
| static/js/pdf-render.js | 94 | `const loadingTask = pdfjs.getDocument({ data: arrayBuffer });` |
| static/js/pdf-compress.js | 59 | `const loadingTask = pdfjs.getDocument({ data: arrayBuffer });` |
| static/js/pdf-extract-images.js | 56 | `const loadingTask = pdfjs.getDocument({ data: arrayBuffer });` |

- いずれも第1引数は **`{ data: arrayBuffer }` のみ**。`password` キーは渡していない。

**grep 結果（password / onPasswordCallback / PasswordResponses）**

- 検索: `getDocument\(|password|onPasswordCallback|PasswordResponses`（static/js 内 *.js）
- ヒット: **getDocument** は上記3箇所。**password** は isEncryptedPdfJsError 内の **文字列** `'password'`（エラー判定用）のみ。**onPasswordCallback** / **PasswordResponses** は **0 件**。
- 別検索: `onPasswordCallback|PasswordResponses|PasswordException`（リポジトリ内 *.js）→ **0 件**。

**結論**: getDocument に password を渡す実装はない。onPasswordCallback / PasswordResponses / PasswordException の利用はない。

### UI 側のパスワード入力欄

- 検索: `password|type="password"|パスワード`（templates/tools/pdf.html）
- 結果: **No matches found**（0 件）。

**結論**: パスワード入力欄は存在しない。

### password が options/ctx 経由で渡る経路

- **tool-runner.js**  
  - **processFile**（run 用）: **213-216 行**で `ctx = { index, signal: { cancelled: this.cancelled } }` のみ。**219 行** `await processor(file, ctx)`。  
  - **runBatch**: **283-301 行**で ctx は `signal`, `setTaskState`, `setProgress` のみ。
- **runOperation**（pdf.html:821-824, 834-841, 858-867）で取得しているのは、`image-format`, `image-scale`, `image-quality`, `compress-quality`, `compress-scale`, `compress-max-long-edge`, `extract-images-format` 等の要素の value のみ。**password を取得している箇所はない。**

**結論**: password を options や ctx に載せて各処理に渡す経路は存在しない。

### 「復号して PDF として再出力する」パイプラインの有無

- **結合/抽出/分割**: pdf-lib の `loadPdfOrThrowUserMessage` → `PDFDocument.load(arrayBuffer)` のみ。暗号化時は例外をキャッチしてメッセージ差し替えで拒否（pdf-ops.js:22,24-25）。復号して新 PDF を組み立てる処理はない。
- **to-images / compress / extract-images**: PDF.js で getDocument → getPage → render 等。compress は「読み取り → ラスタ → pdf-lib で新 PDF 保存」だが、入力が暗号化の場合は getDocument で失敗し、復号してから新 PDF を出す経路にはなっていない。
- **「入力 PDF をパスワードで復号し、その内容で新規 PDF を 1 本出力する」** ようなモードや関数は、どの JS にも存在しない。

**欠けている部品の列挙**

1. **UI**: パスワード入力欄（例: `input type="password"`）。
2. **受け渡し**: runOperation でパスワードを読み、PdfRender / PdfCompress / PdfExtractImages の第2引数 options に `password` を載せる経路。runBatch の ctx に password を載せる経路（compress 用）。
3. **API 呼び出し**: 各所での `getDocument({ data: arrayBuffer, password: options.password })` の利用。
4. **「復号→新 PDF 出力」パイプライン**: PDF.js で getDocument({ data, password }) → ページ取得 → pdf-lib で新 PDF に追加 → save の一連処理（現状なし）。

---

## 5) 「保護付与（暗号化）」観点の事実確認

### 出力 PDF を生成/保存している save 呼び出しの全列挙

| ファイル | 行番号 | コード断片 |
|----------|--------|------------|
| static/js/pdf-ops.js | 73 | `const pdfBytes = await mergedPdf.save();` |
| static/js/pdf-ops.js | 127 | `const pdfBytes = await extractedPdf.save();` |
| static/js/pdf-ops.js | 197 | `const pdfBytes = await splitPdf.save();` |
| static/js/pdf-compress.js | 180 | `const pdfBytes = await compressedPdf.save();` |
| static/js/pdf-images-to-pdf.js | 162 | `const pdfBytes = await pdf.save();` |

- いずれも **`save()` は引数なし**。続けて Blob 化し toolRunner の outputs 経由でダウンロード/ZIP。

### 暗号化設定に相当する記述の有無

- 検索: `encrypt|setEncryption|userPassword|ownerPassword|permissions`（static/js 内 pdf*.js）
- ヒット: **encrypt / setEncryption / userPassword / ownerPassword / permissions** という名前の **API 呼び出しやプロパティ設定は 0 件**。  
  - ヒットするのは isEncryptedPdfJsError 等の **文字列** `'password'`, `'encrypted'`（エラー判定用）のみ。

**結論**: 出力 PDF にパスワードを付与する、または権限を設定するような API の呼び出しは存在しない。

---

## 6) サーバ側の可能性（コード根拠のみ）

### requirements.txt 等の PDF 暗号化/復号ライブラリ

- **requirements.txt**（リポジトリ内）:  
  `Flask==2.3.3`, `openpyxl`, `playwright`, `jpholiday`, `psutil`, `gunicorn`, `requests`, `beautifulsoup4` のみ。
- **pypdf / pikepdf / PyPDF2** 等の PDF 用ライブラリは **記載なし**。

**結論**: 現状、PDF の暗号化/復号用の Python 依存は入っていない。

### Dockerfile / Render 設定での qpdf 等

- **Dockerfile**: `apt-get install` で入っているのは、Chrome 用の wget/gnupg/ca-certificates、google-chrome-stable、フォント・ライブラリ群（fonts-*, lib*）のみ。**qpdf や poppler-utils 等の PDF 用パッケージはインストールしていない。**

**結論**: サーバ側の「現状」として、qpdf 等のシステム依存はなし。

---

## 7) Summary（可/不可/未実装）

| 項目 | ステータス | 根拠の要約 |
|------|------------|------------|
| 保護解除（パスワード入力で読み込み） | **不可** | getDocument に password を渡していない（pdf-render.js:94, pdf-compress.js:59, pdf-extract-images.js:56）。UI にパスワード欄なし（pdf.html grep 0 件）。 |
| 復号して PDF として再出力 | **未実装** | 上記パスワード経路なしに加え、「復号→新 PDF 生成→save」のパイプラインがコードに存在しない。 |
| 保護付与（出力 PDF を暗号化） | **未実装** | save は全箇所で引数なし（pdf-ops.js:73,127,197 / pdf-compress.js:180 / pdf-images-to-pdf.js:162）。encrypt/userPassword/ownerPassword 等の設定 0 件。 |

---

## 8) ギャップ（UI / 受け渡し / API）

| 観点 | 不足しているもの |
|------|------------------|
| **UI** | パスワード入力欄（type="password"）。templates/tools/pdf.html に現状なし。 |
| **受け渡し** | runOperation から取得した password を、PdfRender.pdfToImages / PdfCompress.compressPdfByRasterize / PdfExtractImages.extractEmbeddedImages の第2引数 options に載せる経路。runBatch の ctx に password を載せる経路（compress 用）。tool-runner の ctx は現状 index と signal のみ（tool-runner.js:213-216, 283-301）。 |
| **API** | getDocument({ data: arrayBuffer, password: ... }) の第2キー。onPasswordCallback / PasswordResponses 等の利用（現状 0 件）。「復号→新 PDF に書き出し→save」の一連処理。save 前または save 時の暗号化オプション（現状なし）。 |

---

## 9) 次の論点

- パスワード入力欄を「PDF を読み込む全モード」に置くか、「to-images / compress / extract-images のみ」にするか。
- getDocument に password を渡す実装を入れる場合、options の取得元（runOperation 内の getElementById 等）と、各 JS の第2引数 options に password を追加する仕様。
- 「復号して新 PDF を 1 本出力する」機能を提供するか。提供する場合、PDF.js（password 付き）と pdf-lib（新規 PDF 作成）を連携するパイプラインの設計。
- 「出力 PDF にパスワード付与」を提供するか。提供する場合、採用ライブラリ（pdf-lib 等）の暗号化 API の有無確認と、save 前/時のオプション仕様。
- パスワードをログ・永続化・URL・LocalStorage・Cookie に一切出さないことを、レビュー・ドキュメントでどう担保するか。

---

**本レポートは事実確認のみ行っており、実装・挙動変更・UI追加・依存追加・設定変更・コミットは一切行っていません。**
