# Phase 2（⑥プロダクト品質）監査レポート

**目的**: バズっても「壊れない/迷わない/誤解されない」を最小差分で作るため、主要ツール（特に /tools/csv）の無言障害・innerHTML・二重実行・非送信明示・想定外入力を事実ベースで洗い出す。**本ターンは分析のみ（実装禁止）。**  
**スコープ**: P1=/tools/csv、P2=/tools/pdf, seo, image-batch, image-cleanup（共通パターンのみ言及）。  
**証跡**: file:line、および scripts/smoke_test.py --deploy / verify_deploy_routes.py 実行結果（exit 0 を取得済み）。

---

## A. サマリ（論点別・一言）

| 論点 | P1 /tools/csv | P2 他ツール |
|------|----------------|-------------|
| 無言で壊れる | FileValidation 未定義時にファイル選択で未捕捉 throw → コンソールのみ。CDN 失敗時は CsvOps 内で throw → setOutput で表示される経路あり。 | 共通: 他ツールは tool-runner.js の isRunning で二重実行ガードあり。CSV は独自実装のためガードなし。 |
| innerHTML 由来 | ファイル名を未エスケープで rejectedEl/fileList に挿入 → XSS リスク。プレビュー・setOutput は `<` のみエスケープ。 | 未実施（CSV に集中）。 |
| 二重実行/処理中UI | 実行ボタンに disabled なし・isRunning 相当なし。連打で複数 Promise チェーンが並列実行され、複数回ダウンロード＋結果メッセージ上書き。 | pdf/seo/image-* は ToolRunner 使用で「既に処理が実行中です」throw あり。 |
| 「ファイルは送らない」明示 | 本文に「ローカル処理」「アップロードせず」の文言あり。fetch/XHR/FormData/sendBeacon は CSV 用 JS に存在しない。GA4/AdSense は head 共通で外部通信あり。 | 同上。誤解を減らすなら「計測・広告用の通信以外はファイルを送りません」の一言が有効。 |
| 想定外入力で落ちる | 空ファイル・超行数は CsvOps 内で throw し、processOne/chain の .catch で setOutput。行数上限 100000 は csv-ops.js:54。拡張子偽装は FileValidation で弾くが中身が Excel の .csv 等はパースで失敗し得る → 同様に setOutput。 | 未実施。 |

---

## B. 事実（監査結果）

### B1. CDN 失敗時（パターン別）: file:line / 現状挙動 / “無言”の有無

| パターン | 根拠（file:line） | 現状挙動 | 無言か |
|----------|-------------------|----------|--------|
| PapaParse 未定義 | static/js/csv-ops.js:46 `if (typeof Papa === 'undefined') throw new Error(...)`。同 115-116 toCSVString 内でも Papa 未定義時は自前 join にフォールバック。 | parseCSV 呼び出し時に throw → 呼び元は loadPreview の try/catch または processOne の .catch → setOutput(err.message, true) で表示。 | 否（UI に出る） |
| SheetJS (XLSX) 未定義 | csv-ops.js:180, 198 `if (typeof XLSX === 'undefined') throw new Error(...)` | 同上。 | 否 |
| Encoding (encoding-japanese) 未定義 | csv-ops.js:34, 141 throw | 同上。 | 否 |
| JSZip 未定義 | static/js/zip-utils.js:14-16 throw。CSV ツールは複数出力時に ZipUtils.createZip を使用（csv.html:332）。 | chain.then(...).catch(err => setOutput(err.message, true))（csv.html:334）で表示。 | 否 |
| FileValidation 未定義 | templates/tools/csv.html:219 `FileValidation.validateFiles(files, CSV_RULES)`。リスナー全体に try/catch なし。 | ファイル選択時に ReferenceError。未捕捉のためコンソールのみ。UI には何も出ない。 | **はい（無言）** |
| FileUtils / ZipUtils 未定義 | csv.html:321 FileUtils.downloadBlob、332 ZipUtils.createZip | 実行完了時に throw → .catch で setOutput。 | 否 |

**読み込み順（csv.html:101-108）**: file-validation.js → file-utils.js → jszip.min.js (CDN) → zip-utils.js → papaparse.min.js (CDN) → xlsx.full.min.js (CDN) → encoding.min.js (CDN) → csv-ops.js。いずれか 1 本でも失敗すると後続が未定義になり得る。

