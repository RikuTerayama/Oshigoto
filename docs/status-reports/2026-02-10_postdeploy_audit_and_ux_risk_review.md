# 本番デプロイ後監査・UXリスクレビュー

**日付**: 2026-02-10  
**目的**: 本番デプロイ済みの状態で、潜在リスクとUX毀損を事実ベースで洗い出し、改善候補を優先度付きで提示する。  
**絶対条件**: 事実と推測を分離、事実には証跡（コマンド・出力・ファイル:行）、改善は最小差分優先。

---

## 1. サマリ（結論と優先度付き改善リスト）

### 本番URL（BASE_URL）の根拠

| 根拠 | 場所 |
|------|------|
| app.py の sitemap ベースURL | app.py 2050 行: `base_url = 'https://jobcan-automation.onrender.com'` |
| テンプレートの canonical・OGP | templates/includes/head_meta.html 30 行、templates/tools/csv.html 20 行 等 |
| SRE_RUNBOOK.md | healthz 等の URL が `https://jobcan-automation.onrender.com` |

**採用**: `BASE_URL = https://jobcan-automation.onrender.com`

### 本番ルート・301 の結果（事実）

本番に対する `python scripts/verify_deploy_routes.py --live https://jobcan-automation.onrender.com` の結果は**期待どおり**。  
証跡: `docs/status-reports/evidence_prod_routes.log` に保存済み。

| パス | 期待 | 本番結果 |
|------|------|----------|
| /tools/seo | 200 | 200 OK |
| /tools/csv | 200 | 200 OK |
| /guide/csv | 200 | 200 OK |
| /tools/minutes | 301 Location=/tools | 301 Location: /tools |
| /guide/minutes | 301 Location=/guide | 301 Location: /guide |
| /tools/pdf/ | 301 Location=/tools/pdf | 301 Location: /tools/pdf |

**結論**: 顕在のルーティング不具合はなし。何をもって問題なしとするか: 上記6項目がすべて期待値と一致していること（証跡ログで確認済み）。

### 優先度付き改善リスト（要約）

| 優先度 | 内容 | 背景 |
|--------|------|------|
| P1 | CDN 失敗時のエラー表示 | 依存 script が読めない場合に無言で壊れるリスク |
| P2 | プレビュー/結果のファイル名エスケープ | ファイル名に `<` 等が含まれる場合の XSS リスク低減 |
| P2 | 大ファイル時の進捗・キャンセル | メモリ枯渇・フリーズ時の UX |
| P3 | プライバシー文言の明示 | 「ファイルを送信しません」の UI 明示 |
| P3 | アクセシビリティ（フォーカス・キーボード） | キーボード操作・フォーカス順 |
| 参考 | 大改修案 | 末尾に分離 |

---

## 2. 事実（証跡と参照）

### 2.1 本番ルート・301 の live 証跡

**コマンド**:
```bash
python scripts/verify_deploy_routes.py --live https://jobcan-automation.onrender.com --output docs/status-reports/evidence_prod_routes.log
```

**出力（要約）**: 全6パスで期待どおり。完全ログは `docs/status-reports/evidence_prod_routes.log` を参照。

**curl 証跡**: `scripts/verify_deploy_routes.sh` は Linux/macOS/Git Bash 用。本監査では Windows のため Python の `--live` で同等の GET を実行し、その出力を証跡とした。手動で curl 証跡を取る場合（Git Bash 等）:
```bash
# Git Bash 等
BASE_URL=https://jobcan-automation.onrender.com
for path in /tools/seo /tools/csv /guide/csv /tools/minutes /guide/minutes /tools/pdf/; do
  echo "curl -I $BASE_URL$path"; curl -sI "$BASE_URL$path"; echo "";
done
```
→ 結果を `evidence_prod_curl.log` に保存可能。

### 2.2 /tools/csv のテンプレート・JS 依存

| ファイル | 役割 |
|----------|------|
| templates/tools/csv.html | ツールUI・script 読み込み順の定義 |
| static/js/csv-ops.js | パース・列操作・Blob 出力・文字コード |
| static/js/file-validation.js | ファイル数・サイズ・拡張子チェック（CSV_RULES で使用） |
| static/js/file-utils.js | downloadBlob, getFilenameWithoutExtension 等 |
| static/js/zip-utils.js | 複数ファイル時の ZIP 作成（JSZip 使用） |

### 2.3 CDN 依存の一覧と読み込み順（templates/tools/csv.html）

| 行 | URL | 役割 | 前提 |
|----|-----|------|------|
| 103 | https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js | ZIP | 先に読み込まれること |
| 105 | https://cdnjs.cloudflare.com/ajax/libs/PapaParse/5.4.1/papaparse.min.js | CSV パース | csv-ops.js より前 |
| 106 | https://cdn.sheetjs.com/xlsx-0.20.3/package/dist/xlsx.full.min.js | XLSX 入出力 | csv-ops.js より前 |
| 107 | https://cdn.jsdelivr.net/npm/encoding-japanese@2.0.0/encoding.min.js | Shift-JIS | csv-ops.js より前 |

