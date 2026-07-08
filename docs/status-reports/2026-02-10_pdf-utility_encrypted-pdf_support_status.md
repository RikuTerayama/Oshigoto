# PDFユーティリティ 暗号化PDF対応ステータス分析レポート

**作成日**: 2026-02-10  
**目的**: 暗号化PDF（パスワード保護/権限制限）を無料機能としてどこまで対応できるか、現状コードのステータスを断定できる分析を行う。**実装は一切しない（レポート追加のみ）。**

**前提**
- 「暗号を破る/迂回する」機能は対象外。ユーザーがパスワードを知っている前提で「入力して処理できるか」を検討する。
- 既存の2エラー: (1) pdf-lib: Input document to PDFDocument.load is encrypted... (2) PDF→画像: 画像変換に失敗しました。

---

## 1. Summary（機能別の結論）

| 機能 | 現状 | 方針A（パスワード入力で処理） | 方針B（暗号化は明示拒否） |
|------|------|------------------------------|----------------------------|
| **結合** | 暗号化PDFで load 失敗 → ユーザー向けメッセージに差し替え済み | **困難**。pdf-lib はパスワード復号APIを持たない。ignoreEncryption は「読み捨て」程度で編集・保存の保証なし。 | **軽微改修で完了済み**。明示拒否メッセージ表示。 |
| **抽出** | 同上（getPageCount → extractPdf の両方で loadPdfOrThrowUserMessage 経由） | **困難**。同上。 | **軽微改修で完了済み**。 |
| **分割** | 同上 | **困難**。同上。 | **軽微改修で完了済み**。 |
| **PDF→画像** | getDocument 失敗時は暗号化判定で同一メッセージに差し替え済み。toBlob null 時は段階ログ追加済み。 | **軽微改修で可能**。PDF.js の getDocument({ data, password }) と onPasswordCallback でパスワード入力UIと連携可能。 | **軽微改修で完了済み**。 |
| **圧縮（ラスタライズ）** | getDocument のみで load、render/toBlob で「画像変換に失敗しました」が出得る。暗号化時は load_failed で同一メッセージに差し替え済み。 | **軽微改修で可能**。PDF.js に password を渡す改修で対応可能。 | **軽微改修で完了済み**。 |
| **埋め込み画像抽出** | 同上。getDocument で load、toBlob で失敗時は toBlob_failed ログ＋拒否メッセージ。 | **軽微改修で可能**。同上。 | **軽微改修で完了済み**。 |
| **画像→PDF** | 入力は画像のみ。PDFの load は使わない。 | 対象外（暗号化PDFを読まない） | 対象外。 |

**結論**
- **方針B（暗号化は明示拒否）**: 結合・抽出・分割・PDF→画像・圧縮・埋め込み画像抽出は、現状コードで既に「ユーザー向けメッセージに差し替え」および「load_failed/render_failed/toBlob_failed の段階ログ」が入っており、**最小の安全策としては完了済み**。
- **方針A（パスワード入力で処理）**: **pdf-lib 系（結合/抽出/分割）は、クライアントのみの無料機能としては困難**。pdf-lib はパスワード復号を提供しておらず、ignoreEncryption は「暗号化を無視して読む試み」であり、復号できない場合は内容が得られず編集・保存も保証されない。**PDF.js 系（PDF→画像・圧縮・埋め込み画像抽出）は、getDocument に password を渡す改修とパスワード入力UIの追加で、軽微改修で可能**。ただしパスワードの保持・ログ出力をしない設計と、失敗時のメッセージ出し分け（暗号化/パスワード必要/パスワード誤り）の整理が必要。

---

## 2. 現状フロー（mode → JS → 表示）

### 2-1. mode 一覧と JS の対応

