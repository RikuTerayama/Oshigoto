# PDFユーティリティ「操作モード変更でファイルが消える／アップロードできなくなる」分析レポート

**作成日**: 2026-02-10  
**目的**: 原因を断定できる証拠を集め、一次原因まで整理する。**実装は行わない（レポート追加のみ）。**

---

## 1. Summary（結論と一次原因）

- **結論**
  - **事象1（選択済みファイルが消える）**: 一次原因は **モード変更時に `updateModeOptions()` 内で意図的に `toolRunner.clearFiles()` を呼んでいる** ことである。根拠: **templates/tools/pdf.html** の **337 行**で `<select id="mode" onchange="updateModeOptions()">` によりモード変更で `updateModeOptions()` が実行され、同ファイル **728-731 行**で「ファイルリストをクリア」とコメントしたうえで `toolRunner.clearFiles()` → `updateFileList()` → `updateRunButton()` が並んでいる（**templates/tools/pdf.html:728-731**）。`clearFiles()` は **static/js/tool-runner.js:53-59** で `selectedFiles = []` と `tasksState.clear()` を行い、**templates/tools/pdf.html:640** の `updateFileList()` が `fileList.innerHTML = ''` のうえ `toolRunner.selectedFiles` から再描画するため、結果として選択済みファイルが画面から消える。
  - **事象2（モード変更後にアップロードできなくなることがある）**: コード上、dropzone と file-input の DOM は **差し替え・削除・無効化されておらず**、イベントも **DOMContentLoaded で一度だけ** `setupDropzone()` により登録されている（**templates/tools/pdf.html:569-593**）。したがって「常にアップロードできなくなる」ような実装は見当たらない。**推測**: モード変更後に `clearFiles()` で `toolRunner.selectedFiles` は空になるが、**ネイティブの `<input type="file">` の `value`（および `files`）はリセットしていない**（**pdf.html 内に fileInput.value = '' の記述はない**）。一部ブラウザでは、同じファイルを再度選択した場合に `change` が発火しないことがある。その場合「再追加できない」ように見える可能性がある。断定するにはブラウザでの再現と Console/Network の確認が必要である。
- **一次原因の整理**
  - 事象1: **updateModeOptions() 内の toolRunner.clearFiles() 呼び出し**（設計上の「モード変更でクリア」がそのままユーザー報告の「ファイルが消える」に相当）。
  - 事象2: コード上は **イベント剥がれや DOM 差し替えはない**。**input の value をリセットしていない**ことによる「同一ファイル再選択で change が発火しない」可能性を、要手動確認として記載する。

---

## 2. 症状と期待動作

| 項目 | 内容 |
|------|------|
| **報告1** | 操作設定の操作モードを変更すると、選択済みのファイルが消える。 |
| **期待1** | 選択ファイルは維持される（ユーザーが明示的にクリアしない限り）。 |
| **報告2** | モードを変更したあとに、ファイルがアップロードできなくなることがある。 |
| **期待2** | いつでもファイル追加（選択・ドラッグ＆ドロップ・再追加）ができる。 |

---

## 3. 再現手順（確実に再現できるステップ）

1. ブラウザで `/tools/pdf` を開く（**app.py:984-989** でルート定義、**templates/tools/pdf.html** を表示）。
2. 操作モードは初期の「結合」のままで、PDF を 1 つ以上ドロップまたはファイル選択で追加する。
3. 操作設定の「操作モード」の `<select id="mode">`（**337 行**）で別のモード（例: 抽出・分割・PDF→画像）に変更する。
4. **結果**: ファイル一覧（**#file-list**）が空になり、選択済みファイルが消える（**事象1**）。  
   ※ 事象2 は「モード変更後、再度ファイルを追加しようとしても追加できない／change が発火しない」など。環境依存のため、手動観測チェックリストで確認する。

---

## 4. コード根拠（定義/参照/読み込み/イベント/状態管理：ファイルパス＋行番号）

### 4-1. ルートとテンプレート

| ファイル | 行番号 | 内容 |
|----------|--------|------|
| app.py | 984-989 | `@app.route('/tools/pdf')`、`render_template('tools/pdf.html', product=product)` |

