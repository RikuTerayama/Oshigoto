# PDFユーティリティ「暗号化PDFエラー」と「画像変換に失敗しました」分析レポート

**作成日**: 2026-02-10  
**目的**: エラー1（PDFDocument.load is encrypted）とエラー2（画像変換に失敗しました）の一次原因を断定できる証拠を集め、最小修正方針まで整理する。**コード修正は行わない（レポート追加のみ）。**

---

## 1. Summary（結論、一次原因、推奨方針）

- **結論**
  - **エラー1**: 一次原因は **暗号化（パスワード保護または権限制限）されたPDF** を **pdf-lib の `PDFDocument.load(arrayBuffer)` で読み込んでいる**こと。pdf-lib は暗号化PDFをデフォルトで受け付けず、例外を投げる。呼び出し箇所は **static/js/pdf-ops.js** の **31, 83, 141, 205 行**（merge / extract / split / getPageCount）。**ignoreEncryption は現状未使用**（リポジトリ内に 0 件）。
  - **エラー2**: 「画像変換に失敗しました」は **static/js/pdf-render.js 93 行・103 行** および **pdf-compress.js 106 行**、**pdf-extract-images.js 111 行** で、**canvas.toBlob のコールバックで blob が null の場合に reject する汎用メッセージ**として使われている。PDF→画像パイプラインでは **pdfjs-dist** で getDocument → getPage → page.render → canvas.toBlob の順。暗号化PDFの場合、**pdfjs の getDocument または render が先に失敗する可能性**があり、その例外メッセージが toolRunner に渡れば「画像変換に失敗しました」ではなく元のメッセージが表示される。**toBlob が null を返す**（例: メモリ不足・セキュリティ制限・巨大 canvas）場合に、この汎用メッセージがユーザーに表示される。したがってエラー2の一次原因は **「toBlob が null を返した」または「その前に pdfjs / render で例外が発生し、メッセージが握りつぶされた」** のいずれか。**同一の暗号化PDF**で、結合モードでエラー1 → PDF→画像モードでエラー2も出る場合は、**暗号化が根因で連鎖している**と判断できる。
- **推奨方針**
  - **案1（推奨）**: 暗号化PDFを検知して明示的に拒否する。PDFDocument.load の例外メッセージに "encrypted" が含まれる場合、そのファイルをエラーとして一覧に残し、「このPDFはパスワード保護されています。保護を外したPDFを使用してください」と表示する。画像変換モードでは pdfjs の getDocument 失敗時も同様に「暗号化PDFの可能性」を判定し、同じメッセージを表示する。
  - 画像変換の例外は握りつぶさず、Console に error + コンテキスト（ファイル名・ページ番号・段階: load_failed / render_failed / toBlob_failed）を出す。ユーザー向け表示は簡潔でも、原因が追えるログを残す。

---

## 2. 症状（2エラーの発生条件、ユーザー操作）

| エラー | 文言（概要） | 想定発生条件 |
|--------|--------------|--------------|
| **エラー1** | Input document to `PDFDocument.load` is encrypted. You can use `PDFDocument.load(..., { ignoreEncryption: true })`... | 結合・抽出・分割モードで **暗号化PDF** を選択して実行したとき。getPageCount または mergePdfs / extractPdf / splitPdf 内の PDFDocument.load が実行され、pdf-lib が例外を投げる。 |
| **エラー2** | 画像変換に失敗しました | PDF→画像モード（または圧縮・埋め込み画像抽出）で、**PDF を画像に変換する過程**で失敗したとき。canvas.toBlob が null を返した場合、または pdfjs の getDocument / getPage / page.render で例外が出たがメッセージが汎用化されている場合。 |

**ユーザー操作の例**
- パスワード付きPDFをアップロード → 結合または抽出・分割で「実行」→ エラー1 が表示される。
- 同じパスワード付きPDFで「PDF→画像」を実行 → エラー2 が表示される、または pdfjs 由来の別メッセージが表示される（要観測）。
- 暗号化していない通常のPDFで「PDF→画像」→ 成功する場合、エラー2 は暗号化以外の要因（toBlob 失敗・worker 失敗等）で発生している可能性がある。

---

## 3. 再現手順（通常PDF vs 暗号化PDFで比較）

