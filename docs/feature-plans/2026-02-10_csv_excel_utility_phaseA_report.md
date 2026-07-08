# CSV/Excelユーティリティ 新ツール 実装計画レポート（Phase A）

**日付**: 2026-02-10  
**前提**: minutes 削除後の現状。本フェーズではコード改修は行わず、レポート作成のみ。

---

## 1. 概要

| 項目 | 内容 |
|------|------|
| 新ツール名（仮） | CSV/Excelユーティリティ |
| 想定URL | `/tools/csv`（ツール本体）、`/guide/csv`（ガイド） |
| MVP機能候補 | ①CSV文字コード変換（Shift-JIS/UTF-8） ②CSV⇄XLSX変換 ③重複削除（キー列指定） ④列の抽出/並べ替え/ヘッダ名置換 ⑤分割（N行ごと、列値ごと） |

---

## 2. 既存ツールの追加パターン調査

### 2.1 lib/products_catalog.py の構造

**事実（ファイル:行番号）**

- **場所**: `lib/products_catalog.py` 先頭～187行。`PRODUCTS` はリストで、各要素は辞書。
- **必須キー**: `id`, `name`, `description`, `path`, `guide_path`, `status`, `icon`。  
  - 例: `path: '/tools/pdf'`, `guide_path: '/guide/pdf'`（8–15行付近、61–66行付近）。
- **任意キー**: `category`, `tags`, `features`, `capabilities`, `recommended_for`, `usage_steps`, `constraints`, `faq`。  
  - `constraints` は配列（例: 49–52行、93–97行）。`faq` は `[{"q":"...", "a":"..."}]`（54–57行、99–101行）。
- **status**: `'available'` のものだけがナビ・sitemap に含まれる（app.py 2099–2118、lib/nav.py 18行付近）。

**結論**: 新ツール用に `id: 'csv'`, `path: '/tools/csv'`, `guide_path: '/guide/csv'`, `status: 'available'` のエントリを 1 件追加する形で整合する。

---

### 2.2 app.py の /tools/* と /guide/* ルーティング

**事実（ファイル:行番号）**

- **ツール**: `@app.route('/tools/xxx')` → 関数内で `get_product_by_path('/tools/xxx')`、`render_template('tools/xxx.html', product=product)`。  
  - 例: `/tools/pdf` 1017–1023行、`/tools/image-batch` 1011–1016行、`/tools/seo` 1151–1156行。
- **ガイド**: `@app.route('/guide/xxx')` → `return render_template('guide/xxx.html')` のみ（product は渡していない）。  
  - 例: `/guide/pdf` 991–994行、`/guide/seo` 1006–1009行。

**結論**: 追加するのは次の 2 本。  
- `@app.route('/tools/csv')` → `get_product_by_path('/tools/csv')` で product 取得し `render_template('tools/csv.html', product=product)`。  
- `@app.route('/guide/csv')` → `render_template('guide/csv.html')`。

---

### 2.3 templates/tools/* と templates/guide/* の共通レイアウト

**事実（ファイル:行番号）**

- **ツールページ**:  
  - `page_title`, `page_description`, `breadcrumb_title` を `{% set %}`（例: pdf.html 4–6行）。  
  - `{% include 'includes/head_meta.html' %}`, `{% block description_meta %}`, `{% block og_description %}`。  
  - product がある場合は `includes/structured_data.html` と SoftwareApplication 用 `extra_structured_data`（pdf.html 11–36行）。  
  - `{% include 'includes/header.html' %}`, `{% include 'includes/breadcrumb.html' %}`。  
  - ページヘッダー直下で `{% include 'includes/tool_guide_link.html' %}`（pdf.html 309行）。  
  - ファイル選択は `#dropzone` / `#file-input`、`#file-list`、`#rejected-files` の構成（pdf.html 313–329行）。  
  - 操作設定は `.tool-section` 内の select/option やボタン（pdf.html 332行以降）。
- **ガイドページ**:  
  - `page_title`, `description_meta` を set。  
  - `guide/pdf.html` と同様に、h1・「できること」・「このツールで解決できる課題」・「使い方の流れ」・入出力仕様・データの取り扱い・FAQ・関連リンク・nav-links。  
  - 末尾で `{% set tool_path = '/tools/xxx' %}`, `{% set tool_name = '...' %}` のうえで `guide/_partials/guide_related_links.html` を include（pdf.html 189–194行）。  
  - FAQ は `{% set faq_list = [...] %}` で定義し、`guide/_partials/guide_faq_jsonld.html` を include（pdf.html 153–169行、_partials 1–23行）。  
  - nav-links で「← ツールに戻る」「← ツール一覧へ」「次のガイド: ○○ →」（pdf.html 196–201行）。

