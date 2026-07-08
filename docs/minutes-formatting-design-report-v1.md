# ③ 議事録整形サービス 現状分析・設計レポート v1

---

## 1. 目的とゴール（MVP / 将来）

### 目的
「議事録整形」を**会議の音声文字起こしから、構造化されたきれいな議事録を作成するサービス**へ転換するための現状把握とMVP設計。

### MVP（本レポートの対象）
- **入力**: 文字起こし済みテキスト（貼り付け、または .txt / .md のアップロード）
- **処理**: テキストを構造化し、見出し・箇条書き・決定事項・ToDo 等の形式で整形
- **出力**: 画面表示、コピー、.md / .txt ダウンロード
- **音声アップロード → 文字起こし**: 対象外（次フェーズ）

### 将来（拡張案）
- 音声ファイルアップロード → 文字起こしAPI連携 → 文字起こしテキスト → 本MVPの整形パイプラインに投入
- .docx 出力
- 多言語（日本語/英語）の明示対応、話者ラベル（Speaker1/名前）の保持・整理

---

## 2. 現状のコード構造（ルート、テンプレ、共通JS、既存パターン）

### 2.1 Flask ルーティング

| パス | 定義箇所 | 処理 |
|------|----------|------|
| `/tools` | `app.py` 約804行 | `tools_index()` → `templates/tools/index.html`、`PRODUCTS` を渡してツール一覧表示 |
| `/tools/minutes` | `app.py` 約776–783行 | `tools_minutes()` → `get_product_by_path('/tools/minutes')`、`related_products` を取得し `templates/tools/minutes.html` をレンダリング |

**抜粋（app.py 776–783行付近）**
```python
@app.route('/tools/minutes')
def tools_minutes():
    """議事録整形ツール"""
    from lib.routes import get_product_by_path, get_available_products
    product = get_product_by_path('/tools/minutes')
    available_products = get_available_products()
    related_products = [p for p in available_products if p['id'] != 'minutes' and p.get('status') == 'available'][:4]
    return render_template('tools/minutes.html', product=product, related_products=related_products)
```

- ツール一覧の元データは **`lib/products_catalog.PRODUCTS`**。`lib.routes.get_product_by_path` / `get_available_products` がこれを参照。

### 2.2 テンプレート構成

- **ツール共通**: `templates/includes/header.html`, `footer.html`, `breadcrumb.html`, `related_tools.html`
- **ツールページ**: `templates/tools/*.html`（index, pdf, image-batch, image-cleanup, **minutes**, seo）
- **議事録**: `templates/tools/minutes.html` のみ。**tool-runner.js は使っていない**（単一テキスト入力＋即時整形のため、画像/PDFツールと異なるパターン）。

### 2.3 議事録ツールの既存UI/JSパターン

- **レイアウト**: 3カラム（入力 | 編集 | 出力）
- **入力**: 
  - `<textarea id="raw-text">`（原文）
  - `<input type="file" id="file-input" accept="text/plain">`（.txt 読み込み）
  - 「サンプル入力」ボタン（`loadSampleText()`）
  - 最大文字数 200,000（クライアントで制限）
- **オプション**: テンプレート選択（決定事項とToDo分解 / 上司向け報告書 / インシデント用）、メタ（タイトル・日付・参加者・作成者）、インシデント時は重要度・影響システム
- **実行**: 「抽出して整形」→ `extractAndFormat()`（同期的にクライアントで実行）
- **編集**: 抽出された決定事項・ToDoをカードで表示し、編集・削除・追加可能。再抽出で上書き。
- **出力**: 
  - `#output-preview` に Markdown を表示
  - 「Markdownをコピー」「Markdownをダウンロード」「ToDo CSV」「ToDo JSON」ボタン

### 2.4 既存の変換ロジック（すべてクライアント）

- **minutes-parse.js**: `MinutesParse.normalizeText(raw)`, `splitLines(text)` — 改行統一・行分割
- **minutes-normalize.js**: 行の正規化（MinutesNormalize）
- **minutes-extract.js**: `MinutesExtract.extractCandidates(lines, baseDate)` → `{ decisions, actions }`。キーワード・正規表現で決定事項・ToDo候補を抽出（ルールベース）
- **minutes-templates.js**: `MinutesTemplates.renderActionTemplate` / `renderReportTemplate` / `renderIncidentTemplate` — メタ・決定事項・ToDo から Markdown 文字列を生成
- **minutes-export.js**, **minutes-export-v2.js**: コピー、Markdown/CSV/JSON ダウンロード