### 4-2. 操作モードの DOM とモード変更時の呼び出し

| ファイル | 行番号 | 内容 |
|----------|--------|------|
| templates/tools/pdf.html | 333-349 | 「操作設定」セクション。**337**: `<select id="mode" onchange="updateModeOptions()">`。モード変更で **updateModeOptions()** が呼ばれる。 |
| templates/tools/pdf.html | 678-731 | **updateModeOptions()** の定義。679 で `mode = document.getElementById('mode').value`。682-706 でオプション表示の切替。709-725 で **file-input** の `accept` / `multiple` と **dropzone-hint** の文言を更新。**728-731**: 「ファイルリストをクリア」として **toolRunner.clearFiles()**、**updateFileList()**、**updateRunButton()** を実行。 |

### 4-3. ファイル入力と dropzone の DOM

| ファイル | 行番号 | 内容 |
|----------|--------|------|
| templates/tools/pdf.html | 316-327 | **dropzone**（id="dropzone"）、その中に **file-input**（id="file-input", type="file", accept="application/pdf", multiple）。 |
| templates/tools/pdf.html | 329 | **file-list**（id="file-list"）。updateFileList() でここを書き換える。 |

### 4-4. イベント登録（setupDropzone）とファイル処理

| ファイル | 行番号 | 内容 |
|----------|--------|------|
| templates/tools/pdf.html | 520-531 | DOMContentLoaded で toolRunner 生成、**setupDropzone()**、**updateModeOptions()** を実行。 |
| templates/tools/pdf.html | 567-594 | **setupDropzone()**: dropzone の click → fileInput.click()、dragover/dragleave/drop、**fileInput の change** → handleFiles(Array.from(e.target.files))。**イベントは初回のみ登録**。updateModeOptions() では dropzone/file-input を差し替えず、**イベントの再登録は行っていない**。 |
| templates/tools/pdf.html | 597-634 | **handleFiles(files)**: mode に応じて rules を決め、FileValidation.validateFiles 後、okFiles を **toolRunner.addFiles(okFiles)** し、updateFileList()、updateRunButton() を呼ぶ。 |
| templates/tools/pdf.html | 636-654 | **updateFileList()**: fileList = getElementById('file-list')、**fileList.innerHTML = ''**（640）、toolRunner.selectedFiles を forEach して file-item を append。 |
| templates/tools/pdf.html | 658-660 | **removeFile(index)**: toolRunner.removeFile(index)、updateFileList()、updateRunButton()。 |

### 4-5. 状態管理（ToolRunner）

| ファイル | 行番号 | 内容 |
|----------|--------|------|
| static/js/tool-runner.js | 9, 24-36, 53-59 | **selectedFiles** 配列。**addFiles(files)** で push。**clearFiles()** で **selectedFiles = []**、tasksState.clear()、outputs/errors クリア、onProgress 呼び出し。 |
| templates/tools/pdf.html | 729 | updateModeOptions() 内で **toolRunner.clearFiles()** を呼んでいる。 |

### 4-6. input[type=file] の value リセットの有無

- **templates/tools/pdf.html** 内で **fileInput.value = ''** や **input.value = ''** の記述は **存在しない**（grep で確認済み）。モード変更後もネイティブ input の選択状態（files）はそのまま残る。

---

## 5. 原因候補ランキング（当てはまり条件を明確に）

