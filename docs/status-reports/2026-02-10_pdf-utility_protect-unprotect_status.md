# PDFユーティリティ「保護解除（復号）」と「保護付与（暗号化）」構想 ステータス分析レポート

**作成日**: 2026-02-10  
**目的**: 保護解除（復号）と保護付与（暗号化）を無料機能として提供する構想について、現行ブランチのコードのみを根拠に現状ステータスの事実確認とギャップ抽出を行う。**実装・挙動変更は一切行っていない（レポート追加のみ）。**

**重要な前提（安全/要件）**
- パスワードを破る/推測する/回避する機能は対象外。ユーザーが正しいパスワードを知っている前提での復号のみ対象とする。
- パスワードはログ出力しない、永続化しない（本レポートでもその方針を採用する）。
- クライアントのみで完結できる範囲と、サーバ側処理が必要な範囲を分離して整理する。

---

## 1. Summary（機能別ステータス表）

| 機能 | 現状（可/不可/一部可） | 根拠（ファイル:行） | 方針A（復号して処理）に必要な追加 | 方針B（保護付与） |
|------|------------------------|---------------------|-----------------------------------|-------------------|
| 復号して結合/抽出/分割したい | **不可** | pdf-lib はパスワード復号APIを持たず、load で暗号化検知→拒否メッセージ（pdf-ops.js:22,24-25,57,109,167,229） | クライアントのみでは困難。サーバ側で復号するか、別エンジン必要。 | — |
| 復号してPDF→画像/圧縮/画像抽出したい | **不可**（パスワード未入力のため） | getDocument に password を渡していない（pdf-render.js:94, pdf-compress.js:59, pdf-extract-images.js:56） | UI: パスワード入力。getDocument({ data, password })。PasswordException 等の出し分け。 | — |
| 出力PDFにパスワードを付けたい（保護付与） | **不可** | 現状コードに encrypt/ownerPassword/userPassword の設定なし。save は引数なし（pdf-ops.js:73,127,197 / pdf-compress.js:180 / pdf-images-to-pdf.js:162） | ライブラリの暗号化API利用（pdf-lib に setEncryption 等があればクライアントで可能。要調査）。 | 未実装 |
| 既存PDFのパスワードを正しいパスワードで外したPDFを出力したい（保護解除） | **不可** | 復号して保存する経路が存在しない（結合/抽出/分割は pdf-lib で復号不可。PDF.js は表示用で save しない） | 復号→新PDF生成のパイプライン（クライアントなら PDF.js で読んで pdf-lib で新規PDFに書き出す等。またはサーバ側で復号）。 | 未実装 |

---

## 2. 現状の事実（ファイル:行番号の根拠）

### 2-1. ブランチと対象範囲の確定

- **git branch**: `analysis/pdf-utility-encrypted-support-status`
- **git log -1**: `ec495d1 docs: add PDF utility encrypted PDF support status analysis report`
- **git status**: レポート追加前時点で、上記ブランチに未追跡ファイルあり。本レポート追加のみをコミット対象とする。

**/tools/pdf の参照関係**

| 種別 | ファイル | 行番号 | 内容 |
|------|----------|--------|------|
| ルート | app.py | 981-986 | @app.route('/tools/pdf'), render_template('tools/pdf.html', product=product) |
| テンプレート | templates/tools/pdf.html | — | 単一エントリ |
| CDN | templates/tools/pdf.html | 493 | pdf-lib 1.17.1: https://cdnjs.cloudflare.com/ajax/libs/pdf-lib/1.17.1/pdf-lib.min.js |
| CDN | templates/tools/pdf.html | 494 | pdf.js 3.11.174: https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js |
| 静的JS | templates/tools/pdf.html | 504-513 | file-validation.js, file-utils.js, zip-utils.js, tool-runner.js, pdf-range.js, pdf-ops.js, pdf-render.js, pdf-compress.js, pdf-images-to-pdf.js, pdf-extract-images.js |

---

### 2-2. A. 保護解除（復号・暗号化PDFの取り扱い）

#### pdf-lib を使う経路（結合/抽出/分割/ページ数取得）

- **PDFDocument.load の実質呼び出し**: **static/js/pdf-ops.js:22**  
  `return await PDFDocument.load(arrayBuffer);`（loadPdfOrThrowUserMessage 内。第2引数なし）