| mode（value） | 表示名 | 呼び出しJS | エントリ関数 |
|---------------|--------|------------|--------------|
| merge | 結合 | pdf-ops.js | PdfOps.mergePdfs(files, ctx) |
| extract | 抽出 | pdf-ops.js | 先に PdfOps.getPageCount(files[0]) → PdfOps.extractPdf(files[0], pages, ctx) |
| split | 分割 | pdf-ops.js | 先に PdfOps.getPageCount(files[0]) → PdfOps.splitPdf(files[0], pageGroups, ctx) |
| to-images | PDF→画像 | pdf-render.js | PdfRender.pdfToImages(file, options, ctx) |
| compress | 圧縮 | pdf-compress.js | PdfCompress.compressPdfByRasterize(files[0], options, ctx) |
| images-to-pdf | 画像→PDF | pdf-images-to-pdf.js | PdfImagesToPdf.imagesToPdf(files, options, ctx) |
| extract-images | 埋め込み画像抽出 | pdf-extract-images.js | PdfExtractImages.extractEmbeddedImages(file, options, ctx) |

- **templates/tools/pdf.html**: mode は `<select id="mode">`（337行）。runOperation() は 771行～。各 mode の分岐は 781～869 行（merge → runBatch + PdfOps.mergePdfs / extract → getPageCount + runBatch + PdfOps.extractPdf / split → getPageCount + runBatch + PdfOps.splitPdf / to-images → run + PdfRender.pdfToImages / compress → runBatch + PdfCompress.compressPdfByRasterize / images-to-pdf → runBatch + PdfImagesToPdf.imagesToPdf / extract-images → run + PdfExtractImages.extractEmbeddedImages）。

### 2-2. エラー表示経路

- **runBatch が throw した場合**（merge / extract / split / compress / images-to-pdf）: runOperation の try-catch（869-872行）で catch → **handleError(error)**（871行）。handleError（989-992行）は error-section を表示し、**error-message に「エラー: ${error.message}」** を設定する。
- **run(processor) で processFile が reject した場合**（to-images / extract-images）: toolRunner が error を this.errors に積み、onComplete で handleComplete → **showErrors(errors)**（937行）。showErrors（974-983行）は error-section を表示し、**error-message に「以下のファイルでエラーが発生しました」＋各 sourceIndex/file.name と message の一覧** を innerHTML で設定する。
- **toolRunner**: onError は handleError を指す（525行）。run 内で processFiles が throw すると onError が呼ばれるが、現状 processFiles は throw せず errors 配列に集約するため、run 系のエラーは showErrors 経由で表示される。

### 2-3. 追加UIの入れ場所候補

- **操作設定**の「オプション領域」は、mode に応じて表示される **option-group** のブロック（352-454行）: extract-options, split-options, to-images-options, to-images-scale, to-images-quality, compress-options, images-to-pdf-options, extract-images-options。これらと同様に、**「パスワード保護PDF用」の option-group**（例: id="password-pdf-options"）を追加し、mode が to-images / compress / extract-images のいずれかのときだけ表示する、あるいは全 mode 共通で「パスワード（任意）」入力欄を置く、といった配置が可能。run-button の直上（456行付近）にブロックを挿入するか、既存の option-group の末尾に追加する形が自然。

---

## 3. エラー1の一次原因（根拠付き）

- **事象**: 暗号化PDFで結合・抽出・分割を実行すると、pdf-lib が「Input document to PDFDocument.load is encrypted. You can use PDFDocument.load(..., { ignoreEncryption: true })」に類する例外を投げる（または、現状は loadPdfOrThrowUserMessage により「このPDFはパスワード保護されています。保護を外したPDFを使用してください。」に差し替え済み）。
- **一次原因**: **pdf-lib の PDFDocument.load は、暗号化されたPDFをデフォルトでは受け付けない**。load の実装がドキュメントの暗号化フラグを検出し、オプションなしの場合は例外を投げる。
- **コード根拠**:
  - **static/js/pdf-ops.js**: 実際の load は **loadPdfOrThrowUserMessage** 内の **22行** `return await PDFDocument.load(arrayBuffer);` で実行される。この関数は mergePdfs（56行）、extractPdf（109行）、splitPdf（167行）、getPageCount（229行）から呼ばれる。いずれも **第2引数（ignoreEncryption）は渡していない**。
  - **ignoreEncryption の使用有無**: リポジトリ全体を grep した結果、**ignoreEncryption という文字列は分析レポート（docs）内の記述のみで、実装コード内には存在しない**。よって「現状は ignoreEncryption は未使用」と断定できる。