---

### B2. innerHTML 棚卸し表（/tools/csv）

| 箇所 | file:line | 入力源 | 現状の対策 | リスク |
|------|-----------|--------|------------|--------|
| rejectedEl.innerHTML | templates/tools/csv.html:136 | r.file.name（ユーザー選択ファイル名）, r.reason（当方文言） | なし | **高**: ファイル名に `<script>alert(1)</script>.csv` 等を入れると実行されうる。 |
| fileList.innerHTML | csv.html:140 | f.name（ユーザー選択ファイル名）, f.size | なし | **高**: 同上。 |
| modeOptions.innerHTML | csv.html:147, 162 | 空または固定文言 | 147 は空、162 は固定文字列 | 低 |
| previewWrap.innerHTML | csv.html:194-200 | ヘッダ/セル値（ファイル内容） | head/cell で `String(h).replace(/</g,'&lt;')` のみ（194-196行目） | 中: `<` のみエスケープ。`>` `"` `'` `&` は未対応。通常の CSV では問題になりにくいが、意図した悪用では不十分。 |
| outputArea.innerHTML | csv.html:206, 268 | 206: msg（err.message または 当方文言）, 268: 固定「処理中...」 | 206: `(msg || '').replace(/</g,'&lt;')` のみ。268: 固定 | 中: msg にライブラリや動的メッセージが含まれる場合、`<` 以外の文字で DOM を壊す/閉じタグを打たれる可能性。 |

**結論（事実）**: ユーザー入力（ファイル名）が **そのまま** innerHTML に入る経路が 2 箇所（136, 140行目）。サニタイズなし。プレビュー・結果メッセージは `<` のみエスケープ。

---

### B3. 実行中 UI: 状態遷移と二重実行リスク

| 項目 | 根拠（file:line） | 現状 |
|------|-------------------|------|
| 実行ボタン disabled | csv.html に `runBtn.disabled` の記述なし。runBtn は 123行目で取得、265行目で click リスナー登録のみ。 | 処理中もクリック可能。 |
| スピナー/文言変更 | 268行目で `outputArea.innerHTML = '<p>処理中...</p>';` のみ。ボタン文言変更なし。 | 「処理中」は結果エリアのみ。 |
| 二重実行ガード | クリックハンドラ内に isRunning 相当のフラグなし。毎回 `const outputs = [];` で新規に Promise チェーンを開始（265-318行目）。 | 連打すると複数チェーンが並列で動く。各チェーンの最後で FileUtils.downloadBlob / ZipUtils.createZip が複数回呼ばれ、setOutput でメッセージが上書きされる。 |
| エラー時の復旧 | .catch で setOutput のみ。ボタンは元から disabled にしていないため「復旧」の概念なし。 | エラー時もボタンは押し続け可能。 |
| 再現手順（コード根拠） | 265行目 `runBtn.addEventListener('click', () => { ... });` が唯一の登録。先頭で `runBtn.disabled = true` 等が無い。 | 手順: ファイル選択 → 実行を短時間で 2 回以上クリック → 2 回以上のダウンロードと結果メッセージの上書きが発生しうる。 |

**比較（P2）**: static/js/tool-runner.js:102-105 で `if (this.isRunning) { throw new Error('既に処理が実行中です'); }` があり、pdf/seo/image-* 等は ToolRunner 経由で二重実行がガードされている。**/tools/csv は ToolRunner を使っていないため同ガードがない。**

---

### B4. 非送信担保（ツール別・外部通信の分類）

| 種別 | /tools/csv | 備考 |
|------|------------|------|
| fetch / XMLHttpRequest / FormData / sendBeacon | **なし** | templates/tools/csv.html のインラインスクリプトおよび static/js/csv-ops.js, file-utils.js, file-validation.js, zip-utils.js に fetch/XHR/FormData/sendBeacon の使用なし（grep で確認。seo-ogp-canvas.js の fetch は dataURL 用で CSV ツールでは未使用）。 |
| ファイル送信 | なし | 同上。Blob は FileUtils.downloadBlob（createObjectURL + a.click）でローカルダウンロードのみ。 |
| CDN（PapaParse, SheetJS, encoding-japanese, JSZip） | あり | スクリプト取得のみ。ユーザーファイルは送っていない。 |
| GA4 / AdSense | あり | templates/includes/head_meta.html で全ページ共通。計測・広告用。 |
| 自サイト API | /tools/csv では未使用 | app.py に /tools/csv 向けの POST ルートはない。 |