**読み込み順（minutes.html 368–376行付近）**
```html
<script src=".../file-validation.js"></script>
<script src=".../file-utils.js"></script>
<script src=".../minutes-parse.js"></script>
<script src=".../minutes-normalize.js"></script>
<script src=".../minutes-date.js"></script>
<script src=".../minutes-extract.js"></script>
<script src=".../minutes-templates.js"></script>
<script src=".../minutes-export.js"></script>
<script src=".../minutes-export-v2.js"></script>
```

### 2.5 LLM / 外部API の有無

- **調査結果**: リポジトリ内に **openai / OPENAI / llm / API_KEY 等の参照はなし**（`grep` で確認）。
- **requirements.txt**: Flask, openpyxl, playwright, jpholiday, psutil, gunicorn のみ。**LLM用ライブラリは未導入**。
- **結論**: 現状は**すべてブラウザ内のルールベース処理**。LLM を導入する場合は**新規にサーバ側API（Flask ルート）を設け、APIキーは環境変数で管理**する形になる。

### 2.6 既存ツールの入力形態（参考）

| ツール | 入力 | 出力 | 共通JS |
|--------|------|------|--------|
| image-batch | ファイル複数（画像） | 画像ZIP | tool-runner.js, zip-utils.js |
| pdf | ファイル複数（PDF） | PDF/画像/ZIP | tool-runner.js, zip-utils.js |
| image-cleanup | ファイル複数（画像） | 画像ZIP | tool-runner.js, zip-utils.js |
| **minutes** | **textarea + ファイル(.txt)** | **Markdown/CSV/JSON** | **tool-runner なし** |
| seo | textarea / URL / フォーム | HTML/OGP/sitemap等 | なし（各機能で個別script） |

---

## 3. MVP機能要件（入力 / オプション / 出力）

### 3.1 入力

| 項目 | 内容 |
|------|------|
| 主入力 | 文字起こしテキスト（貼り付け、または .txt / .md アップロード） |
| 制約 | 最大文字数は現状 200,000。MVP で LLM を使う場合はサーバ負荷・コストのため 50,000 等の上限を検討 |
| 既存 | textarea `#raw-text`、`#file-input` accept="text/plain" — .md は未対応のため `accept=".txt,.md"` や `accept="text/plain,text/markdown"` への拡張を推奨 |

### 3.2 オプション（MVPで検討する項目）

| オプション | 説明 | 既存との対応 |
|------------|------|--------------|
| 言語 | 日本語 / 英語（プロンプトやラベルに反映） | 現状なし。LLM 導入時に有効 |
| 形式テンプレ | サマリ、議題、決定事項、ToDo、担当、期限、未決、リスク、次回 等のセクション構成 | 既存は「決定事項とToDo分解」「上司向け報告書」「インシデント用」の3種。項目の追加・名前の揃えで対応可能 |
| 話者ラベル | ある/なし、Speaker1 形式、名前あり（保持・正規化） | 現状なし。ルールベースでは「Speaker1:」等の行頭パターンで分割可能。LLM なら「話者を維持して整形」を指示可能 |
| 粒度 | 短め / 標準 / 詳細（要約の長さ、項目数） | 現状なし。LLM のプロンプトで制御可能 |

### 3.3 出力

| 項目 | 内容 |
|------|------|
| 画面表示 | 構造化された議事録（Markdown をそのまま表示、既存の `#output-preview` と同様で可） |
| コピー | クリップボードに Markdown をコピー（既存の「Markdownをコピー」と同様） |
| ダウンロード | .md および .txt でダウンロード（既存は .md。.txt は同一内容を `text/plain` で出すだけでも可） |
| 将来 | .docx 出力（拡張案。サーバ側で python-docx 等を使用する想定） |

---

## 4. 画面フロー（ユーザー操作の流れ）

1. `/tools/minutes` を開く
2. **入力**: 文字起こしテキストを貼り付ける、または .txt / .md を選択して読み込む。任意で「サンプル入力」を挿入
3. **オプション**: テンプレート（形式）、言語・話者・粒度（MVP で追加する場合）を選択。メタ（タイトル・日付・参加者・作成者）を入力
4. **実行**: 「抽出して整形」（または「構造化して整形」等の文言）をクリック
5. **進捗**: LLM を使う場合は「処理中…」等の表示。ルールベースのままなら現状どおり即時
6. **編集**: 抽出された決定事項・ToDo 等を編集（既存の中央パネルと同様）
7. **出力**: 右パネルでプレビュー確認 → 「コピー」「.md ダウンロード」「.txt ダウンロード」等で利用

---

## 5. 技術設計案

### 5.1 フロント構成（どこに何を置くか）

