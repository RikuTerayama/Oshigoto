# 議事録整形 MVP 実装サマリ（③）

## 1. 修正したファイル一覧

| ファイル | 変更内容 |
|----------|----------|
| `templates/tools/minutes.html` | UI文言、テンプレート表示名・標準（サマリ付き）追加、ファイル accept(.txt/.md)、話者ラベル選択、注意書きブロック、実行ボタン「構造化して整形」、.txt ダウンロードボタン、extractAndFormat で話者除去オプション適用、regenerateOutput で standard-summary 対応、downloadOutputTxt 追加 |
| `static/js/minutes-parse.js` | `stripSpeakerLabels(text)` を追加（行頭の Speaker1:/名前: 等を除去） |
| `static/js/minutes-templates.js` | `renderStandardWithSummary(meta, decisions, actions, rawText)` を追加（サマリ欄プレースホルダ付き） |
| `static/js/minutes-export.js` | `downloadTxt(text, filenameBase)` を追加（text/plain, .txt） |
| `app.py` | `POST /api/minutes/format` を追加（501 + `{ success: false, error: "Not implemented" }`） |
| `lib/products_catalog.py` | minutes の description / capabilities / features を「文字起こしから構造化議事録」に合わせて更新 |

---

## 2. 主な差分（該当箇所）

### 2.1 templates/tools/minutes.html

- **ページ説明**: 「要約ではなく成果物フォーマットへ…」→「会議の文字起こしテキストを貼り付けると、決定事項とToDoを中心に議事録として整形します。処理はブラウザ内で完結し、テキストはサーバーに送信されません。」
- **テンプレート select**: 表示名を「決定事項とToDo（標準）」「上司向けサマリ（報告用）」「インシデント報告（障害用）」に変更し、`<option value="standard-summary">標準（サマリ付き）</option>` を追加。
- **話者ラベル**: `<select id="speaker-labels">` を追加（維持 / 除去）。
- **注意書き**: 入力エリア上に「機密情報が含まれる場合は…」「現在の整形処理はブラウザ内で完結し…」の1ブロックを追加。
- **ファイル入力**: `accept="text/plain"` → `accept=".txt,.md,text/plain,text/markdown"`。
- **textarea placeholder**: 「文字起こしテキストを貼り付けてください（例: Speaker1: では始めます）」。
- **実行ボタン**: 「抽出して整形」→「構造化して整形」。
- **出力**: 「テキスト(.txt)をダウンロード」ボタンと `downloadOutputTxt()` を追加。
- **extractAndFormat()**: `speaker-labels` が「除去」のとき `MinutesParse.stripSpeakerLabels(textForExtract)` を適用してから正規化・行分割。
- **regenerateOutput()**: `state.templateId === 'standard-summary'` のとき `MinutesTemplates.renderStandardWithSummary(...)` を呼ぶ。
- **updateTemplateOptions()**: `templateId === 'standard-summary'` のときも共通メタを表示。

### 2.2 static/js/minutes-parse.js

- **stripSpeakerLabels(text)** を先頭に追加:
  - 行ごとに処理。行頭の `Speaker 1:`, `Speaker1:`, `S1:` 等は正規で除去。
  - 行頭の `名前:` 形式は、`http:`, `https:`, `mailto:` 以外を除去（行頭限定で `http:` を壊さない）。

### 2.3 static/js/minutes-templates.js

- **renderStandardWithSummary(meta, decisions, actions, rawText)** を追加:
  - 見出し・日付・参加者・作成者 → 「サマリ」セクションに「（必要に応じて追記）」→ 決定事項 → ToDo 表。既存の action テンプレに近いがサマリ欄あり。

### 2.4 static/js/minutes-export.js

- **downloadTxt(text, filenameBase)** を追加:
  - `Blob([text], { type: 'text/plain;charset=utf-8' })`、ファイル名 `${filenameBase}_YYYYMMDD.txt`、`FileUtils.downloadBlob` でダウンロード。

### 2.5 app.py

- **POST /api/minutes/format** を追加:
  - `return jsonify(success=False, error='Not implemented'), 501`。リクエスト body は未使用（スタブのため）。

### 2.6 lib/products_catalog.py

- **minutes**: `description` を「会議の文字起こしテキストから、決定事項・ToDoを中心に構造化された議事録を作成。.md/.txt/CSV/JSON出力。ブラウザ内処理でサーバーに送信しません。」に変更。
- **capabilities**: 文字起こし・話者ラベル・Markdown/テキスト出力を明記。
- **features**: 「話者ラベル除去」を追加。

---

## 3. 手動テスト結果メモ

### 環境
- ローカル: `python app.py`、http://127.0.0.1:5000/tools/minutes

### 確認項目

| 項目 | 結果 |
|------|------|
| /tools/minutes が表示できる | ✅ 200 |
| .txt を読み込める | （手動）ファイル選択で .txt を選ぶと textarea に反映される想定。accept に .txt, text/plain を追加済み |
| .md を読み込める | （手動）同様に .md を選択可能。accept に .md, text/markdown を追加済み |
| 話者ラベル「維持」 | （手動）そのまま抽出。従来どおり |
| 話者ラベル「除去」 | （手動）「Speaker1: では始めます」等の行頭ラベルが除去され、本文のみで抽出される想定。stripSpeakerLabels が行頭のみ処理するため、本文の "http:" は影響を受けない |
| 出力表示・コピー・.md ダウンロード | （手動）既存どおり動作する想定 |
| .txt ダウンロード | （手動）「テキスト(.txt)をダウンロード」で同一内容が minutes_YYYYMMDD.txt で保存される想定 |
| ToDo CSV / JSON | （手動）既存ボタンで変更なし。リグレッションなしの想定 |
| テンプレ「標準（サマリ付き）」 | （手動）選択するとサマリ欄に「（必要に応じて追記）」が入った議事録が出力される想定 |
| POST /api/minutes/format | ✅ 501、`{ "success": false, "error": "Not implemented" }` を確認済み（test_client） |

### サンプル文字起こしで試す場合（手動推奨）

1. **話者維持**: 例として「Speaker1: では定例会議を始めます。Speaker2: 決定事項は予算案の承認です。」を貼り付け → 構造化して整形 → 決定事項に「予算案の承認」等が抽出されることを確認。
2. **話者除去**: 同じテキストで話者ラベルを「除去」にし、再実行 → 行頭の "Speaker1:", "Speaker2:" が除かれた状態で抽出されることを確認（出力の見た目は「維持」とほぼ同じだが、抽出入力がラベルなしになる）。

---

## 4. 注意

- 注意書きは「現在の整形処理はブラウザ内で完結し、入力テキストはサーバーに送信されません」としている。将来 LLM 連携を入れる場合は、このブロックの文言を「API に送信する場合は…」等に変更する想定。
- `/api/minutes/format` はスタブのため、リクエストの検証やログは行っていない。実装時に `request.get_json()` で `text` / `options` を受け取り、レート制限・文字数上限等を追加する想定。