**結論**: 新ツールは `templates/tools/csv.html` を pdf/image-batch の流れに合わせ、ガイドは `templates/guide/csv.html` を guide/pdf.html の構成に合わせて作成する。

---

### 2.4 tool-runner.js / file-utils.js / zip-utils.js の再利用

**事実（ファイル:行番号）**

- **file-validation.js**:  
  - `FileValidation.validateFiles(files, rules)`。`rules`: `maxFiles`, `maxFileSize`, `maxTotalSize`, `allowedExtensions`, `allowedMimeTypes`（16–24行）。  
  - デフォルト: maxFiles 50、maxFileSize 20MB、maxTotalSize 200MB（19–21行）。  
  - `FileValidation.sanitizeFilename(filename)`（105–112行）。
- **file-utils.js**:  
  - `FileUtils.downloadBlob(blob, filename)`（10–19行）、`formatBytes`, `getExtension`, `getFilenameWithoutExtension`。
- **zip-utils.js**:  
  - `ZipUtils.createZip(outputs, zipName)`。`outputs`: `[{blob, filename}, ...]`。内部でグローバル `JSZip` を利用（6–31行）。
- **tool-runner.js**:  
  - `ToolRunner`: `addFiles`, `removeFile`, `clearFiles`, `resetRunState`。`selectedFiles`, `outputs`, `onProgress`, `onComplete`, `onError`（6–76行）。  
  - 複数ファイルのキュー・進捗・キャンセル・出力集約用。

**参照箇所**:  
- pdf.html 528–531行: file-validation, file-utils, zip-utils, tool-runner を読み込み。  
- image-batch.html 511–517行、image-cleanup.html 522–525行: 同様。

**結論**:  
- CSV/Excel ツールでも **file-validation.js** で `.csv`, `.xlsx`（必要なら `.xls`）の拡張子・MIME・最大ファイル数/サイズ/合計を統一できる。  
- **file-utils.js** で Blob ダウンロード・ファイル名処理を再利用。  
- 複数ファイルを ZIP で返す場合は **zip-utils.js** と **JSZip**（CDN は既に pdf.html 等で cdnjs 3.10.1 を使用）をそのまま利用可能。  
- 複数ファイルを順次処理する場合は **tool-runner.js** のパターンを流用できる。単一ファイル＋プレビュー中心のUIの場合は、tool-runner を使わず独自の「選択→処理→ダウンロード」でも可（推測）。

---

## 3. CSV/Excel で必要なライブラリ候補の調査

### 3.1 既存CDN利用状況（事実）

- **pdf.html 517–525行**:  
  - `pdf-lib` 1.17.1、`pdf.js` 3.11.174、`jszip` 3.10.1（いずれも `cdnjs.cloudflare.com/ajax/libs/...`）。
- **image-batch.html 508行、image-cleanup.html 519行**:  
  - `jszip` 3.10.1（cdnjs）。

**結論**: 新規CDNは同じ cdnjs で揃えるとキャッシュ・方針の一貫性が取りやすい（推測）。

---

### 3.2 XLSX 処理（SheetJS）

- **コードベース**: SheetJS / xlsx の参照はなし。  
- **推測**:  
  - ブラウザで .xlsx の読み書きには **SheetJS (xlsx)** が一般的。  
  - CDN: 例として `https://cdn.sheetjs.com/xlsx-0.20.0/package/dist/xlsx.full.min.js` や unpkg/cdnjs。  
  - フルビルドはサイズが大きい（1MB 前後）。  
  - 読み込み順: 既存の file-validation → file-utils → zip-utils → tool-runner のあと、xlsx を読み込み、その後に csv 専用の `csv-ops.js`（仮）を読み込む形が安全（推測）。

---

### 3.3 CSV パース（PapaParse 等）

- **コードベース**: PapaParse の参照はなし。  
- **推測**:  
  - CSV のパース・ヘッダー検出・改行・クォート処理には **PapaParse** がよく使われる。  
  - CDN: 例 `https://cdnjs.cloudflare.com/ajax/libs/PapaParse/5.4.1/papaparse.min.js`。  
  - 軽量。encoding は別ライブラリに任せる想定（推測）。

---

### 3.4 文字コード変換（Shift-JIS）

- **コードベース**: encoding.js / iconv / TextDecoder の Shift-JIS 利用は未使用。  
- **推測**:  
  - ブラウザの `TextDecoder('shift_jis')` は環境によっては未対応のため、**encoding.js**（または `text-encoding` 等）を CDN で入れる方法がある。  
  - 例: `encoding-japanese`（npm）の UMD や、Shift-JIS デコード用の小さなライブラリを 1 本追加する形が考えられる（推測）。  
  - 既存の jszip とは役割が違うため、併用で問題ない（推測）。

