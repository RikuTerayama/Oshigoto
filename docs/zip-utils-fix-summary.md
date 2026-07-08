# ZipUtils is not defined 修正サマリ ＋ PDF埋め込み画像抽出の説明追記

## 1. 修正したファイル一覧

| ファイル | 変更内容 |
|----------|----------|
| `templates/tools/pdf.html` | ① tool-runner.js の直前に zip-utils.js の script タグを追加（既存）。② 「埋め込み画像抽出（試験版）について」の説明ブロックをオプション欄に追加 |
| `templates/tools/image-cleanup.html` | tool-runner.js の直前に zip-utils.js の script タグを追加（既存） |
| `static/js/tool-runner.js` | downloadAllZip 冒頭で ZipUtils 未定義時にユーザー向けメッセージを投げるガード（文言を「ZIP機能の読み込みに失敗しました（zip-utils.js）。ページを再読み込みしてください。」に統一） |

---

## 2. 変更差分（script 追加箇所）

### templates/tools/pdf.html

**追加位置**: 「共通ライブラリ」ブロック内、`file-utils.js` の次・`tool-runner.js` の前

```diff
     <!-- 共通ライブラリ -->
     <script src="{{ url_for('static', filename='js/file-validation.js') }}"></script>
     <script src="{{ url_for('static', filename='js/file-utils.js') }}"></script>
+    <script src="{{ url_for('static', filename='js/zip-utils.js') }}"></script>
     <script src="{{ url_for('static', filename='js/tool-runner.js') }}"></script>
```

### templates/tools/image-cleanup.html

**追加位置**: 同上（共通ライブラリブロック、file-utils.js の次・tool-runner.js の前）

```diff
     <!-- 共通ライブラリ -->
     <script src="{{ url_for('static', filename='js/file-validation.js') }}"></script>
     <script src="{{ url_for('static', filename='js/file-utils.js') }}"></script>
+    <script src="{{ url_for('static', filename='js/zip-utils.js') }}"></script>
     <script src="{{ url_for('static', filename='js/tool-runner.js') }}"></script>
```

**読み込み順（3ツール共通）**: JSZip CDN → file-validation.js → file-utils.js → **zip-utils.js** → tool-runner.js → 各ツール固有JS

---

## 2.1 PDFツール: 埋め込み画像抽出の説明ブロック（pdf.html）

**追加位置**: `id="extract-images-options"` の option-group 内、先頭（ラベル・フォームの前）

- 見出し「埋め込み画像抽出（試験版）について」と箇条書きを、既存の `.info-text` スタイルに合わせた枠（左ボーダー・薄い青背景）で追加。
- 内容: PDF内画像の取り出し説明、試験版の注意、うまく抽出できないケース（ベクター中心・保護PDF・ページ数多）、ZIP一括ダウンロードの案内。

```diff
             <!-- v2: 埋め込み画像抽出オプション -->
             <div id="extract-images-options" class="option-group" style="display: none;">
+                <div class="info-text" style="margin-bottom: 15px; padding: 12px; background: rgba(74, 158, 255, 0.08); border-radius: 8px; border-left: 3px solid rgba(74, 158, 255, 0.5);">
+                    <strong>埋め込み画像抽出（試験版）について</strong>
+                    <ul style="margin: 10px 0 0 0; padding-left: 20px; line-height: 1.6;">
+                        <li>PDFの中に含まれる画像を取り出し、画像ファイルとして保存します。</li>
+                        <li>PDFの種類によっては「画像だけ」ではなく「ページ全体を画像として保存」する形になることがあります（試験版）。</li>
+                        <li>うまく抽出できない主なケース: （図形/ベクター中心、保護PDF、ページ数多いPDF）</li>
+                        <li>複数の画像が出力された場合は「ZIPで一括ダウンロード」でまとめて保存できます。</li>
+                    </ul>
+                </div>
                 <label>画像形式</label>
```

---

## 3. tool-runner.js のガード差分

**ファイル**: `static/js/tool-runner.js`  
**箇所**: `downloadAllZip` メソッドの冒頭（outputs.length チェックの直後）

```diff
     async downloadAllZip(zipName = 'output.zip') {
         if (this.outputs.length === 0) {
             throw new Error('ダウンロード可能なファイルがありません');
         }
+        if (typeof ZipUtils === 'undefined') {
+            throw new Error('ZIP機能の読み込みに失敗しました（zip-utils.js）。ページを再読み込みしてください。');
+        }
+
         try {
             const zipBlob = await ZipUtils.createZip(
```

---

## 4. 参照箇所の網羅チェック結果

| テンプレート | downloadAllZip の呼び出し | tool-runner.js 読み込み | zip-utils.js 読み込み（修正後） |
|--------------|---------------------------|-------------------------|----------------------------------|
| templates/tools/pdf.html | あり（pdf-tools-output.zip） | あり | ✅ 追加済み |
| templates/tools/image-cleanup.html | あり（image-cleanup-output.zip） | あり | ✅ 追加済み |
| templates/tools/image-batch.html | あり（converted_images.zip） | あり | もともとあり |

→ downloadAllZip を使う全ページで zip-utils.js が読み込まれる状態になった。

---

## 5. テスト結果メモ（ローカル）

- **確認日**: 2026-02-05
- **方法**: Flask test_client で各ツールページを GET。レスポンスに `zip-utils.js` と `tool-runner.js` が含まれることを確認。

| URL | ステータス | zip-utils.js 含む | tool-runner.js 含む |
|-----|------------|-------------------|---------------------|
| /tools/pdf | 200 | ✅ | ✅ |
| /tools/image-cleanup | 200 | ✅ | ✅ |
| /tools/image-batch | 200 | ✅ | ✅ |

- **手動確認（推奨）**:
  - PDFツール: 埋め込み画像抽出で複数出力 → 「ZIPで一括ダウンロード」でZIPがダウンロードされること、Console に `ZipUtils is not defined` が出ないこと。ツール選択で「埋め込み画像抽出（試験版）」を選んだときに説明ブロックが表示されること。
  - 画像クリーンアップ: 複数ファイル処理 → 同様にZIP一括ダウンロードが動作すること。
  - 画像一括変換: 従来どおりZIP一括ダウンロードが動作すること（リグレッションなし）。