- **load を経由する箇所の全列挙**:
  - **pdf-ops.js:57** — mergePdfs: `const pdf = await loadPdfOrThrowUserMessage(arrayBuffer, file.name);`
  - **pdf-ops.js:109** — extractPdf: `const pdf = await loadPdfOrThrowUserMessage(arrayBuffer, file.name);`
  - **pdf-ops.js:167** — splitPdf: 同上
  - **pdf-ops.js:229** — getPageCount: 同上
- **ignoreEncryption の使用有無**: リポジトリ全体で grep した結果、**実装コード（*.js）には 0 件**。docs 内の記述のみ。→ **未使用**。
- **暗号化検知とメッセージ差し替え**:
  - **pdf-ops.js:6-8** — `isEncryptedPdfLibError(e)`: `e?.message` を toLowerCase し `'encrypted'` を含むか判定。
  - **pdf-ops.js:24-25** — catch 内で `isEncryptedPdfLibError(e)` なら `throw new Error('このPDFはパスワード保護されています。保護を外したPDFを使用してください。');` に差し替え。
  - **結論**: 暗号化PDFは load で例外 → 上記メッセージで拒否される。復号は行っていない。

#### PDF.js を使う経路（PDF→画像/圧縮/埋め込み画像抽出）

- **pdfjs.getDocument の呼び出し箇所の全列挙**:
  - **pdf-render.js:94** — `const loadingTask = pdfjs.getDocument({ data: arrayBuffer });`
  - **pdf-compress.js:59** — 同上
  - **pdf-extract-images.js:56** — 同上
- **password を渡しているか**: いずれも **`{ data: arrayBuffer }` のみ**。**password は渡していない。→ 未対応。**
- **PasswordException / onPassword / PasswordResponses**: リポジトリ内の *.js で grep した結果 **0 件**。→ **未実装。**
- **失敗時のユーザー向け表示**:
  - getDocument の try-catch で `isEncryptedPdfJsError(e)` なら同一の「このPDFはパスワード保護されています。保護を外したPDFを使用してください。」に差し替えて throw（pdf-render.js:97-99, pdf-compress.js:62-64, pdf-extract-images.js:59-61）。
  - **run(processor)** で処理する to-images / extract-images では、throw が toolRunner の processFile の catch に入り、**errors 配列**に message が入り、**handleComplete → showErrors(errors)** で表示（pdf.html:937, 974-985）。**一覧表示**（「以下のファイルでエラーが発生しました」＋ファイル名: message）。
  - **runBatch** で処理する compress では、throw が runOperation の try-catch に入り **handleError(error)**（pdf.html:871, 989-991）。**単一エラー表示**（「エラー: ${error.message}」）。

---

### 2-3. B. 保護付与（暗号化PDFの生成）

- **PDF を生成/保存している箇所の列挙**:
  - **pdf-ops.js:73** — `const pdfBytes = await mergedPdf.save();`（結合）
  - **pdf-ops.js:127** — `const pdfBytes = await extractedPdf.save();`（抽出）
  - **pdf-ops.js:197** — `const pdfBytes = await splitPdf.save();`（分割）
  - **pdf-compress.js:180** — `const pdfBytes = await compressedPdf.save();`（圧縮）
  - **pdf-images-to-pdf.js:162** — `const pdfBytes = await pdf.save();`（画像→PDF）
  - いずれも **save() は引数なし**。続けて `new Blob([pdfBytes], { type: 'application/pdf' })` で Blob 化し、toolRunner の outputs 経由でダウンロードまたは ZIP 化（tool-runner.js の downloadSingle / downloadAllZip）。
- **既存コード内の encryption 設定**:  
  **encrypt / setEncryption / ownerPassword / userPassword / security** を *.js および *.py で grep した結果、**暗号化設定に相当する呼び出しは存在しない**。  
  ヒットするのは isEncryptedPdfJsError 等の **エラーメッセージ判定用の文字列**（'password', 'encrypted'）のみ。