| 役割 | 配置 | 備考 |
|------|------|------|
| ページ | `templates/tools/minutes.html` | 既存を拡張。入力/オプション/出力のラベル・文言を「議事録整形・文字起こしテキストから構造化」に寄せる |
| クライアント整形（ルールベース） | 既存の `static/js/minutes-*.js` | そのまま利用可能。話者ラベルや .md 読み込みは既存JSの拡張で対応可能 |
| サーバAPI（LLM を使う場合） | 新規 `app.py` にルート追加（例: `POST /api/minutes/format`） | リクエスト body にテキスト＋オプション、レスポンスに構造化テキスト or JSON（決定事項・ToDo 等） |
| 新規JS（LLM 連携時） | 例: `static/js/minutes-api.js` | `fetch` で上記 API を呼び、返却を既存の state（decisions, actions）に流し込む |

### 5.2 サーバAPI設計（LLM を使う場合の案）

- **エンドポイント**: `POST /api/minutes/format`（要 CSRF 対策または Same-Origin のみ）
- **リクエスト例**:
```json
{
  "text": "文字起こしテキスト...",
  "options": {
    "language": "ja",
    "template": "standard",
    "speaker_mode": "keep",
    "granularity": "standard"
  }
}
```
- **レスポンス例（構造化テキストを返す場合）**:
```json
{
  "success": true,
  "markdown": "# 議事録\n\n## サマリ\n...",
  "decisions": [{"text": "..."}],
  "actions": [{"title": "...", "owner": "...", "dueRaw": "..."}]
}
```
- **エラー時**: `success: false`, `error` メッセージ。トークン超過・レート制限時は 429 や専用メッセージを返す想定。

### 5.3 変換ロジック（チャンク、プロンプト、整形ルール）

#### LLM を使う場合

- **実行場所**: **必ずサーバ側**。ブラウザ直呼びは API キー露出・CORS のため不可。Flask のルート内で OpenAI / 他プロバイダの SDK を呼ぶ。
- **チャンク分割**: モデルのコンテキスト長を超える長文は、段落や「Speaker」区切りで分割し、先頭チャンクで「議題・サマリ」、後続で「決定事項・ToDo」等を抽出。最後にマージして一つの Markdown にまとめる。
- **トークン上限**: 1リクエストあたりの最大文字数（例: 50,000 文字）、最大チャンク数（例: 5）を設け、超過時は「テキストが長すぎます」等でエラーまたは先頭 N 文字のみ処理とする。
- **プロンプト**: システムプロンプトで「文字起こしテキストを、見出し・サマリ・議題・決定事項・ToDo・担当・期限・未決・リスク・次回の予定 に整理した Markdown で出力する」等を指定。話者ラベルを維持するかはオプションで指示。
- **整形ルール**: 出力は Markdown（見出し ##、箇条書き -、番号リスト 1. 等）。表は必須にしない（LLM の安定性のため、まずはリスト中心）。
- **エラー・リトライ**: API の一時エラーは指数バックオフで 1〜2 回リトライ。部分結果（先頭チャンクのみ成功）は「一部のみ整形しました」と明示して返すか、エラーに含めて返すかを方針化する。

#### LLM を使わない場合（ルールベースのまま）

- **限界**: キーワード・正規表現では「決定」「ToDo」等の明示表現に強く依存する。話者名の正規化・曖昧な表現の解釈は難しい。
- **MVP で可能な拡張**: 話者行の検出（`Speaker1:`、`山田:` 等）で発言ブロックに分割し、各ブロックを既存の決定事項/ToDo 抽出に渡す。形式テンプレの項目を増やし（未決・リスク・次回等）、既存テンプレートを拡張する。

---

## 6. エッジケースと対策

| エッジケース | 対策 |
|--------------|------|
| 長文 | 文字数上限を設け、超過時は先頭 N 文字のみ処理するかエラー。LLM の場合はチャンク分割＋マージ |
| 話者混在（名前・Speaker1・なし） | オプションで「話者を維持」「話者を除去」を選択可能に。正規表現で行頭の「名前:」「Speaker N:」を検出してブロック化 |
| ノイズ（誤変換・余計な発言） | ルールベースでは除去が困難。LLM のプロンプトで「不要な相槌・言いよどみは省略」等を指示 |
| 箇条書き崩れ（改行だらけ） | 既存の `MinutesParse.normalizeText` で連続空白・空行を整理。LLM 出力はプロンプトで「不要な空行を入れない」と指定 |
| API 失敗・タイムアウト | サーバでリトライ。フロントでは「しばらく待って再実行」メッセージと、可能ならルールベースフォールバックを案内 |
| 機密入力 | 注意書きと同意UI（後述）。サーバではログに原文を残さない |

---

## 7. 受け入れ条件（DoD）