**ユーザーが誤解しやすい点**: 「ファイルは一切送らない」と書いてある一方で、GA4/AdSense によりページビューやイベントは外部へ送信される。ファイル内容は送っていないが、通信が「ゼロ」ではない。

**最小差分の文言案**: 「ファイルの内容はサーバーに送信しません。計測・広告のためだけに外部サービス（Google 等）へアクセスすることがあります。」など。

**Service Worker**: リポジトリ全体で `serviceWorker` / `service worker` を検索した結果、docs/status-reports 内の言及のみ。コード上での登録・fetch フックはなし。

---

### B5. エラーハンドリング: 例外経路と UI 表示の有無

| 経路 | file:line | 例外の出し方 | UI 表示 |
|------|-----------|--------------|---------|
| loadPreview（ファイル選択直後） | csv.html:224-257 | try/catch および .catch(err => setOutput(err.message, true)) | setOutput で表示 |
| processOne（実行時の 1 ファイル処理） | csv.html:274-319, 334 | 各 Promise の .catch(err => setOutput(err.message, true)) | 同上 |
| CsvOps 内の throw | csv-ops.js:34, 46, 54, 141, 180, 198 等 | Error を throw。呼び元は上記の try/catch または .catch。 | 同上 |
| 行数上限 | csv-ops.js:54 `if (rows.length > this.MAX_ROWS) throw new Error(...)` | MAX_ROWS=100000。超えた場合のみ throw。 | setOutput で表示 |
| 空ファイル | Papa.parse('', { skipEmptyLines: true }) → data が [] または [[]]。buildModeOptions で早期 return。実行時は selectColumns(rows, []) 等で空配列になり得る。 | 例外ではなく「出力がありません」に至る経路（321行目）。 | setOutput('出力がありません。', true) |
| FileValidation の throw | なし（validateFiles は return で rejected を返す）。ただし FileValidation が未定義のときは change リスナー内で ReferenceError。 | 未捕捉。 | なし（無言） |

**想定外入力**: 拡張子偽装（.csv で Excel バイナリ）は readFileAsText で読むとパース失敗し、setOutput で表示。BOM 付き UTF-8 は readAsText でそのまま読まれ Papa が解釈。極端に長い行・NULL 混入は未検証（ブラウザ/E2E での証跡は未実施）。

---

## C. 推測・注意（証跡不足と追加で取るべき証跡）

- **CDN 失敗の実機再現**: 未実施。推奨: DevTools で cdnjs / sheetjs / jsdelivr をブロックしてファイル選択・実行を行い、どのパターンで「何も起きない」になるか記録する。
- **二重実行の実機確認**: 未実施。推奨: /tools/csv でファイル選択 → 実行を連打し、ダウンロード回数と結果メッセージを記録。
- **ファイル名 XSS の実機確認**: 未実施。推奨: ファイル名に `<img src=x onerror=alert(1)>` 等を付けたファイルで選択し、rejected または file-list 表示時の挙動を記録。
- **空/巨大/異常 CSV の網羅**: コード上は throw → setOutput の経路があるが、空・BOM・CR のみ・NULL・極長行は未検証。必要なら E2E または手動でケースを追加。
- **他ツール（pdf, seo, image-*）の innerHTML**: 本監査では未実施。必要なら同様に「入力源・対策・リスク」を列挙。

---

## D. 最小差分バックログ（TSV）

**ファイル**: `docs/phase2_product_quality_backlog.tsv` に同じ内容を格納（コピペ用）。