| 候補 | 内容 | 当てはまり | 根拠 |
|------|------|------------|------|
| **A** | モード変更時に **意図的に** toolRunner.clearFiles() を呼んでいる | **◎ 事象1に当てはまる** | **pdf.html:728-731** に「ファイルリストをクリア」とコメント付きで clearFiles() がある。 |
| **B** | モード変更で **DOM が差し替え**られ、dropzone や file-input が別要素になっている | **× 当てはまらない** | updateModeOptions() は option の表示非表示と fileInput の **setAttribute** のみ。dropzone/file-input の親要素の innerHTML や差し替えは行っていない（**pdf.html:678-731**）。 |
| **C** | モード変更で **イベントリスナーが外れている**（要素の差し替えや再生成で登録が消える） | **× 当てはまらない** | dropzone と file-input は同一要素のまま。setupDropzone() は DOMContentLoaded で 1 回だけ呼ばれ、**updateModeOptions() 内で dropzone/file-input を再取得してリスナーを付け直す処理はない**（**pdf.html:569-593, 678-731**）。 |
| **D** | **input の value（files）をリセットしていない**ため、同一ファイル再選択で change が発火しないことがある | **△ 事象2の可能性**（要ブラウザ確認） | pdf.html に fileInput.value = '' はない。一部ブラウザでは、同じファイルを再度選んでも change が発火しない場合がある。 |
| **E** | **form.reset** や **別の箇所での clearFiles** がモード変更以外で呼ばれている | **× 事象1の主因ではない** | clearFiles() が呼ばれているのは **pdf.html:729** の updateModeOptions() 内のみ（grep で確認）。form は使っていない。 |

---

## 6. 手動観測チェックリスト（Network/Console/Elements）

### 6-1. 再現の確実化

- [ ] 1 回だけモードを切り替える（例: 結合 → 抽出）。ファイルが消えるか。
- [ ] 2 回以上切り替える（結合 → 抽出 → 結合）。その都度ファイルが消えるか。
- [ ] ファイルを追加 → モード変更（ファイルが消える）→ 再度「ファイル選択」またはドラッグ＆ドロップで追加。追加できるか／できないか。
- [ ] 上記で「追加できない」場合: 別ファイルを選ぶと追加できるか、同じファイルを選ぶと追加できないか。
- [ ] PDF モードで複数 PDF を追加 → モードを「画像→PDF」に変更 → 画像を追加しようとする。追加できるか。

### 6-2. Network

- [ ] /tools/pdf 表示時に、**tool-runner.js** や **file-validation.js** が 200 で読まれているか。
- [ ] モード変更時に **XHR/Fetch は発生していない**想定（クライアントのみの動作）。不審な 4xx/5xx や Failed がないか。

### 6-3. Console

- [ ] モード変更時に **エラー**（Uncaught TypeError、ReferenceError 等）が出ていないか。特に **updateModeOptions** 実行前後のスタック。
- [ ] ファイル追加が「できなくなった」状態で、dropzone をクリックしてファイルを選んだときに **change が発火しているか**（handleFiles 内に console.log を一時的に仕込むか、Breakpoint で fileInput の change を確認）。

### 6-4. Elements

- [ ] モード変更の前後で **#file-input** が同じ 1 要素のままか（削除・複製されていないか）。
- [ ] **#dropzone** も同様に同一要素のままか。
- [ ] **#file-input** に **disabled** が付与されていないか。
- [ ] **#file-input** の **accept** がモードに応じて切り替わっているか（PDF 用 / 画像用）。

---

## 7. 最小修正方針（複数案、実装なし）