読み込み順（証跡: csv.html 104–108 行）:  
file-validation.js → file-utils.js → jszip → zip-utils.js → PapaParse → SheetJS → encoding-japanese → csv-ops.js  
依存の前提: Papa, XLSX, Encoding, JSZip がグローバルに存在したうえで csv-ops.js が実行される。

### 2.4 CSP・セキュリティヘッダ

**事実**: app.py 内で `Content-Security-Policy` を設定している箇所は**なし**（検索: Content-Security-Policy, X-Frame, X-Content-Type 等）。  
after_request で付与しているヘッダは X-Request-ID（134–139 行）、X-Robots-Tag（396–402 行）、X-Error-Id（176, 190 行）、Retry-After（1220 行）等のみ。  
→ CSP により CDN がブロックされている状態ではない（CSP 未設定のため）。

### 2.5 本番での CDN/Console 実ロード証跡（E2E）

**実施**: 実行環境に Playwright が未インストールのため、本番向け E2E は未実行。  
**証跡ファイル**: `evidence_prod_e2e.json` は未生成。

**手動確認手順（本番で実施した場合の記録用）**:
1. ブラウザで https://jobcan-automation.onrender.com/tools/csv を開く。
2. 開発者ツール → Network: cdnjs.cloudflare.com, cdn.sheetjs.com, cdn.jsdelivr.net の script が 200 で返っていること。
3. Console で `typeof Papa !== 'undefined' && typeof XLSX !== 'undefined' && typeof Encoding !== 'undefined' && typeof JSZip !== 'undefined'` を実行 → `true` であること。
4. Console に `Papa is not defined` 等の未定義エラーが出ていないこと。

**E2E を実行する場合（Playwright 導入済み環境）**:
```bash
set BASE_URL=https://jobcan-automation.onrender.com
python scripts/e2e_tools_csv_playwright.py --output docs/status-reports/evidence_prod_e2e.json
```
→ 出力 JSON の `globals_ok`, `console_errors`, `origin_mutating_requests` をレポートに転記する。

### 2.6 ファイルがサーバに送られていないこと（コード上の確認）

