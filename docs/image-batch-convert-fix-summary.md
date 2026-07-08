# 画像一括変換（ImageBatchConvert is not defined）修正サマリ

## 1. 変更したファイル一覧

| ファイル | 変更内容 |
|----------|----------|
| `static/js/image-batch-convert.js` | 末尾に `window.ImageBatchConvert` の明示代入と `console.debug` を追加 |
| `templates/tools/image-batch.html` | `runConversion()` 先頭に ImageBatchConvert / ImageConverter の読み込みガードを追加（alert + return） |

---

## 2. 各ファイルの差分

### 2.1 static/js/image-batch-convert.js

**追加位置**: ファイル末尾（class の閉じ括弧 `}` の直後）

```diff
     static generateSuffix(width) {
         if (width === 0) {
             return 'original';
         }
         return `w${width}`;
     }
 }
+
+if (typeof window !== 'undefined') {
+    window.ImageBatchConvert = ImageBatchConvert;
+}
+console.debug('[image-batch-convert] loaded', typeof window !== 'undefined' ? !!window.ImageBatchConvert : 'no-window');
```

### 2.2 templates/tools/image-batch.html

**追加位置**: `runConversion()` の先頭（ファイル・バリアント数チェックの前）

```diff
         // 変換実行
         async function runConversion() {
+            if (typeof ImageBatchConvert === 'undefined') {
+                alert('画像変換機能の読み込みに失敗しました（image-batch-convert.js）。ページを再読み込みしてください。');
+                return;
+            }
+            if (typeof ImageConverter === 'undefined') {
+                alert('画像変換機能の読み込みに失敗しました（image-convert.js）。ページを再読み込みしてください。');
+                return;
+            }
             if (toolRunner.selectedFiles.length === 0) {
                 alert('ファイルを選択してください');
                 return;
             }
```

---

## 3. script タグの点検結果（変更なし）

- **確認内容**: `templates/tools/image-batch.html` の 508〜519 行付近の script タグを確認。
- **結果**:
  - `image-batch-convert.js` / `image-convert.js` / `tool-runner.js` のいずれにも **async / defer は付いていない**（同期読み込み・順序保証のまま）。
  - 読み込み順:  
    `file-validation.js` → `file-utils.js` → `image-convert.js` → `image-batch-presets.js` → **image-batch-convert.js** → `zip-utils.js` → `tool-runner.js` → インライン script  
  - **image-batch-convert.js は tool-runner.js より前、かつインライン script より前**で問題なし。変更は行っていない。

---

## 4. ローカルでの手動テスト結果メモ

- **確認日**: 実施日を記入してください。
- **環境**: ローカル（`python app.py`）または本番 URL。

| 項目 | 結果 |
|------|------|
| /tools/image-batch の表示 | 200、HTML に `image-batch-convert.js` を含むことを確認済み（test_client） |
| 画像1枚選択 + 3バリアント（2000/1200/800）で実行 | （手動）画像を1枚選び、バリアントを 2000px / 1200px / 800px に設定して「変換開始」→ 全バリアントで「ImageBatchConvert is not defined」が出ないこと、変換完了すること |
| ZIP一括ダウンロード | （手動）変換完了後「ZIPで一括ダウンロード」をクリック → ZIP がダウンロードされ、中身の画像が期待通りであること |
| DevTools Console | （手動）`[image-batch-convert] loaded true` が出力されること。SyntaxError / 404 が出ていないこと |
| Network | （手動）本番で `image-batch-convert.js` が 200 で返っていること（本番確認時） |

**手動チェック手順（推奨）**  
1. http://localhost:5000/tools/image-batch を開く。  
2. Console に `[image-batch-convert] loaded true` が出ることを確認。  
3. 画像を1枚選択し、バリアントを 2000 / 1200 / 800 の3つに設定。  
4. 「変換開始」をクリック。  
5. 進捗が進み、完了後に「ZIPで一括ダウンロード」が表示されることを確認。  
6. ZIP をクリックしてダウンロードし、解凍して画像が3種類あることを確認。