| 方針 | 内容 | メリット | デメリット |
|------|------|----------|------------|
| **案1: モード変更で clearFiles() を呼ばない** | updateModeOptions() の **729 行**の `toolRunner.clearFiles()` を削除（または条件付きでスキップ）。選択済みファイルを維持する。 | 事象1が解消する。変更箇所が 1 か所で済む。 | モードによっては「PDF のみ」「画像のみ」など形式が変わる。既に選択しているファイルが新しいモードと合わない場合の扱い（警告表示・無効化・自動クリアの選択）を決める必要がある。 |
| **案2: モード変更で「新モードに合わないファイルだけ外す」** | clearFiles() の代わりに、現在の mode の rules（allowedExtensions 等）に合致するファイルだけ残し、それ以外を removeFile で削除する。合致するファイルが 0 件の場合は clearFiles() と同等にするか、警告を出してユーザーにクリアさせる。 | モードと形式の整合性を保ちつつ、残せるファイルは残せる。 | ロジックが増える。validateFiles と同等の判定を selectedFiles に対して行う必要がある。 |
| **案3: モード変更時に input.value をリセットする（現状の clearFiles は維持）** | updateModeOptions() 内で clearFiles() のあと、**fileInput.value = ''** を実行する。 | 事象2の「同じファイルを再選択すると change が発火しない」を避けやすくなる。 | 事象1（ファイルが消える）はそのまま。ユーザー期待「選択維持」には沿わない。 |
| **案4: DOM を触らず表示だけ切替＋状態は in-memory で保持** | モード変更では **clearFiles() を呼ばない**。表示は updateFileList() のままで、toolRunner.selectedFiles を維持。accept だけ fileInput で更新する。新規追加時（handleFiles）では、現在の mode の rules でバリデーションする（既存のまま）。 | 事象1・2 の両方を解消する方向にできる。 | モードを「画像→PDF」から「結合」に切り替えた場合、selectedFiles に画像が残る。実行時にバリデーションで弾くか、モード切替時に「形式が合わないファイルは一覧から外す（選択は維持だが警告を出す）」などの仕様が必要。 |
| **案5: イベント再バインドの統一** | 現状は差し替えがないため必須ではない。将来、オプション領域を innerHTML で差し替える実装にする場合は、**setupDropzone() を updateModeOptions() の末尾で再実行**するか、file-input だけは必ず「外側のコンテナ」に残し、差し替えないようにする。 | 将来の DOM 変更でもイベントが外れにくくなる。 | 今回の不具合の直接原因ではない。 |

**推奨の方向性**: 受け入れ条件「モードを切り替えても選択済みファイルが消えない」「常にファイル追加ができる」を満たすには、**案1 または 案4** を採用し、**モード変更時に clearFiles() を呼ばない**ようにする。そのうえで、モードとファイル形式の不一致（例: 画像→PDF モードで PDF が残っている）は、**実行時バリデーション**や**一覧表示上の注意**で対応する設計が最小変更で済む。

---

## 8. テスト観点と受け入れ条件

### 8-1. 受け入れ条件（必須）

- モードを何回切り替えても、**選択済みファイルが消えない**（ユーザーが明示的にクリアしない限り維持）。
- モード切替後も、**常にファイル追加ができる**（ファイル選択・ドラッグ＆ドロップの両方）。
- コンソールエラーが出ない。
- 複数ファイル、異なる PDF、連続操作でも壊れない。

### 8-2. テスト観点

- 複数 PDF 追加 → モードを 2 回以上切り替え → 一覧が維持されているか。
- モード切替後、ドラッグ＆ドロップで追加 → 一覧に追加されるか。
- モード切替後、クリックでファイル選択 → 一覧に追加されるか。
- 同一ファイルを一度削除して再度追加 → 追加できるか。
- モードを「画像→PDF」にしたあと画像を追加 → さらにモードを「結合」に戻し、PDF を追加 → 両方の形式が一覧に存在してよいか／実行時のみバリで弾くかは仕様次第。

---

## 9. 参照（ファイル・行番号一覧）

| ファイル | 行番号 | 内容 |
|----------|--------|------|
| app.py | 984-989 | /tools/pdf ルート、pdf.html レンダリング |
| templates/tools/pdf.html | 316-327 | dropzone、file-input（id="file-input"） |
| templates/tools/pdf.html | 329 | file-list |
| templates/tools/pdf.html | 333-349 | 操作モード select、onchange="updateModeOptions()" |
| templates/tools/pdf.html | 516-531 | toolRunner、DOMContentLoaded、setupDropzone()、updateModeOptions() |
| templates/tools/pdf.html | 567-594 | setupDropzone()、dropzone/fileInput のイベント登録 |
| templates/tools/pdf.html | 597-634 | handleFiles、addFiles、updateFileList、updateRunButton |
| templates/tools/pdf.html | 636-654 | updateFileList、fileList.innerHTML = ''、selectedFiles から再描画 |
| templates/tools/pdf.html | 678-731 | updateModeOptions()、clearFiles() 呼び出し（728-731） |
| static/js/tool-runner.js | 9, 24-36, 53-59 | selectedFiles、addFiles、clearFiles |

---

以上。