**検索対象**: fetch, XMLHttpRequest, sendBeacon, FormData, .submit(

**結果（行番号付き）**:

| ファイル | ヒット | 備考 |
|----------|--------|------|
| static/js/csv-ops.js | 0 | 送信処理なし |
| templates/tools/csv.html | 0 | 送信処理なし |
| static/js/file-utils.js | 0 | downloadBlob のみ |
| static/js/file-validation.js | 0 | バリデーションのみ |

**他ツール（CSV 以外）でのヒット（参考）**:
- templates/tools/seo.html: 804, 932 行（fetch: 自サイト API）
- templates/tools/pdf.html: 938, 941, 972, 975 行（FormData + fetch: /api/pdf/*）
- templates/autofill.html, index.html: FormData + fetch（/upload 等）
- static/js/seo-ogp-canvas.js: 205 行（fetch(dataURL) → blob、data URL 取得用）

**結論**: /tools/csv で使用している csv-ops.js および csv.html 内の script には、サーバへファイルや本文を送る fetch/XMLHttpRequest/sendBeacon/FormData/submit は**存在しない**（0 件）。  
挙動上の確認: Playwright E2E で「ファイル選択〜実行」後に origin への POST/PUT/PATCH を記録する実装は `scripts/e2e_tools_csv_playwright.py` にあり、`origin_mutating_requests` が空であることを証跡とする想定。本番では E2E 未実行のため、手動で Network タブで「実行」後に origin への POST/PUT/PATCH が 0 件であることを確認する手順を推奨。

### 2.7 見落としやすい経路の確認

| 経路 | 確認結果 |
|------|----------|
| navigator.sendBeacon | csv.html, csv-ops.js, file-utils.js, file-validation.js, zip-utils.js にヒットなし |
| 分析・analytics 送信 | csv.html に gtag/ga/analytics の script なし（共通 head は未確認。AdSense 等は別ページで読み込む可能性あり） |
| Service Worker | 本監査では service worker の登録・fetch フックは未検索。CSV ツール単体では未使用の想定。 |
| form の auto submit | csv.html に `<form>` は存在しない。送信はすべて script 内の Blob ダウンロード。 |
| 第三者が追加した script | テンプレートに CDN 4 本と静的 4 本のみ。第三者スクリプトの動的追加はなし。 |

---

## 3. 推測（未確認事項と理由）

- **本番ブラウザでの CDN 実ロード**: 実行環境で Playwright が使えず、本番 URL に対して E2E を実行していない。そのため「本番で Papa/XLSX/Encoding/JSZip が確実に読めている」ことは、手動確認または別環境での E2E で補う必要がある。
- **CDN 障害時の挙動**: コード上、CDN script が 404 やネットワークエラーで読めない場合、`Papa` 等が未定義となり、実行時に `Papa is not defined` 等のエラーになる。ユーザー向けの「CDN が読めません」のようなフォールバックメッセージは現状ない（推測）。
- **大容量 CSV のメモリ**: 約 10 万行まで許容（csv-ops.js MAX_ROWS）しており、端末によってはメモリ圧迫やフリーズの可能性がある。進捗表示やキャンセルは実装されていない（推測）。
- **ファイル名の XSS**: プレビュー表や結果エリアのセル値は `.replace(/</g,'&lt;')` でエスケープされている（csv.html 195, 197, 206 行）。一方、ファイル名をそのまま innerHTML に含めている箇所（136, 140 行: rejected 表示・ファイル一覧）ではエスケープしていない。ファイル名は通常 OS が制御するが、悪意あるファイル名をアップロードされた場合の影響は未検証（推測）。

---

## 4. 潜在リスクとUX毀損ポイント（優先度順）

### P1: CDN 障害・ブロック時の挙動

- **リスク**: cdnjs / sheetjs / jsdelivr のいずれかがブロックまたは障害だと、該当 script が読めず、画面が無言で壊れる（実行時エラー）。
- **現状**: 依存が読めない場合は `Papa is not defined` 等のランタイムエラーに依存。フォールバックや「CDN が読み込めません」といったメッセージはない。
- **証跡**: csv-ops.js 46 行 `if (typeof Papa === 'undefined') throw new Error('PapaParse が読み込まれていません');` 等、各依存で未定義時 throw。

### P2: 大きな CSV/Excel の性能

- **リスク**: メモリ枯渇、タブのフリーズ、長時間無応答。
- **現状**: MAX_ROWS 100000（csv-ops.js 7 行）、ファイルサイズは file-validation で 10MB/50MB 制限（csv.html 111 行）。進捗表示・キャンセルはなし。
- **証跡**: static/js/csv-ops.js 7 行、templates/tools/csv.html 111 行。

### P2: 文字コード・改行・Excel の癖

- **リスク**: Shift-JIS の機種依存文字での文字化け、BOM の有無、CRLF/LF/CR、Excel の数値や日付の文字列化。
- **現状**: 入力は UTF-8/SJIS 選択、出力は UTF-8 BOM あり/なし/SJIS。UI に注意書きあり（csv.html 72 行）。改行コードの正規化や Excel 特有値の扱いは明示していない。
- **証跡**: templates/tools/csv.html 66–72 行、static/js/csv-ops.js readFileAsTextWithEncoding / textToSJISBlob。

### P2: セキュリティ（XSS・ファイル名・サイズ）

- **リスク**: CSV 内容を DOM に出す箇所で XSS。ファイル名の表示で XSS。Zip 展開は行っていない。サイズ制限はあり。
- **現状**: プレビュー・結果メッセージでは `.replace(/</g,'&lt;')` でエスケープ（csv.html 195, 197, 206 行）。ファイル名は 136, 140 行で未エスケープ。Zip は JSZip で生成のみで展開はなし。サイズは file-validation で制限。
- **証跡**: 上記行番号。

### P3: アクセシビリティ

- **リスク**: キーボード操作、フォーカス順、コントラスト、エラー表示の伝わりやすさ。
- **現状**: フォーカス管理・aria 属性・スキップリンク等は未確認。エラーは setOutput でテキスト表示。
- **証跡**: templates/tools/csv.html のボタン・select・ファイル入力のマークアップ。

### P3: ルーティング・正規化・SEO

- **リスク**: 末尾スラッシュの二重リダイレクト、canonical の不整合。
- **現状**: 本番で /tools/pdf/ は 301 で /tools/pdf に寄ることを確認済み。canonical は head_meta で共通。
- **証跡**: evidence_prod_routes.log、app.py normalize_trailing_slash。

### P3: プライバシー表示

- **リスク**: 「ファイルをサーバに送らない」がユーザーに伝わっていない。
- **現状**: ページ説明に「ファイルはアップロードせず、ブラウザ内で変換します」（csv.html 49, 5 行）とある。ツール上部の文言で明示されている。
- **証跡**: templates/tools/csv.html 5 行 page_description、49 行 p タグ。

---

## 5. 改善提案（最小差分、コミット計画、受け入れ基準）

### 5.1 P1: CDN 失敗時のエラー表示（最小差分）

- **背景**: P1「CDN 障害・ブロック時の挙動」に効く。依存が読めない場合に無言で壊れず、メッセージを出す。
- **変更案**: ページロード後、短い timeout で `typeof Papa !== 'undefined' && typeof XLSX !== 'undefined' && typeof Encoding !== 'undefined' && typeof JSZip !== 'undefined'` をチェックし、未定義なら #output-area に「必要なスクリプトの読み込みに失敗しました。ネットワークやブロッカーをご確認ください。」と表示する。
- **ファイル・行**: templates/tools/csv.html の inline script 先頭付近（例: 110 行付近）に 1 ブロック追加。
- **影響範囲**: /tools/csv のみ。他ツールは変更しない。
- **受け入れ基準**: CDN をブロックした状態で /tools/csv を開いたとき、上記メッセージが表示される。通常時は表示されない。
- **コミット**: 1 コミット（例: `fix(csv): show message when CDN scripts fail to load`）。

### 5.2 P2: ファイル名のエスケープ（最小差分）

- **背景**: P2「セキュリティ（ファイル名）」に効く。rejected 表示・ファイル一覧でファイル名をそのまま innerHTML に含めている箇所をエスケープする。
- **変更案**: ファイル名を表示する前に `String(name).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')` でエスケープする（または既存の sanitize があれば利用）。
- **ファイル・行**: templates/tools/csv.html 136 行、140 行。`(r.file.name || '')` および `(f.name || '')` をエスケープ関数に通す。
- **影響範囲**: /tools/csv のファイル一覧・rejected 表示のみ。
- **受け入れ基準**: ファイル名に `<script>alert(1)</script>` を含むファイルを選択したとき、スクリプトが実行されず文字列として表示される。
- **コミット**: 1 コミット（例: `fix(csv): escape file names in list and rejected UI`）。

### 5.3 P2: 大ファイル時の進捗・キャンセル（やや大きめ）

- **背景**: P2「大きな CSV/Excel の性能」に効く。長時間処理時の UX 改善。
- **変更案（最小）**: 「実行」クリック直後に「処理中…」を表示している箇所を、行数に応じて「処理中（約 N 行）…」のようにする。キャンセルは AbortController 等で read を中断する必要があり、差分は大きい。
- **ファイル・行**: templates/tools/csv.html の setOutput / 実行ボタン周り。csv-ops の parse は同期的なため、進捗は「開始した」の 1 回のみが現実的。
- **受け入れ基準**: 大量行で実行したとき「処理中…」が表示され、完了後に結果またはエラーが出る。
- **コミット**: 進捗文言の変更のみなら 1 コミット。キャンセルまで含める場合は別コミット（参考に回す）。

### 5.4 P3: プライバシー文言の明示強化（最小差分）

- **背景**: P3「プライバニー表示」の確実な伝達。
- **変更案**: ファイル選択エリアの直下または操作エリアの上に、短い注意書き「このツールはファイルをサーバに送信しません。すべてブラウザ内で処理されます。」を 1 行追加する。
- **ファイル・行**: templates/tools/csv.html 54 行付近（ファイル選択の p の後）または 64 行付近。
- **影響範囲**: /tools/csv の表示のみ。
- **受け入れ基準**: ページを開いたときに、ファイル非送信の文言が目につく位置にある。
- **コミット**: 1 コミット（例: `docs(csv): add explicit privacy notice for no-upload`）。

### 5.5 参考（大改修案・最後に分離）

- **CDN フォールバック**: 主要ライブラリを self-host または optional な 2nd CDN で読み直す仕組み。影響が大きいため、要件とコストを検討のうえ検討。
- **処理の Web Worker 化**: 重いパースを Worker に移し、メインスレッドのフリーズを防ぐ。キャンセルや進捗を Worker と連携させる場合は設計変更が必要。
- **アクセシビリティの抜本対応**: フォーカス順、aria-*、スキップリンク、エラーとラベルの関連付け等。ツール全体の a11y 方針に合わせて別タスクで実施することを推奨。

---

## 証跡ファイル一覧

| ファイル | 説明 |
|----------|------|
| docs/status-reports/evidence_prod_routes.log | 本番ルート・301 の Python --live 実行ログ |
| docs/status-reports/evidence_prod_e2e.json | （未作成）Playwright 導入環境で E2E 実行時に出力する JSON |
| docs/status-reports/evidence_prod_curl.log | （任意）手動で curl を実行した場合のログ保存先 |

---

**注意**: 「現状問題が無さそう」と判断した根拠は、本レポートの「事実」セクションに記載した証跡（本番 200/301 の一致、コード上の fetch/FormData の 0 件、プレビュー出力のエスケープ）による。CDN の実ロードと origin への POST 0 件は、本番ブラウザでの手動確認または E2E で補完することを推奨する。
