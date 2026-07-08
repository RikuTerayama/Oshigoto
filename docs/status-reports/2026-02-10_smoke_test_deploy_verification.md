# 本番デプロイ前スモークテスト・検証レポート

**日付**: 2026-02-10  
**目的**: minutes 削除と CSV/Excel ユーティリティ追加が本番デプロイ前に壊れていないかを事実ベースで検証する。  
**対象ブランチ**: cleanup/remove-minutes, feature/add-csv-excel-utility, seo/topicality-phase-b

---

## 1. 事実（ファイル・行・確認結果）

### 1.1 ルートとリダイレクト（app.py）

| ファイル | 行 | 事実 |
|----------|-----|------|
| app.py | 371-388 | `normalize_trailing_slash()`: GET/HEAD で末尾スラッシュありかつ `url_map` に存在するパスなら 301 でスラッシュなしへリダイレクト。`/static/`・`/api/` は対象外。 |
| app.py | 1001-1004 | `/guide/minutes` → `redirect('/guide', code=301)` |
| app.py | 1144-1147 | `/tools/minutes` → `redirect('/tools', code=301)` |
| app.py | 1011-1014 | `/guide/csv` → `render_template('guide/csv.html')` |
| app.py | 1156-1161 | `/tools/seo` → get_product_by_path + render_template('tools/seo.html') |
| app.py | 1163-1168 | `/tools/csv` → get_product_by_path + render_template('tools/csv.html') |
| app.py | 1023-1027 | `/tools/pdf` が存在するため、`/tools/pdf/` は 301 で `/tools/pdf` へマッチする。 |

### 1.2 CSV ツール: ファイル送信なし（コード上）

| ファイル | 確認方法 | 結果 |
|----------|----------|------|
| static/js/csv-ops.js | 検索: fetch, XMLHttpRequest, post, upload, FormData | **0件**。ファイル読み込みは FileReader のみ。 |
| templates/tools/csv.html | 同上 | **0件**。フォーム送信・fetch なし。 |
| templates/tools/csv.html | フォーム要素 | `<form>` は存在しない。`<input type="file">` は script 内で FileReader に渡しているのみ。 |

**結論（事実）**: 実装コード上、CSV/Excel ツールからサーバへファイルを送る処理は存在しない。

### 1.3 /tools/csv の外部 CDN（templates/tools/csv.html）

| 行 | URL | 用途 |
|----|-----|------|
| 103 | https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js | ZIP |
| 105 | https://cdnjs.cloudflare.com/ajax/libs/PapaParse/5.4.1/papaparse.min.js | CSV パース |
| 106 | https://cdn.sheetjs.com/xlsx-0.20.3/package/dist/xlsx.full.min.js | XLSX |
| 107 | https://cdn.jsdelivr.net/npm/encoding-japanese@2.0.0/encoding.min.js | Shift-JIS |

読み込み順: file-validation.js → file-utils.js → jszip → zip-utils.js → PapaParse → SheetJS → encoding-japanese → csv-ops.js（依存が先、csv-ops が最後）。

---

## 2. 再現可能なスモークテスト手順

### 2.1 自動スクリプト（Flask test client・サーバ不要）

```bash
# プロジェクトルートで
python scripts/smoke_test.py --deploy
```

**確認内容**  
- `/tools/seo` → 200、本文に `⚠️ エラーが発生しました` なし  
- `/tools/csv` → 200、同上  
- `/guide/csv` → 200、同上  
- `/tools/minutes` → 301、Location に `/tools` を含む  
- `/guide/minutes` → 301、Location に `/guide` を含む  
- `/tools/pdf/` → 301、Location に `/tools/pdf` を含む  

**実行結果（2026-02-10・feature/add-csv-excel-utility）**: 上記すべてパス。  
`OK: deploy verification (tools/seo, tools/csv, guide/csv=200; minutes 301; /tools/pdf/ 301)`

### 2.2 手元でローカル起動してブラウザで確認する場合

1. **起動**
   ```bash
   flask run
   # または
   python -m flask run
   ```
   デフォルトは http://127.0.0.1:5000

2. **ページ表示**
   - http://127.0.0.1:5000/tools/seo … エラーなく開く
   - http://127.0.0.1:5000/tools/csv … エラーなく開く
   - http://127.0.0.1:5000/guide/csv … 開く
   - http://127.0.0.1:5000/tools/minutes … 301 で /tools へ
   - http://127.0.0.1:5000/guide/minutes … 301 で /guide へ
   - http://127.0.0.1:5000/tools/pdf/ … 301 で /tools/pdf へ