---

## 4. エラー2の一次原因候補（切り分け手順付き）

- **事象**: 「画像変換に失敗しました」がユーザーに表示される。PDF→画像・圧縮・埋め込み画像抽出のいずれかで発生し得る。
- **表示箇所**: いずれも **canvas.toBlob** のコールバックで **blob が null** の場合に reject(new Error('画像変換に失敗しました')) している箇所、または toDataURL フォールバックまで失敗した場合。
  - **static/js/pdf-render.js**: toBlobWithLog 内 38行（reject）、47行（toDataURL フォールバック失敗時の reject）。
  - **static/js/pdf-compress.js**: 138行（toBlob コールバックで null 時の reject）。
  - **static/js/pdf-extract-images.js**: 144行（同様）。
- **一次原因候補**
  1. **toBlob が null を返した**: ブラウザが canvas を Blob に変換できなかった（メモリ不足・セキュリティ制限・巨大 canvas 等）。この場合、**toBlob_failed** の console.error が既に出力される（pdf-render.js 24行付近、pdf-compress.js 132行付近、pdf-extract-images.js 137行付近）。
  2. **getDocument または page.render が先に失敗した**: 暗号化PDFの場合、getDocument の promise が reject する、または PDF.js が PasswordException を投げる。現状は load_failed の try-catch で **isEncryptedPdfJsError** 判定し、暗号化と判断した場合は「このPDFはパスワード保護されています。保護を外したPDFを使用してください。」に差し替えて throw するため、「画像変換に失敗しました」ではなくなる。それ以外の getDocument/render の失敗は、load_failed または render_failed の console.error が出たうえで、error.message がそのまま toolRunner.errors に入り showErrors に表示される。
- **切り分け手順**
  - 本番ブラウザで「画像変換に失敗しました」が出た直前に、Console に **[PdfRender] load_failed / render_failed / toBlob_failed** のいずれかが出力されているかを確認する。toBlob_failed のみなら「toBlob が null」が一次原因。load_failed が先に出ていれば getDocument 失敗が一次原因。render_failed が先なら page.render 失敗が一次原因。

---

## 5. 暗号化PDF対応の可否（機能別）

- **結合・抽出・分割（pdf-lib 系）**
  - **現状**: 暗号化PDFでは loadPdfOrThrowUserMessage 内で PDFDocument.load が throw し、暗号化判定でユーザー向けメッセージに差し替え済み。**方針Bとしては完了**。
  - **方針A（パスワード入力で処理）**: **困難**。pdf-lib の公開APIには「パスワードを渡して復号する」機能がない。**ignoreEncryption: true** は「暗号化を無視して読み込む」オプションであり、**復号を行うものではない**。パスワードで保護されたPDFでは、中身が復号されないためページ取得や編集が正しく行えず、save しても空または壊れたPDFになる可能性が高い。公式ドキュメント・ソース上も「パスワード解除はサポートしていない」旨が示されている。したがって、結合/抽出/分割を「パスワード入力で対応」するには、**別エンジン（サーバ側の qpdf 等で復号してから返す、または wasm で復号できるライブラリを組み込む）の導入**が必要となり、軽微改修では成立しない。