- **現行採用ライブラリで「出力暗号化」を実装できるか**:
  - **pdf-lib**: CDN 1.17.1 を読み込んでいるのみ。現状コードでは `PDFDocument.create()`, `load()`, `save()` のみ使用。**save に encryption オプションを渡す呼び出しはない。** pdf-lib の公式 API に setEncryption や save のオプションでパスワードを指定する仕様があるかは、本レポートでは未検証。**「現状コードからは出力暗号化の接点はなく、ライブラリのドキュメント確認または追加 API の利用が必要」** と整理する。
  - **PDF.js**: 表示・レンダリング用。PDF を新規生成して保存する機能はクライアント側の現行コードでは使っていない（pdf-lib で新規 PDF を組み立てている）。  
  → **保護付与は現状コードでは未実装。クライアントでやる場合は pdf-lib の暗号化 API の有無に依存する。**

---

### 2-4. 失敗系のログ/エラー表示の現状（運用観点）

- **「画像変換に失敗しました」が出る段階**（ファイル:行番号）:
  - **pdf-render.js:38, 47** — toBlobWithLog 内で toBlob が null、または toDataURL フォールバック失敗時の reject。
  - **pdf-compress.js:138** — canvas.toBlob のコールバックで blob が null のときの reject。
  - **pdf-extract-images.js:144** — 同上。
- **段階ログ（load_failed / render_failed / toBlob_failed）**:
  - **pdf-render.js:97** — load_failed、**140** — render_failed、**24, 46** — toBlob_failed。
  - **pdf-compress.js:62** — load_failed、**120** — render_failed、**132** — toBlob_failed。
  - **pdf-extract-images.js:59** — load_failed、**121** — render_failed、**137** — toBlob_failed。
- **暗号化関連の失敗が UI でどう見えるか**:
  - **runBatch で throw した場合**（merge, extract, split, compress）: **handleError(error)** により **単一メッセージ**「エラー: このPDFはパスワード保護されています。保護を外したPDFを使用してください。」（pdf.html:989-991）。
  - **run(processor) で throw した場合**（to-images, extract-images）: **showErrors(errors)** により **一覧**「以下のファイルでエラーが発生しました」＋ ファイル名: 上記メッセージ（pdf.html:974-985）。

---

## 3. ギャップ（要件別）

| 要件 | 現状 | 必要な追加 | 影響範囲 |
|------|------|------------|----------|
| **復号して結合/抽出/分割したい**（ユーザーがパスワードを入力） | **不可**。pdf-lib はパスワード復号 API を持たず、load 時点で暗号化なら拒否。 | クライアントのみ: 別エンジン（PDF.js で復号してページを取得し、pdf-lib で新 PDF に書き出す等、設計要検討）またはサーバ側で復号（後述）。 | pdf-ops.js の load 経路、または新規エンドポイント＋サーバ処理。 |
| **復号してPDF→画像/圧縮/画像抽出したい**（ユーザーがパスワードを入力） | **不可**。getDocument に password を渡していない。 | パスワード入力 UI（templates/tools/pdf.html）。runOperation から options に password を渡す。pdf-render.js / pdf-compress.js / pdf-extract-images.js で getDocument({ data, password }) に変更。PasswordException 等の出し分けとメッセージ（「パスワードが必要」「パスワードが違います」）。パスワードはメモリのみ・ログ/永続化しない。 | テンプレート、3つの JS、toolRunner の ctx または options 経路。 |
| **出力PDFにパスワードを付けたい**（保護付与） | **不可**。save に encryption 系の引数なし。コード内に encrypt/ownerPassword/userPassword の設定なし。 | 採用ライブラリ（pdf-lib 等）の暗号化 API の確認と利用。あれば save 前の設定または save(options) でパスワード付与。パスワードは UI から取得し、メモリのみ・ログ/永続化しない。 | pdf-ops.js, pdf-compress.js, pdf-images-to-pdf.js の save 前処理、およびオプション UI。 |
| **既存PDFのパスワードを正しいパスワードで外したPDFを出力したい**（保護解除） | **不可**。復号して新 PDF を出力する経路がない。 | クライアント: PDF.js で password 付き getDocument → ページ取得 → pdf-lib で新 PDF に追加 → save（暗号化なし）。またはサーバ側: 復号 API を用意し、クライアントはファイル＋パスワードを送り、復号済み PDF を返す。いずれもパスワードはログ/永続化しない。 | 新規フロー（「保護を解除」モード）と、PDF.js 連携またはサーバ側エンドポイント。 |

