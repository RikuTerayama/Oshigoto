# Google Analytics / Search Console 現状監査レポート

**作成日**: 2026-02-03  
**対象サイト**: https://jobcan-automation.onrender.com/  
**監査目的**: GA4/GSCトラッキングの現状確認と環境変数対応への移行

---

## 1. 現状サマリー

### Google Analytics 4 (GA4)

**ステータス**: ✅ **既に実装済み**

**実装箇所**:
- `templates/includes/head_meta.html` (1-10行目)

**測定ID**: `G-D91LLNQ7ZL` (ハードコード)

**実装内容**:
```html
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-D91LLNQ7ZL"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-D91LLNQ7ZL');
</script>
```

**問題点**:
- 測定IDがハードコードされており、環境変数で出し分けできない
- ローカル環境でも本番と同じIDで計測されてしまう
- `anonymize_ip: true` が設定されていない（プライバシー配慮不足）

**影響範囲**:
- 全ページ（`templates/includes/head_meta.html` を include している全テンプレート）
- 確認済み: `/`, `/autofill`, `/tools/*`, `/guide/*` など全25ページ以上

---

### Google Search Console (GSC)

**ステータス**: ✅ **既に実装済み（メタタグ方式）**

**実装箇所**:
- `templates/includes/head_meta.html` (18行目)

**検証文字列**: `bQuTb9pABqynDmXqfDdakvmFSqz8y8MyYnOExuucmnA` (ハードコード)

**実装内容**:
```html
<meta name="google-site-verification" content="bQuTb9pABqynDdakvmFSqz8y8MyYnOExuucmnA" />
```

**問題点**:
- 検証文字列がハードコードされており、環境変数で出し分けできない
- 複数環境（本番/ステージング）で異なる検証文字列を使えない

**影響範囲**:
- 全ページ（`templates/includes/head_meta.html` を include している全テンプレート）

---

### 共通HEAD挿入点

**ファイル**: `templates/includes/head_meta.html`

**使用状況**:
- 全ページで `{% include 'includes/head_meta.html' %}` を使用
- 確認済みテンプレート:
  - `templates/landing.html`
  - `templates/autofill.html`
  - `templates/tools/*.html` (6ファイル)
  - `templates/guide/*.html` (8ファイル以上)
  - その他多数

**結論**: このファイルを修正すれば全ページに反映される

---

### robots.txt

**ステータス**: ✅ **存在**

**場所**: `static/robots.txt`

**配信URL**: `/robots.txt`

**ルート定義**: `app.py:1037-1041`
```python
@app.route('/robots.txt')
def robots_txt():
    """robots.txt を配信"""
    try:
        return send_file('static/robots.txt', mimetype='text/plain')
```

---

### sitemap.xml

**ステータス**: ✅ **存在（動的生成）**

**配信URL**: `/sitemap.xml`

**ルート定義**: `app.py:1055-1118`
- 動的にXMLを生成
- URLリスト、changefreq、priority、lastmodを含む

---

## 2. 追加実装の方針

### 2.1 GA4の環境変数対応

**変更ファイル**: 
- `app.py` (context_processor)
- `templates/includes/head_meta.html`

**実装内容**:
1. `app.py` の `inject_env_vars()` に `GA_MEASUREMENT_ID` を追加
2. `head_meta.html` で環境変数が設定されている場合のみ gtag を出力
3. `anonymize_ip: true` を追加（プライバシー配慮）
4. イベント計測を追加（tool_run_start, tool_download, autofill_start など）

**環境変数**:
- `GA_MEASUREMENT_ID`: GA4の測定ID（例: `G-D91LLNQ7ZL`）

**動作**:
- 環境変数が設定されている場合: gtag を出力
- 環境変数が未設定の場合: gtag を出力しない（ローカル開発時）

---

### 2.2 GSC検証の環境変数対応

**変更ファイル**:
- `app.py` (context_processor)
- `templates/includes/head_meta.html`

**実装内容**:
1. `app.py` の `inject_env_vars()` に `GSC_VERIFICATION_CONTENT` を追加
2. `head_meta.html` で環境変数が設定されている場合のみメタタグを出力