---

## 3. /tools/csv の CDN ロード成功確認（手動）

**手順**  
1. ブラウザで http://127.0.0.1:5000/tools/csv を開く。  
2. **Network タブ**  
   - フィルタを「JS」または「All」に。  
   - 一覧で以下が **200** であること:  
     - cdnjs.cloudflare.com (jszip, papaparse)  
     - cdn.sheetjs.com (xlsx)  
     - cdn.jsdelivr.net (encoding-japanese)  
   - いずれも 4xx/5xx や (failed) でないこと。  
3. **Console タブ**  
   - 未定義エラー（例: `Papa is not defined`, `Encoding is not defined`, `XLSX is not defined`）が出ていないこと。  

**依存が読み込めているか簡単に確認する方法**  
- ページ表示後、Console で次を実行（エラーにならなければ読み込み済み）:
  ```js
  typeof Papa !== 'undefined' && typeof XLSX !== 'undefined' && typeof Encoding !== 'undefined' && typeof JSZip !== 'undefined'
  ```
  → `true` なら主要 CDN は読み込めている。

---

## 4. 「ファイルをサーバに送っていない」確認（手動）

**手順**  
1. http://127.0.0.1:5000/tools/csv を開く。  
2. Network タブを開いた状態で、CSV ファイルを 1 つ選択し「実行」まで行う（列抽出や CSV→XLSX など任意）。  
3. **確認**  
   - 一覧に **POST や PUT で自サイト（origin）へ送っているリクエストが無い**こと。  
   - あるのは通常、初回の HTML 取得・static ファイル・CDN の script のみ。  
   - ファイル選択や実行に伴う「ファイル内容を body に載せたリクエスト」が無いこと。  

**事実（コード）**: 4. の挙動と一致する実装になっている（1.2 のとおり fetch/FormData/upload 未使用）。

**もし送っている挙動があった場合の修正方針**  
- templates/tools/csv.html または static/js/csv-ops.js 内で、ファイル内容を `fetch`/`XMLHttpRequest` の body に載せている箇所を削除する。  
- 処理はすべて FileReader + メモリ内処理 + Blob ダウンロードに限定する（現状の設計どおり）。

---

## 5. 対象ブランチごとの実行

| ブランチ | スクリプト実行 | 備考 |
|----------|----------------|------|
| feature/add-csv-excel-utility | `python scripts/smoke_test.py --deploy` | 上記で実施済み・全パス |
| cleanup/remove-minutes | 同様に実行 | minutes 301 と他ルートが存在する限り同じ期待結果 |
| seo/topicality-phase-b | 同様に実行 | CSV/minutes が含まれていれば同じ観点で確認 |

他ブランチでは `git checkout <branch>` のあと、同じコマンドで再実行すればよい。

---

## 6. 推測・注意事項

- **CDN の可用性**: 本番はユーザー環境から cdnjs / sheetjs / jsdelivr へアクセスするため、ネットワークや CSP でブロックされると script が失敗する。本レポート時点では CSP で script-src を絞っている設定は未確認（設定が無ければ CDN は許可される想定）。  
- **修正が必要な場合**: CDN URL 誤り・CSP ブロック・読み込み順・変数名ミスなどは、該当箇所のみ最小差分で修正し、修正後に `python scripts/smoke_test.py --deploy` および上記 3・4 の手動確認を再度行うことを推奨する。

---

## 7. 変更サマリ（今回の対応）

- **scripts/smoke_test.py**: `--deploy` オプションを追加。  
  - 200: /tools/seo, /tools/csv, /guide/csv  
  - 301: /tools/minutes → /tools, /guide/minutes → /guide, /tools/pdf/ → /tools/pdf  
  - 本文にエラーフレーズが含まれないこと  
- **docs/status-reports/2026-02-10_smoke_test_deploy_verification.md**: 本レポートを追加。

**手動確認手順（再掲）**  
1. `python scripts/smoke_test.py --deploy` で全項目パス。  
2. ローカルで `flask run` → ブラウザで 2.2 の URL を開き、表示と 301 を確認。  
3. /tools/csv で Network の script が 200、Console に未定義エラーなし。  
4. /tools/csv でファイル選択・実行し、自サイトへのファイル送信リクエストが無いことを確認。