---

## 4. アーキ案比較（クライアント完結 / サーバ併用）

### 案1: クライアント完結（できる範囲のみ）

- **内容**: PDF.js の getDocument({ data, password }) とパスワード入力 UI を連携し、PDF→画像・圧縮・埋め込み画像抽出で「復号して処理」を実現する。結合/抽出/分割は pdf-lib が復号に対応していないため、クライアントのみでは「復号して結合/抽出/分割」は困難。保護付与は、pdf-lib に暗号化 API があれば save 前の設定で対応可能（要調査）。「保護解除して新 PDF を出力」は、PDF.js で読んで pdf-lib で新 PDF に書き出すパイプラインでクライアント完結の可能性あり。
- **セキュリティ**: パスワードはブラウザのメモリと UI のみ。サーバに送らない。ログ・永続化しない。
- **コスト/運用**: 既存と同様にクライアントの CPU/メモリで完結。サーバの PDF 処理負荷は増えない。
- **既存構成への侵襲度**: テンプレートに入力欄追加、3つの PDF.js 利用 JS に password 渡しとエラー出し分け、runOperation で options に password を載せる。新規モード「保護解除」を足す場合は、PDF.js → pdf-lib のパイプライン追加。**中程度。**

### 案2: サーバ側で暗号化/復号を行う

- **内容**: Flask に「復号」「暗号化」用のエンドポイントを追加。アップロードされた PDF とパスワード（HTTPS で送信）を受け、サーバで復号または暗号化して結果の PDF を返す。Python では pypdf, pikepdf 等で復号/暗号化が可能。**現状の requirements.txt には PDF 用ライブラリは含まれていない**（Flask, openpyxl, playwright, gunicorn 等のみ）。Dockerfile も qpdf 等のシステムパッケージは入れておらず、Python 3.11-slim + Chrome/Playwright が中心。**導入の「可能性」**: requirements.txt に pypdf や pikepdf を追加し、復号/暗号化のロジックを app.py または別モジュールに実装する、あるいは apt-get で qpdf を入れ、subprocess で呼ぶ、といった構成が考えられる。導入可否・ライセンスは未検証。
- **セキュリティ**: パスワードがサーバに渡る。HTTPS 必須。サーバ側でログ・永続化しない設計が必須。一時ファイルの扱いと削除の徹底が必要。
- **コスト/運用**: サーバの CPU/RAM を使用。Render 等ではワーカー数・メモリ制限の影響を受ける。大容量 PDF はタイムアウト・メモリに注意。
- **既存構成への侵襲度**: 新規ルート、新規依存（requirements.txt）、場合により Dockerfile のパッケージ追加。クライアントはアップロード＋パスワード送信＋結果ダウンロードの UI。**やや大。**

---

## 5. 次に Cursor に実装依頼するための「論点リスト」

- パスワード入力欄を「全モード共通」にするか、「PDF.js を使うモード（PDF→画像/圧縮/埋め込み画像抽出）のみ」にするか。
- 復号して結合/抽出/分割を行うか行わないか。行う場合、クライアントで PDF.js からページを取得して pdf-lib で新 PDF に組み立てる設計とするか、サーバ側で復号するか。
- 「保護を解除した PDF を出力」機能を提供するか。提供する場合、クライアント完結（PDF.js + pdf-lib）とサーバ側のどちらとするか。
- 「出力 PDF にパスワードを付与」を提供するか。提供する場合、pdf-lib の暗号化 API の有無を確認したうえで、クライアントで実装するか。
- パスワードを「メモリのみ・ログ/永続化しない」ことをコードレビューとドキュメントでどう担保するか（コメント、チェックリスト）。
- 失敗時のメッセージ出し分け（「パスワードが必要」「パスワードが違います」「このPDFはパスワード保護されています…」）をどこまで細かくするか。
- サーバ側を採用する場合、使用する Python ライブラリ（pypdf / pikepdf 等）または qpdf の選定と、requirements.txt / Dockerfile の変更方針。

---

**本レポートは分析のみであり、実装・挙動変更は一切行っていません。**