**環境変数**:
- `GSC_VERIFICATION_CONTENT`: GSC検証文字列（例: `bQuTb9pABqynDdakvmFSqz8y8MyYnOExuucmnA`）

**動作**:
- 環境変数が設定されている場合: メタタグを出力
- 環境変数が未設定の場合: メタタグを出力しない

---

### 2.3 イベント計測の追加

**対象イベント**:
1. **Tool実行開始**: `tool_run_start`
   - パラメータ: `tool_id` (例: `image-batch`, `pdf`)
   - 実装箇所: 各ツールの実行ボタンクリック時

2. **生成物ダウンロード**: `tool_download`
   - パラメータ: `tool_id`, `file_type` (例: `zip`, `png`)
   - 実装箇所: ダウンロードボタンクリック時

3. **AutoFill処理開始**: `autofill_start`
   - パラメータ: なし
   - 実装箇所: `/upload` エンドポイント呼び出し時

4. **AutoFill処理成功**: `autofill_success`
   - パラメータ: なし
   - 実装箇所: 処理完了時

5. **AutoFill処理エラー**: `autofill_error`
   - パラメータ: `error_type` (任意)
   - 実装箇所: エラー発生時

**実装方針**:
- `window.gtag` が存在する場合のみイベント送信（未設定環境でエラーにならない）
- 既存JS（`tool-runner.js`, 各ツールJS）に薄くイベント送信を差し込む

---

## 3. 影響範囲

### 修正が必要なファイル

1. **`app.py`**
   - `inject_env_vars()` 関数に環境変数を追加

2. **`templates/includes/head_meta.html`**
   - GA4 gtag を環境変数対応に変更
   - GSC検証メタタグを環境変数対応に変更

3. **JavaScriptファイル（イベント計測追加）**
   - `static/js/tool-runner.js` (tool_run_start, tool_download)
   - `templates/autofill.html` 内のJS (autofill_start, autofill_success, autofill_error)
   - 各ツールページのJS（必要に応じて）

### 影響を受けるページ

- **全ページ**: `head_meta.html` を include しているため、全ページに影響
- 主要ページ:
  - `/` (landing.html)
  - `/autofill` (autofill.html)
  - `/tools` (tools/index.html)
  - `/tools/*` (各ツールページ)
  - `/guide/*` (各ガイドページ)

---

## 4. 実装後の確認項目

### ローカル環境での確認

1. **環境変数未設定時**:
   - gtag が出力されないこと
   - GSC検証メタタグが出力されないこと
   - JSエラーが発生しないこと

2. **環境変数設定時**:
   - gtag が正しく出力されること
   - GSC検証メタタグが正しく出力されること
   - イベント送信が動作すること（DevToolsで確認）

### 本番環境での確認

1. **GA4**:
   - リアルタイムレポートでアクセスが記録されること
   - イベントが正しく送信されること

2. **GSC**:
   - Search Consoleでサイト所有権が確認できること

---

## 5. 環境変数一覧

### 追加する環境変数

| 変数名 | 説明 | 例 | 必須 |
|--------|------|-----|------|
| `GA_MEASUREMENT_ID` | GA4の測定ID | `G-D91LLNQ7ZL` | 任意 |
| `GSC_VERIFICATION_CONTENT` | GSC検証文字列 | `bQuTb9pABqynDdakvmFSqz8y8MyYnOExuucmnA` | 任意 |

**注意**: 両方とも任意（未設定でも動作する）

---

## 6. 既存実装との互換性

### 現在のハードコード値

- GA4測定ID: `G-D91LLNQ7ZL`
- GSC検証文字列: `bQuTb9pABqynDdakvmFSqz8y8MyYnOExuucmnA`

### 移行方針

- 環境変数が未設定の場合、既存のハードコード値を使用する（後方互換性）
- または、環境変数のみを使用し、ハードコード値を削除（推奨）

**推奨**: 環境変数のみを使用（本番環境で環境変数を設定する前提）

---

## 7. 次のステップ

1. ✅ 現状監査完了（本レポート）
2. ⏳ GA4の環境変数対応実装
3. ⏳ GSC検証の環境変数対応実装
4. ⏳ イベント計測の追加
5. ⏳ 動作確認
6. ⏳ コミット・プッシュ