- **PDF→画像・圧縮・埋め込み画像抽出（PDF.js 系）**
  - **現状**: getDocument 失敗時に暗号化判定でユーザー向けメッセージに差し替え済み。**方針Bとしては完了**。
  - **方針A**: **軽微改修で可能**。PDF.js の getDocument は **password** オプションと **onPasswordCallback** をサポートする。getDocument({ data: arrayBuffer, password: userPassword }) を渡せば、パスワードが正しければ解読してレンダリングできる。必要改修点は、(1) パスワード入力UI（オプション領域に input type="password" 等）の追加、(2) 実行時にその値を取得し、pdf-render.js / pdf-compress.js / pdf-extract-images.js の getDocument 呼び出しに **password** を渡す、(3) getDocument の promise が reject したとき、PDF.js のエラー種別（PasswordResponses.NEED_PASSWORD / INCORRECT_PASSWORD 等）に応じて「パスワードが必要です」「パスワードが違います」等のメッセージに差し替える、の3点。パスワードはメモリ上でだけ使い、ログやストレージには出さない設計にすれば、セキュリティ上も無料クライアント機能の範囲で対応可能。

---

## 6. 方針案A/B（最小改修点とリスク）

### 方針A: ユーザーにパスワードを入力させて処理（許可された復号）

- **pdf-lib 系（結合/抽出/分割）**: 上記のとおり **困難**。ignoreEncryption は復号しないため、パスワード保護PDFの実用対応にはならない。対応するならサーバ側で qpdf 等で復号するか、wasm 等の別エンジンが必要。
- **PDF.js 系（PDF→画像・圧縮・埋め込み画像抽出）**: **最小改修点**は、(1) templates/tools/pdf.html にパスワード入力用の option-group と input を追加し、mode に応じて表示する、(2) runOperation 内でその値を読み、run/runBatch に渡す（または processor に ctx 経由で渡す）、(3) pdf-render.js / pdf-compress.js / pdf-extract-images.js の getDocument を getDocument({ data: arrayBuffer, password: ctx.password || undefined }) のように変更し、失敗時に PDF.js のエラー種別で「暗号化PDFです」「パスワードが必要です」「パスワードが違います」を出し分ける。**リスク**: パスワードを DOM やグローバル変数に長時間置かない、ログに絶対に出さない、という運用が必要。大容量PDFではメモリと時間が増える点は通常PDFと同様。
- **UX**: 失敗時は「パスワードが違います」等を表示し、同じファイルで再実行する際にパスワードを再入力できる導線を残す。

### 方針B: 暗号化PDFは明示的に拒否してメッセージ案内（現状の最小安全策）

- **最小改修点**: 既に実装済み。loadPdfOrThrowUserMessage（pdf-ops.js）および各 PDF.js 利用ファイルの getDocument 周りの try-catch で、暗号化/パスワード系エラーを検知し「このPDFはパスワード保護されています。保護を外したPDFを使用してください。」に差し替えている。**リスク**: パスワードを知っているユーザーにも「保護を外したPDFを使用してください」と案内することになり、パスワード入力で処理したい需要には応えられない。一方、実装コスト・セキュリティ・予測可能性の面では最も安全。

### 追加実装が必要な場合の選択肢（文章で整理）

- **クライアントのみで完結（PDF.js 中心）**: PDF→画像・圧縮・埋め込み画像抽出については、パスワード入力UIと getDocument の password 渡しだけで、サーバを介さずに対応できる。結合/抽出/分割は pdf-lib に依存しているため、クライアントのみではパスワード復号に対応できず、PDF.js で「読んで表示する」用途に限定するか、または結合/抽出/分割は暗号化PDFを拒否したまま、画像系機能だけパスワード対応にする、という棲み分けが現実的である。
- **結合/抽出/分割まで暗号化PDF対応する場合**: pdf-lib では復号できないため、**サーバ側で qpdf 等で復号してからクライアントに返す**か、**wasm で復号できるライブラリを組み込む**必要がある。いずれも「軽微改修」の範囲を超え、新規コンポーネント・ビルド・デプロイの検討が必要。セキュリティの観点では、サーバにパスワードを送る場合は HTTPS と「パスワードを保存しない」ポリシーが必須となる。
- **セキュリティ/UX**: パスワードはメモリ上でだけ使用し、ログ・ストレージ・URL に含めない。失敗時は「パスワードが必要です」「パスワードが違います」を出し分け、再入力しやすいようにする。大容量PDFでは処理時間とメモリ使用量が増えるため、キャンセルや進捗表示は現状のまま維持するのがよい。