### 環境
- ブラウザ: 要記載（Chrome / Edge / Firefox 等）
- アプリ: `/tools/pdf`（templates/tools/pdf.html）

### パターンA: 通常PDF（暗号化なし）
1. 操作モードを「PDF→画像」にする。
2. 暗号化されていない通常のPDFを1つ選択し、実行する。
3. **期待**: 画像が出力され、ダウンロードできる。
4. **結果**: （要記載）成功するなら、エラー2の再現は暗号化PDFまたは別要因に依存する。

### パターンB: 暗号化PDF（パスワード付きまたは権限制限）
1. パスワードで保護したPDF、または権限制限付きPDFを用意する。
2. **エラー1の確認**: 操作モードを「結合」または「抽出」にする。当該PDFを1つだけ追加し、実行する。
   - **期待**: エラー表示。「Input document to PDFDocument.load is encrypted...」に類するメッセージが出る。
3. **エラー2の確認**: 同じPDFのまま操作モードを「PDF→画像」に切り替え、実行する。
   - **期待**: エラー表示。メッセージが「画像変換に失敗しました」か、pdfjs 由来の別メッセージかを記録する。
4. **連鎖の確認**: 上記でエラー1が出た同じファイルでエラー2も出れば、**同一原因（暗号化PDF）で連鎖**していると判断できる。

### パターンC（任意）: 破損PDF・巨大PDF
- 破損したPDFや極端にページ数が多いPDFで「PDF→画像」を実行し、エラー2が出るか・Console にどの段階の失敗が出るかを記録する。

---

## 4. コード根拠（PDFDocument.load 箇所、画像変換箇所、メッセージ表示箇所の行番号）

### 4-0. 実行フロー（mode 別・関数チェーン）

- **共通**: handleFiles → toolRunner.addFiles → updateFileList。ユーザーが「実行」→ runOperation()（pdf.html 771 行）→ mode に応じて以下。
- **merge**: runOperation → toolRunner.runBatch(batchProcessor) → batchProcessor = async (files, ctx) => PdfOps.mergePdfs(files, ctx) → 各 file で arrayBuffer → **PDFDocument.load(arrayBuffer)**（pdf-ops.js 31）→ copyPages / addPage → save → blob。
- **extract**: runOperation → **PdfOps.getPageCount(files[0])**（pdf-ops.js 205: **PDFDocument.load**）→ バリデーション → toolRunner.runBatch(...) → PdfOps.extractPdf(files[0], pages, ctx) → **PDFDocument.load(arrayBuffer)**（83 行）→ copyPages → save。
- **split**: runOperation → **PdfOps.getPageCount(files[0])**（205 行: **PDFDocument.load**）→ バリデーション → toolRunner.runBatch(...) → PdfOps.splitPdf(...) → **PDFDocument.load(arrayBuffer)**（141 行）→ グループごとに copyPages → save。
- **to-images（PDF→画像）**: runOperation → toolRunner.run(processor) → processFiles(processor) → 各 file で processFile(file, index, processor) → **processor = async (file, ctx) => PdfRender.pdfToImages(file, options, ctx)**（pdf.html 824-830）→ pdf-render.js: **pdfjs.getDocument({ data: arrayBuffer })** → getPage → page.render → **canvas.toBlob**（93/103 行で「画像変換に失敗しました」の reject）。
- **compress**: runBatch → PdfCompress.compressPdfByRasterize → **pdfjs.getDocument** → 各ページ render → **canvas.toBlob**（106 行）→ pdf-lib で再構成。
- **extract-images**: toolRunner.run → PdfExtractImages.extractEmbeddedImages → **pdfjs.getDocument** → getPage → render → **canvas.toBlob**（111 行）。

※ エラー1は **pdf-ops.js の PDFDocument.load**（31/83/141/205）のいずれかで発生。エラー2は **pdf-render.js / pdf-compress.js / pdf-extract-images.js** の toBlob またはその前段（getDocument / render）で発生。

### 4-1. PDFDocument.load の呼び出し（pdf-lib・暗号化で例外）