| 優先度 | 対象URL | 問題（事実） | 影響 | 最小修正案 | 受け入れ基準 | 必要証跡 |
|--------|---------|-------------|------|------------|--------------|----------|
| P1 | /tools/csv | ファイル名を innerHTML に未エスケープで挿入（csv.html:136, 140） | ファイル名に HTML/script を含むと XSS の可能性 | 136・140 でファイル名を DOM に出す前に escapeHtml 等でエスケープ（少なくとも & < > " '）してから innerHTML に渡す | ファイル名に `<script>alert(1)</script>` を入れても実行されない。表示は文字として見える | ブラウザでファイル名 XSS テストを実施しスクショまたは手順を残す |
| P1 | /tools/csv | FileValidation 未定義時にファイル選択で未捕捉 throw（csv.html:219 周辺、リスナーに try/catch なし） | CDN/自前 JS 失敗時、ユーザーは何も起きないと感じる | change リスナー先頭で try/catch し、catch で setOutput('ファイルの検証に失敗しました。ページを再読み込みしてください。', true) 等を表示 | スクリプト失敗時でも UI にメッセージが出る | CDN ブロック等で FileValidation 未定義を再現し確認 |
| P1 | /tools/csv | 実行ボタンに二重実行ガードなし（csv.html:265-318） | 連打で複数ダウンロード・結果上書き | クリック先頭で isRunning フラグを立て、chain.then/catch の finally でフラグを下ろす。フラグが true の間は return するか、runBtn.disabled = true/false で制御 | 連打しても 1 回だけ処理が走る。処理中はボタン disabled または「処理中」表示 | 連打テストでダウンロード回数が 1 回であることを確認 |
| P2 | /tools/csv | setOutput の msg が `<` のみエスケープ（csv.html:206） | 動的メッセージに `"` や `>` が含まれると DOM が壊れる可能性 | msg をフル HTML エスケープ（& < > " '）するか、textContent で表示する | 任意の msg でもタグが解釈されない | 任意 |
| P2 | /tools/csv | プレビュー表のセルが `<` のみエスケープ（csv.html:194-196） | 同上 | セル文字列を同様にフルエスケープ | 同上 | 任意 |
| P2 | 全ツール | 「ファイルは送らない」と GA/計測の区別が伝わりにくい | 誤解・クレーム | ツール本文に 1 文追加「計測・広告のためだけに外部へアクセスすることがあります」等 | 文言レビューで了承 | なし |

---

## E. 追加調査コマンド集（コピペ用）

### ripgrep（プロジェクトルートで）

```bash
# innerHTML 使用箇所（CSV 関連）
rg "innerHTML" --type-add 'web:*.{html,js}' -t web -n

# ネットワーク送信の有無（CSV で使う JS）
rg "fetch|XMLHttpRequest|FormData|sendBeacon" static/js/file-validation.js static/js/file-utils.js static/js/zip-utils.js static/js/csv-ops.js
rg "fetch|XMLHttpRequest|FormData|sendBeacon" templates/tools/csv.html

# Service Worker
rg -i "serviceWorker|service worker" .
```

### ローカル確認手順（証跡用）

1. **CDN ブロックでの無言障害**
   - DevTools → Network → 右クリックで「Block request URL」に `cdnjs.cloudflare.com` や `cdn.sheetjs.com` 等を追加。
   - /tools/csv を開き、ファイルを選択。
   - 期待: 何らかのメッセージが結果エリアに出るか。出ない場合は「無言」として記録。

2. **二重実行**
   - /tools/csv で 1 ファイル選択 → 「実行」を素早く 2 回クリック。
   - 期待（修正後）: ダウンロードは 1 回、結果メッセージは 1 回だけ更新。

3. **ファイル名 XSS**
   - ファイル名を `test<script>alert(1)</script>.csv` や `test<img src=x onerror=alert(1)>.csv` にした CSV を選択（拒否されても「拒否理由」表示に名前が出る）。
   - 期待（修正後）: アラートが立たず、名前がテキストとして表示される。

4. **巨大ファイル / 行数上限**
   - 100001 行の CSV で実行。
   - 期待: 「行数が上限（100000行）を超えています」が結果エリアに表示される。

---

**証跡（デプロイ系）**

- `python scripts/smoke_test.py --deploy` → exit 0（tools/seo, tools/csv, guide/csv=200；minutes 301；/tools/pdf/ 301）。
- `python scripts/verify_deploy_routes.py` → exit 0（上記と同様の curl 風証跡を出力、全 OK）。

以上、Phase 2 プロダクト品質監査の記録とする。