---

## 4. MVP 実装の設計案

### 4.1 UI 構成案

- **入力**: ファイル選択（ドラッグ＆ドロップ + input）。accept は `.csv,.xlsx,.xls`（必要に応じて）。  
- **プレビュー**: 先頭 N 行をテーブル表示（列ヘッダー＋数行）。既存の tool-section 内に `#preview-area` を置く形（推測）。  
- **操作モード**: ①文字コード変換 ②CSV⇄XLSX ③重複削除 ④列の抽出/並べ替え/ヘッダ名置換 ⑤分割。select またはタブで切り替え（pdf の mode と同様、pdf.html 335行付近）。  
- **オプション**: モードごとにキー列指定・列選択・区切り文字・出力文字コード（UTF-8/BOM 有無など）を表示。  
- **出力**: 「ダウンロード」単体、複数ファイルの場合は ZIP（zip-utils + FileUtils.downloadBlob）。

---

### 4.2 サイズ制限とエラーメッセージ

- **file-validation.js** の `validateFiles` に合わせ、例:  
  - `maxFiles`: 10～20、`maxFileSize`: 10MB～20MB、`maxTotalSize`: 50MB～100MB（CSV/Excel は行数でメモリが増えるためやや控えめにする案）。  
- **allowedExtensions**: `['.csv', '.xlsx', '.xls']`。  
- **allowedMimeTypes**: `text/csv`, `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, `application/vnd.ms-excel` 等。  
- 拒否理由は既存と同様に `rejected[].reason` で表示（pdf.html の #rejected-files と同様）。

---

### 4.3 出力ファイル名規則

- **既存**: `FileValidation.sanitizeFilename` と日付サフィックス（export-utils.js 等で `filenameBase_YYYYMMDD.ext`）。  
- **案**: 入力ファイル名のベース + 操作サフィックス + 日付。例: `data_utf8_20260210.csv`、`data_dedup_20260210.xlsx`。複数出力時は ZIP に `元名_分割1.csv` などを入れる（推測）。

---

### 4.4 失敗しやすい論点

- **大容量**: 行数が多いとメモリ・UI フリーズ。行数上限（例: 10万行）と「先頭 N 行のみプレビュー」で注意喚起（推測）。  
- **改行コード**: CRLF / LF / CR 混在でパースずれ。PapaParse や SheetJS のオプションで統一する前提をガイドに記載（推測）。  
- **クォート**: ダブルクォート内のカンマ・改行。パーサー任せだが、エラー時は「クォートの付け方を確認」とガイドに書く（推測）。  
- **Shift-JIS**: BOM なし・機種依存文字で文字化け。encoding ライブラリの挙動と「対応外文字は代替表示」等をガイドで明記（推測）。

---

## 5. 実装時に触るファイル一覧とコミット分割案

### 5.1 追加するファイル

| ファイル | 内容 |
|----------|------|
| `templates/tools/csv.html` | ツール本体。ヘッダー・ファイル選択・モード・プレビュー・出力。 |
| `templates/guide/csv.html` | ガイド。できること・使い方・制限・データ取り扱い・FAQ・関連リンク・nav-links。 |
| `static/js/csv-ops.js`（仮） | CSV/Excel の読み込み・変換・重複削除・列操作・分割・ダウンロード/ZIP のロジック（必要に応じて複数に分割可）。 |

### 5.2 修正するファイル

| ファイル | 変更内容 |
|----------|----------|
| `lib/products_catalog.py` | PRODUCTS に `id: 'csv'`, path `/tools/csv`, guide_path `/guide/csv` のエントリを追加。 |
| `app.py` | `@app.route('/tools/csv')` と `@app.route('/guide/csv')` を追加。get_product_by_path は lib.routes から（既存ツールと同様）。 |
| `lib/nav.py` | `get_nav_sections_fallback()` 内の「ツール別ガイド」に `{'name': 'CSV/Excelユーティリティ', 'path': '/guide/csv', 'icon': '📊'}` を 1 件追加（78行付近のリスト）。get_nav_sections は PRODUCTS 由来のため、PRODUCTS に追加すれば自動反映。 |
| `templates/sitemap.html` | ガイド一覧に「CSV/Excelユーティリティガイド」の固定リンクを 1 行追加（170行付近のリスト）。sitemap.xml は PRODUCTS から生成されるため、PRODUCTS 追加で /tools/csv と /guide/csv が自動で含まれる（app.py 2094–2118行）。 |

### 5.3 コミット分割案

| # | コミット | 内容 |
|---|----------|------|
| 1 | feat(csv): add PRODUCTS entry, routes, and empty templates | products_catalog に csv エントリ。app.py に /tools/csv と /guide/csv。templates/tools/csv.html と guide/csv.html は最小構成（タイトル・説明・「準備中」等）。nav フォールバックと sitemap.html に 1 行追加。 |
| 2 | feat(csv): CSV processing (UTF-8 only) | csv-ops.js で UTF-8 CSV の読み込み・プレビュー・文字コード変換（UTF-8→UTF-8 はそのまま）・CSV ダウンロード。PapaParse CDN 追加。file-validation / file-utils 利用。 |
| 3 | feat(csv): Shift-JIS support | encoding 用 CDN と csv-ops 内の SJIS デコード/エンコード。入力文字コード選択 UI。 |
| 4 | feat(csv): XLSX and guide, internal links | SheetJS CDN。CSV⇄XLSX・重複削除・列操作・分割のロジックと UI。guide/csv.html の本文・FAQ・制限事項を完成。AutoFill / guide/excel-format / troubleshooting との内部リンク追加（下記 SEO 案を反映）。 |

（※ ②と④で XLSX をまとめてもよい。ここでは「まず CSV のみ→SJIS→XLSX とガイド」の順で分割する案。）

---

## 6. SEO 観点：トピカリティと内部リンク設計案

### 6.1 既存の Excel/勤怠まわり

- **事実**:  
  - `/guide/excel-format`（Excel ファイルの作成方法）、`/guide/troubleshooting`（トラブルシューティング）、`/guide/autofill`（AutoFill ガイド）。  
  - FAQ 等で「CSV は非対応、.xlsx で」と明記（faq.html 279行、excel-format-mistakes-and-design.html 252行）。

### 6.2 内部リンク案（推測）

- **guide/csv.html 内**:  
  - 「Jobcan に上げる勤怠データは Excel 形式が必須です。当ツールで CSV から XLSX に変換したあと、<a href="/guide/excel-format">Excel の形式</a>を確認してから <a href="/autofill">AutoFill</a> でアップロードしてください。」  
  - トラブルシューティング欄に「変換後の Excel で日付・時刻がおかしい場合は <a href="/guide/troubleshooting">トラブルシューティング</a> を参照。」  
- **guide/excel-format.html**:  
  - 「CSV しかない場合は <a href="/tools/csv">CSV/Excelユーティリティ</a> で XLSX に変換できます。」を 1 文追加。  
- **guide/troubleshooting.html**:  
  - ファイル形式の項目に「CSV の場合は <a href="/guide/csv">CSV/Excelユーティリティガイド</a> で XLSX に変換してから利用してください。」を追加。  
- **autofill ガイド / faq**:  
  - 「CSV を Excel 形式にしたい」→ `/tools/csv` または `/guide/csv` へのリンクを 1 箇所追加。

これにより「勤怠・Excel・CSV・トラブル」が相互にリンクされ、トピックの一貫性が高まる（推測）。

---

## 7. 依存追加の整理

| 種別 | 候補 | 用途 | 既存との相性 |
|------|------|------|----------------|
| CSV パース | PapaParse（CDN） | パース・ヘッダー・改行・クォート | 新規。file-utils と併用。 |
| XLSX | SheetJS（CDN） | .xlsx 読み書き | 新規。zip-utils で複数 xlsx を ZIP に可能。 |
| 文字コード | encoding.js 等（CDN） | Shift-JIS デコード/エンコード | 新規。PapaParse の前段でバイト→文字列に使用（推測）。 |
| ZIP | JSZip（既存） | 複数ファイル出力 | 既存のまま。csv ツールでも同じ CDN を読み込む。 |

---

## 8. まとめ

- **追加パターン**: PRODUCTS に 1 エントリ、app.py に 2 ルート、tools/csv.html と guide/csv.html を既存ツール/ガイドのレイアウトに合わせて追加。tool_guide_link は product を渡せばそのまま表示される。  
- **再利用**: file-validation、file-utils、zip-utils、tool-runner（必要なら）をそのまま利用。  
- **新規依存**: PapaParse、SheetJS、Shift-JIS 用 encoding の CDN を検討。  
- **実装順**: ルート＋空テンプレ → CSV（UTF-8）→ SJIS → XLSX＋ガイド＋内部リンク、の 4 コミット案で整理した。  
- 断定できる箇所は「ファイル:行番号」で記載し、それ以外は「推測」と明記した。

以上。