| ファイル | 行番号 | 関数・モード | 内容 |
|----------|--------|--------------|------|
| static/js/pdf-ops.js | 31 | PdfOps.mergePdfs | `const pdf = await PDFDocument.load(arrayBuffer);`（結合） |
| static/js/pdf-ops.js | 83 | PdfOps.extractPdf | `const pdf = await PDFDocument.load(arrayBuffer);`（抽出） |
| static/js/pdf-ops.js | 141 | PdfOps.splitPdf | `const pdf = await PDFDocument.load(arrayBuffer);`（分割） |
| static/js/pdf-ops.js | 205 | PdfOps.getPageCount | `const pdf = await PDFDocument.load(arrayBuffer);`（ページ数取得） |

- **ignoreEncryption**: リポジトリ内に **0 件**。すべての load はオプションなし。

### 4-2. 画像変換パイプラインと「画像変換に失敗しました」の表示箇所

| ファイル | 行番号 | 内容 |
|----------|--------|------|
| static/js/pdf-render.js | 43-45 | pdfjs.getDocument({ data: arrayBuffer }) → promise。**PDF→画像**モードで使用。 |
| static/js/pdf-render.js | 65-80 | getPage → viewport → canvas → page.render(renderContext).promise |
| static/js/pdf-render.js | 90-105 | canvas.toBlob のコールバックで **b ? resolve(b) : reject(new Error('画像変換に失敗しました'))**（93 行: JPEG / 103 行: PNG） |
| static/js/pdf-compress.js | 48-50 | pdfjs.getDocument。圧縮モード（レンダリング→画像→再PDF化） |
| static/js/pdf-compress.js | 104-108 | canvas.toBlob で **blob ? resolve(blob) : reject(new Error('画像変換に失敗しました'))**（106 行） |
| static/js/pdf-extract-images.js | 45-46, 106-111 | pdfjs.getDocument。埋め込み画像抽出で page.render 後に toBlob、同メッセージで reject（111 行） |

- PDF→画像モードで実際に呼ばれるのは **PdfRender.pdfToImages**（templates/tools/pdf.html 824-830 行）。**pdf-lib の PDFDocument.load は使っていない**。pdfjs-dist で読み込み、canvas でレンダリングし、toBlob で画像化している。

### 4-3. 例外の伝播とUI表示

| ファイル | 行番号 | 内容 |
|----------|--------|------|
| templates/tools/pdf.html | 771-873 | runOperation()。mode に応じて toolRunner.runBatch / toolRunner.run を呼ぶ。**extract / split では先に PdfOps.getPageCount(files[0]) を await**（789, 808 行）。getPageCount 内の PDFDocument.load が throw すると、runOperation の catch へ。 |
| templates/tools/pdf.html | 869-872 | catch (error) { handleError(error); } → **エラー1はここで handleError に渡り、全文が表示される**。 |
| templates/tools/pdf.html | 989-992 | handleError(error): error-section を表示し、**error-message に「エラー: ${error.message}」** を設定。 |
| static/js/tool-runner.js | 174-185 | processFile が reject すると、**message: error.message** で this.errors に追加。onComplete で handleComplete → showErrors(errors)。 |
| templates/tools/pdf.html | 974-983 | showErrors(errors): 各 errors の **sourceIndex と message** を一覧表示。**エラー2はここで「ファイル名: 画像変換に失敗しました」** として表示される。 |

- **結合モード**で mergePdfs が throw すると runBatch の try から throw し、runOperation の catch → handleError で **エラー1の全文** が表示される。
- **抽出・分割モード**では getPageCount が先に実行され、ここで PDFDocument.load が throw すると **runOperation の catch → handleError** でエラー1が表示される。
- **PDF→画像モード**では run(processor) が processFiles を呼び、各ファイルは processFile で処理される。PdfRender.pdfToImages が throw すると error.message がそのまま this.errors に入り、**showErrors で「画像変換に失敗しました」** などが表示される。**元の例外がどこで握りつぶされたか**は、Console のスタックで確認する必要がある。

---

## 5. 観測ログ（Console/Network。スタックとステータス）

※ 以下は **手動で採取してレポートに貼り付ける** 想定。ここでは観測すべき項目のみ記載する。

