# CSV/Excelユーティリティ 実装完了レポート

**日付**: 2026-02-10  
**ブランチ**: `feature/add-csv-excel-utility`  
**目的**: Phase B 実装のコミット一覧・追加ファイル・手動テスト手順・制約確認を記録する。

---

## 1. コミット一覧（Phase B）

| 順 | コミット | 内容 |
|----|----------|------|
| 1 | `3af2b38` | feat(csv): add routes, PRODUCTS entry, nav, sitemap link, and empty tool/guide pages |
| 2 | `bb05298` | feat(csv): CSV UTF-8 MVP - column extract, dedupe by key, N-row split; PapaParse CDN; samples |
| 3 | `ec70d1d` | feat(csv): add CSV⇄XLSX conversion with SheetJS CDN |
| 4 | `06eccbc` | feat(csv): add Shift-JIS input/output with encoding-japanese CDN |
| 4b | `78ccfa4` | fix(csv): scope getInputEncoding/getOutputEncoding for run button |
| 5 | `ab190bd` | docs(csv): complete guide and add internal links (excel-format, troubleshooting, faq) |

---

## 2. 追加・変更ファイル一覧

### 新規追加

| ファイル | 説明 |
|----------|------|
| `static/js/csv-ops.js` | CSV/XLSX パース・列抽出・重複削除・分割・Blob出力・文字コード（encoding-japanese）処理 |
| `templates/tools/csv.html` | ツールUI（dropzone、モード選択、プレビュー、結果） |
| `templates/guide/csv.html` | ガイド本文（できること、使い方、制限、データ取り扱い、FAQ、関連リンク） |
| `docs/dev-samples/csv/sample_utf8.csv` | 手動テスト用 UTF-8 サンプル |
| `docs/dev-samples/csv/sample_columns.csv` | 手動テスト用 列サンプル |

### 変更

| ファイル | 変更内容 |
|----------|----------|
| `lib/products_catalog.py` | csv エントリ追加（id, path, guide_path, status=available 等） |
| `app.py` | `/guide/csv`, `/tools/csv` ルート追加 |
| `lib/nav.py` | フォールバックに CSV/Excel 1 件追加 |
| `templates/sitemap.html` | `/guide/csv` 固定リンク 1 行追加 |
| `templates/guide/excel-format.html` | 「CSVしかない場合は /tools/csv でXLSX変換」1 文追加 |
| `templates/guide/troubleshooting.html` | その他のリソースに CSV/Excelユーティリティガイド 追加 |
| `templates/faq.html` | さらに詳しく知るに CSV/Excelユーティリティガイド 追加 |

---

## 3. 手動テスト手順

1. **表示確認**
   - `/tools/csv` が開く。ヘッダー・フッター・ツール一覧に CSV/Excel が出る。
   - `/guide/csv` が開く。ガイド一覧に CSV/Excel が出る。
   - ツール一覧・ガイド一覧から両方に遷移できる。

2. **CSV UTF-8 MVP**
   - `docs/dev-samples/csv/sample_utf8.csv` を選択。
   - 列の抽出・並べ替え: 列を外して実行 → 1 ファイル DL。
   - 重複削除: キー列を選んで実行 → 1 ファイル DL。
   - N行ごと分割: N=2 などで実行 → ZIP で複数 DL。

3. **CSV⇄XLSX**
   - CSV→XLSX: 上記 CSV でモード「CSV→XLSX」→ XLSX が DL できる。
   - XLSX→CSV: その XLSX を選択し「XLSX→CSV」→ CSV が DL できる。ファイル名に日付サフィックスが付くこと。

4. **文字コード（Shift-JIS）**
   - 入力: 「入力ファイルの文字コード」を Shift-JIS にし、SJIS の CSV を選択 → プレビューで文字化けしないこと。
   - 出力: 「出力CSVの文字コード」で UTF-8（BOMあり/なし）・Shift-JIS を選んで実行 → 期待どおり DL できること。

5. **制限・エラー**
   - 行数超過（約10万行超）でエラーメッセージが出ること。
   - ファイルサイズ・拡張子でリジェクトされること（rejected 表示）。

6. **内部リンク・sitemap**
   - `/guide/excel-format` に「CSVしかない場合は /tools/csv でXLSX変換」の文がある。
   - `/guide/troubleshooting` の「その他のリソース」に CSV/Excelガイド がある。
   - `/faq` の「さらに詳しく知る」に CSV/Excelガイド がある。
   - `/sitemap.xml` に `/tools/csv` と `/guide/csv` が含まれる（PRODUCTS 由来の動的生成）。

---

## 4. 制約確認（非アップロード・ログ禁止）

| 項目 | 確認内容 |
|------|----------|
| ファイルをサーバに送らない | Network タブで `/tools/csv` 実行時にファイル送信（fetch/POST で body にファイル）が **ない** こと。 |
| パスワード・ファイル内容を console.log しない | Console に CSV/Excel の内容やパスワードが **出ていない** こと。処理段階・件数などの非機微ログのみ可。 |
| 例外メッセージ | エラー時、技術用語だけの表示にならず、ユーザー向けの短いメッセージになっていること。 |
| minutes 非依存 | minutes の復活・依存の再導入を **していない** こと。 |

---

## 5. 外部CDN（バージョン固定）

| ライブラリ | URL | 用途 |
|------------|-----|------|
| PapaParse | cdnjs 5.4.1 | CSV パース |
| SheetJS | cdn.sheetjs.com xlsx-0.20.3 | CSV⇄XLSX |
| encoding-japanese | jsDelivr 2.0.0 | Shift-JIS 入出力 |
| JSZip | cdnjs 3.10.1 | 複数ファイル ZIP DL |

---

## 6. 備考

- Phase A レポート: `docs/status-reports/2026-02-10_csv_tool_phaseA_fact_check.md`
- sitemap.xml は `app.py` の `sitemap()` で PRODUCTS から `path` と `guide_path` を自動追加するため、csv 追加後は `/tools/csv` と `/guide/csv` が含まれる。
- 既存ツール（pdf / image / seo / autofill）の表示・動作が崩れていないことを各コミット後に確認済みとする。