---

## 7. 本番で採取すべき観測ログ

- **暗号化PDFで結合を実行したとき**
  - **期待**: エラー表示が「このPDFはパスワード保護されています。保護を外したPDFを使用してください。」（または mergePdfs の catch 経由で「xxx.pdfの処理に失敗しました: このPDFは…」）。
  - **Console**: スタックの起点が loadPdfOrThrowUserMessage（pdf-ops.js）→ PDFDocument.load であることを確認。もし古いブランチで差し替え前なら「Input document to PDFDocument.load is encrypted」の全文を採取。
- **暗号化PDFで PDF→画像を実行したとき**
  - **期待**: getDocument が失敗し、PasswordException またはそれに類するエラーになるか、または toBlob が null になるか。現状コードでは getDocument 失敗時に isEncryptedPdfJsError で判定し、同一のユーザー向けメッセージに差し替える。
  - **Console**: **[PdfRender] load_failed** が出力され、その中で error に PasswordException や message に "password" / "encrypted" が含まれるかを確認。**render_failed** や **toBlob_failed** が先に出るかどうかも記録する。
- **Network**
  - **worker**: `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js` が 200 で読まれているか。404 や CORS エラーがないか。

---

## 8. 参照（ファイル＋行番号）

| ファイル | 行番号 | 内容 |
|----------|--------|------|
| templates/tools/pdf.html | 337-349 | mode 一覧（select id="mode"） |
| templates/tools/pdf.html | 352-454 | 各 mode 用 option-group（追加UI候補はこの前後） |
| templates/tools/pdf.html | 493-494 | pdf-lib 1.17.1 / pdf.js 3.11.174 の CDN |
| templates/tools/pdf.html | 509-513 | pdf-ops.js, pdf-render.js, pdf-compress.js, pdf-extract-images.js の読み込み |
| templates/tools/pdf.html | 525 | toolRunner onError: handleError |
| templates/tools/pdf.html | 771-872 | runOperation、各 mode の分岐と catch → handleError |
| templates/tools/pdf.html | 974-992 | showErrors、handleError |
| templates/tools/pdf.html | 480-482 | error-section, error-message |
| static/js/pdf-ops.js | 6-8 | isEncryptedPdfLibError |
| static/js/pdf-ops.js | 16-28 | loadPdfOrThrowUserMessage、22行で PDFDocument.load(arrayBuffer) |
| static/js/pdf-ops.js | 56, 109, 167, 229 | mergePdfs / extractPdf / splitPdf / getPageCount での loadPdfOrThrowUserMessage 呼び出し |
| static/js/pdf-render.js | 80 | workerSrc (CDN 3.11.174) |
| static/js/pdf-render.js | 94-101 | getDocument({ data: arrayBuffer })、try-catch と load_failed |
| static/js/pdf-render.js | 24, 38, 46-47 | toBlob_failed と「画像変換に失敗しました」 |
| static/js/pdf-compress.js | 44 | workerSrc |
| static/js/pdf-compress.js | 59-66 | getDocument と load_failed |
| static/js/pdf-compress.js | 132, 138 | toBlob_failed と「画像変換に失敗しました」 |
| static/js/pdf-extract-images.js | 42 | workerSrc |
| static/js/pdf-extract-images.js | 56-63 | getDocument と load_failed |
| static/js/pdf-extract-images.js | 137, 144 | toBlob_failed と「画像変換に失敗しました」 |

**ライブラリバージョン根拠**
- **pdf-lib**: templates/tools/pdf.html 493行 `https://cdnjs.cloudflare.com/ajax/libs/pdf-lib/1.17.1/pdf-lib.min.js`
- **pdf.js（pdfjs-dist）**: 同 494行 `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js`。worker は pdf-render.js / pdf-compress.js / pdf-extract-images.js 内で `3.11.174/pdf.worker.min.js` を指定（同一バージョン）。

以上。