### 5-1. エラー1（PDFDocument.load is encrypted）
- **Console**
  - エラー1が表示されたときの **スタックトレース全文** を採取する。
  - どの関数から PDFDocument.load が呼ばれたか（PdfOps.mergePdfs / extractPdf / splitPdf / getPageCount のいずれか）を確認する。
- **想定スタック例（要実機で確認）**
  - `PDFDocument.load` → `PdfOps.getPageCount` または `mergePdfs` / `extractPdf` / `splitPdf` → `runOperation`（pdf.html）→ ...

### 5-2. エラー2（画像変換に失敗しました）
- **Console**
  - エラー2が表示される **直前に出ているエラー** のスタックを採取する。
  - 握りつぶされている場合、**throw 元**（pdfjs の getDocument / getPage / page.render、または canvas.toBlob）を特定する。
- **確認項目**
  - PdfRender.pdfToImages 内のどの行で例外が発生しているか（getDocument / getPage / render / toBlob）。
  - 同じ操作でエラー1とエラー2が両方出るか（同一ファイル・別モードで比較）。

### 5-3. Network
- **PDF→画像モード**
  - pdfjs の worker: `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js` が 200 で読まれているか。404 や CORS エラーがないか。
- 画像変換がサーバAPIを叩く実装は **ない**（すべてクライアント側の pdf-render.js / pdf-compress.js 等）。サーバエンドポイントの 500 は対象外。

### 5-4. エラー1とエラー2が「同じPDFで連鎖する」かの検証
- **手順**: 暗号化PDFを1つ用意する。
  1. 結合（または抽出）で実行 → エラー1の有無とメッセージを記録。
  2. 同じファイルのまま「PDF→画像」で実行 → エラー2の有無とメッセージ、Console の先頭エラーを記録。
- **解釈**: 両方出る場合、**暗号化PDFが共通原因**。エラー1は pdf-lib、エラー2は pdfjs または toBlob のいずれかで失敗していると判断する。

---

## 6. 原因候補ランキング（肯定・否定条件）

| 候補 | 内容 | 肯定条件 | 否定条件 |
|------|------|----------|----------|
| **A** | 暗号化PDFを pdf-lib の PDFDocument.load で読み込んでいる | エラー1の文言が pdf-lib の encrypted メッセージと一致する。pdf-ops.js の 31/83/141/205 行のいずれかがスタックに含まれる。 | スタックに PDFDocument.load が出ず、別ライブラリ由来のエラーの場合。 |
| **B** | エラー1とエラー2は同一の暗号化PDFで連鎖している | 同じ暗号化PDFで結合でエラー1、PDF→画像でエラー2（または pdfjs 由来メッセージ）が出る。 | 通常PDFでエラー2だけ出る場合は、暗号化以外の要因。 |
| **C** | 画像変換失敗は canvas.toBlob が null を返した | エラー2の直前に toBlob 周りのスタックがある。または「画像変換に失敗しました」が pdf-render.js 93/103 行の reject から来ている。 | エラー2の前に getDocument や getPage の失敗スタックがある場合は、toBlob より前で失敗。 |
| **D** | 画像変換失敗は pdfjs の getDocument / render で発生した | Console に pdfjs や getDocument / getPage / render のスタックが出ている。メッセージが「画像変換に失敗しました」に正規化される前に、別の例外メッセージがログに出ている可能性。 | スタックが toBlob のみで、getDocument が成功している場合。 |
| **E** | worker や wasm の読み込み失敗で画像変換ができない | Network で pdf.worker.min.js が 404 や CORS で失敗している。 | worker が 200 で読まれている場合は別原因。 |

---

## 7. 最小修正方針（案1/案2、画像変換のログ改善）

### 案1: 暗号化PDFを検知して明示的に拒否（推奨）
- **どこを変えるか**
  - **static/js/pdf-ops.js**: PDFDocument.load を try-catch で囲み、例外メッセージに `"encrypted"` または `"Encrypted"` が含まれる場合、**ユーザー向けメッセージ**「このPDFはパスワード保護されています。保護を外したPDFを使用してください」に差し替えて throw する（または throw new Error(ユーザー向けメッセージ)）。対象は mergePdfs（31 行付近）、extractPdf（83 行付近）、splitPdf（141 行付近）、getPageCount（205 行付近）の各 load 呼び出し。
  - **templates/tools/pdf.html**: 変更不要。既に handleError(error) と showErrors で error.message を表示しているため、pdf-ops 側でメッセージを差し替えればそのまま表示される。
  - **画像変換モード**: **static/js/pdf-render.js** の getDocument を try-catch で囲み、pdfjs のエラーメッセージに「password」「encrypted」等が含まれる場合は、上記と同じユーザー向けメッセージに置き換えて throw する。同様の判定を **pdf-compress.js**・**pdf-extract-images.js** の getDocument 周りにも入れると一貫する。