- [ ] 文字起こしテキストを貼り付けまたは .txt / .md で読み込め、既存と同様に「抽出して整形」で構造化される（ルールベースでもLLMでも、どちらかで達成）
- [ ] 出力が画面に表示され、コピーおよび .md（および .txt）ダウンロードができる
- [ ] 既存の決定事項・ToDo の編集・再抽出・CSV/JSON 出力が引き続き動作する
- [ ] （LLM 導入時）文字数上限・エラー時にユーザーに分かるメッセージが表示される
- [ ] 入力エリア付近に「機密情報に注意」等の注意書きと、外部API送信時の同意（LLM 利用時）が表示される
- [ ] 製品カタログ・ガイドの文言が「会議の文字起こしから構造化された議事録を作成」に沿って更新されている（任意だが推奨）

---

## 8. 次ステップ（実装用 Cursor プロンプト案を短く1つ）

```
【依頼】議事録整形ツールを「会議の文字起こしテキストから構造化された議事録を作成する」MVP に合わせて整える。
- 入力: 既存の textarea + ファイル（.txt）に加え、.md を accept に含める。
- オプション: 既存テンプレートを維持しつつ、形式テンプレに「サマリ・議題・決定事項・ToDo・担当・期限・未決・リスク・次回」を明示した選択肢を追加する。話者ラベル（ある/なし・Speaker1形式）のオプションを1つ追加する。
- 出力: 既存の Markdown 表示・コピー・ダウンロードに加え、.txt でダウンロードするボタンを追加する。
- 変換ロジック: まずは既存のルールベース（minutes-extract.js 等）のままとする。話者行の検出（行頭の「名前:」「Speaker N:」）でブロック分割する処理を minutes-parse.js に追加し、既存の extractCandidates に渡す。
- UI: ページ説明を「会議の音声文字起こしテキストを貼り付けると、構造化された議事録に整形します」に変更。入力エリア上に「機密情報が含まれる場合は取り扱いにご注意ください。処理はブラウザ内で完結し、サーバーに送信されません。」の注意書きを表示する。
- 将来の LLM 対応を見据え、docs/minutes-formatting-design-report-v1.md の「5.2 サーバAPI設計」を参照し、POST /api/minutes/format のエンドポイント案とリクエスト/レスポンス形だけ stub で残しておく（実装はしなくてよい）。
```

---

## 付録: 参考になる既存ツールの実装箇所（ファイルパスと短い抜粋）

### ルーティング・製品一覧

- **app.py**（776–783行）: `/tools/minutes` のルートと `minutes.html` レンダリング
- **lib/products_catalog.py**（155–191行）: `id: 'minutes'` の製品定義（name, description, path, capabilities, constraints 等）

### 議事録ツールの入力・実行・出力

- **templates/tools/minutes.html**（303–312行）: ファイル入力・サンプルボタン・textarea・「抽出して整形」ボタン
```html
<input type="file" id="file-input" accept="text/plain" ...>
<button ... onclick="loadSampleText()">サンプル入力</button>
<textarea id="raw-text" placeholder="議事録の原文を貼り付けてください"></textarea>
<button id="extract-button" ... onclick="extractAndFormat()">抽出して整形</button>
```

- **templates/tools/minutes.html**（452–499行）: `extractAndFormat()` — 原文取得、メタ取得、MinutesParse / MinutesExtract 呼び出し、state 更新、編集パネル・出力再生成
- **templates/tools/minutes.html**（349–360行）: 出力プレビューとコピー・Markdown/CSV/JSON ダウンロードボタン
- **templates/tools/minutes.html**（775–794行）: `copyOutput()`, `downloadOutput()` — コピーと Markdown ダウンロード

### ルールベース抽出

- **static/js/minutes-extract.js**（1–70行付近）: `MinutesExtract.extractDecisions(lines)`, `extractActions(lines)` — キーワード・正規表現で決定事項・ToDo を抽出
- **static/js/minutes-parse.js**（10–32行）: `MinutesParse.normalizeText(raw)`, `splitLines(text)` — 改行統一・行分割

### 他ツールのファイル入力（.txt 以外の例）

- **templates/tools/pdf.html**（330行付近）: `<input type="file" id="file-input" accept="application/pdf" multiple ...>` — PDF ツールのファイル入力
- **templates/tools/minutes.html**（407–429行）: `setupFileInput()` — `file.text()` で読み込み、textarea にセット。最大文字数チェックあり

### ツール一覧の出し方

- **app.py**（804–805行）: `/tools` で `tools_index()` が `templates/tools/index.html` に `products` を渡す
- **lib/products_catalog.PRODUCTS**: 全ツールの定義。ここに `minutes` が含まれるため、一覧に表示される