- **メリット**: ユーザーが原因を理解しやすい。暗号化PDFを「未対応」と明示できる。
- **デメリット**: 文言の一致判定に依存するため、pdf-lib / pdfjs の英語メッセージが変わると要調整。

### 案2: ignoreEncryption を使って強行ロード（注意して採用）
- **どこを変えるか**
  - **static/js/pdf-ops.js**: `PDFDocument.load(arrayBuffer, { ignoreEncryption: true })` に変更する。31, 83, 141, 205 行の load 呼び出しに第2引数を追加。
- **注意点**
  - 暗号が解けない場合は中身が読めず、結合・抽出・分割の結果が不正になる可能性がある。パスワードなしの権限制限のみのPDFでは動く場合があるが、**成功率や副作用は実機調査が必要**。
  - ユーザーに「保護付きPDFは正しく処理されない場合があります」などのリスク表示を検討する。
- **推奨**: まずは **案1** で明示拒否を入れ、必要に応じて案2は別PRで検討する。

### 画像変換失敗のログ改善（暗号化以外の原因も含む）
- **どこを変えるか**
  - **static/js/pdf-render.js**: pdfToImages 内で、
    - getDocument 失敗時: `console.error('[PdfRender] load_failed', file.name, e)` および throw 前に context をログ。
    - getPage / page.render 失敗時: `console.error('[PdfRender] render_failed', file.name, pageNum, e)`。
    - toBlob の reject 時: `console.error('[PdfRender] toBlob_failed', file.name, pageNum, format, e)`。reject するメッセージは「画像変換に失敗しました」のままでもよいが、**Console には上記を出す**。
  - **static/js/pdf-compress.js**・**static/js/pdf-extract-images.js**: 同様に、load_failed / render_failed / toBlob_failed の区別で console.error を入れる。
- **ユーザー表示**: 現状の「画像変換に失敗しました」や、showErrors の一覧表示は簡潔なままでよい。**原因追跡は Console ログで行う**。

---

## 8. 受け入れ条件（暗号化PDFは明示エラー、通常PDFは変換成功、原因が追えるログ）

- 暗号化（パスワード保護）PDFを扱った場合、**「このPDFはパスワード保護されています。保護を外したPDFを使用してください」**（または同等の明示メッセージ）が表示され、処理が行われないこと。
- 暗号化されていない通常のPDFでは、結合・抽出・分割・PDF→画像が **期待どおり成功**すること。
- 画像変換で失敗した場合、**Console にどの段階で失敗したか**（load_failed / render_failed / toBlob_failed 等）が分かるログが出力されること。
- エラー1とエラー2が同一の暗号化PDFで連鎖して出る場合、**両方とも上記の明示メッセージ（または原因が分かる表示）に寄せられる**ことが望ましい。

---

## 参照（ファイル・行番号一覧）

| ファイル | 行番号 | 内容 |
|----------|--------|------|
| static/js/pdf-ops.js | 31, 83, 141, 205 | PDFDocument.load（merge / extract / split / getPageCount） |
| static/js/pdf-render.js | 43-45, 65-80, 93, 103 | getDocument, render, toBlob と「画像変換に失敗しました」 |
| static/js/pdf-compress.js | 48-50, 106 | getDocument, toBlob と「画像変換に失敗しました」 |
| static/js/pdf-extract-images.js | 45-46, 111 | getDocument, toBlob と「画像変換に失敗しました」 |
| templates/tools/pdf.html | 771-873, 824-830, 869-872, 974-983, 989-992 | runOperation, PDF→画像の processor, catch, showErrors, handleError |
| static/js/tool-runner.js | 174-185 | processFile の catch で error.message を errors に追加 |
