# ① ZIP作成エラー（ZipUtils is not defined） 現状分析レポート v1

---

## 1. 事象サマリ

| 項目 | 内容 |
|------|------|
| **いつ** | ユーザーが「ZIPで一括ダウンロード」ボタンをクリックした直後 |
| **どこで** | PDFツール（埋め込み画像抽出）または 画像クリーンアップツール の結果が複数ファイルのとき |
| **何をすると** | 複数ファイル出力時に表示される「📦 ZIPで一括ダウンロード」を押すと発生 |
| **期待動作** | 複数画像を1つのZIPにまとめてダウンロードされる |
| **実際の動作** | アラートで「ZIP作成エラー: ZipUtils is not defined」と表示され、ZIPが作成されない |

---

## 2. 再現手順

### 本番手順
1. https://jobcan-automation.onrender.com/tools/pdf を開く
2. ツールモードで「埋め込み画像抽出（試験版）」を選択
3. PDFファイルを1つ選択し、実行
4. 処理完了後、「📦 ZIPで一括ダウンロード」ボタンをクリック
5. → アラート「ZIP作成エラー: ZipUtils is not defined」が表示される

**または** 画像クリーンアップ（/tools/image-cleanup）で複数ファイルを処理し、同様に「ZIPで一括ダウンロード」をクリックした場合も同じエラーが発生する。

### ローカル手順
1. `python app.py` で起動し、http://127.0.0.1:5000/tools/pdf を開く
2. 上記と同様に「埋め込み画像抽出」を実行し、ZIPダウンロードをクリック
3. → 本番と同一のエラーが再現する（環境差なし）

---

## 3. エラーログ（原文）

### Consoleエラー全文（想定）
```
ReferenceError: ZipUtils is not defined
```

### スタックトレース（想定）
```
ReferenceError: ZipUtils is not defined
    at ToolRunner.downloadAllZip (tool-runner.js:426)
    at async HTMLButtonElement.zipButton.onclick (pdf.html または image-cleanup.html 内インライン)
```

### ユーザーに表示される文言
- アラート: **「ZIP作成エラー: ZipUtils is not defined」**
- 出所: 各ツールの `showDownloadPanel` 内で `catch (error)` 時に `alert(\`ZIP作成エラー: ${error.message}\`)` として表示（例: `pdf.html` 934行付近、`image-cleanup.html` 769行付近）。

---

## 4. 関連コードマップ

### 関連ファイル一覧

| 種別 | ファイルパス | 役割 |
|------|--------------|------|
| ユーティリティ（定義） | `static/js/zip-utils.js` | `ZipUtils` クラス定義。`JSZip` をグローバルに参照し `createZip()` を提供 |
| 共通ランナー | `static/js/tool-runner.js` | `ToolRunner.downloadAllZip()` 内で **グローバル** `ZipUtils.createZip()` を呼ぶ |
| PDFツール | `templates/tools/pdf.html` | 埋め込み画像抽出UI・実行・`downloadAllZip('pdf-tools-output.zip')` 呼び出し |
| PDF抽出ロジック | `static/js/pdf-extract-images.js` | `PdfExtractImages.extractEmbeddedImages()` — PDFから画像抽出 |
| 画像クリーンアップ | `templates/tools/image-cleanup.html` | 複数出力時に `downloadAllZip('image-cleanup-output.zip')` 呼び出し |
| 画像一括変換 | `templates/tools/image-batch.html` | 同様にZIPダウンロードを使用するが、**ここだけ** `zip-utils.js` を読み込んでいる |

### 呼び出しの流れ（埋め込み画像抽出の場合）

```
pdf.html
  → ユーザーが「埋め込み画像抽出」実行
  → PdfExtractImages.extractEmbeddedImages()（pdf-extract-images.js）
  → 複数画像が toolRunner.outputs に格納
  → showDownloadPanel() で「ZIPで一括ダウンロード」ボタン表示
  → クリック時: toolRunner.downloadAllZip('pdf-tools-output.zip')
     → tool-runner.js 内で ZipUtils.createZip(...) を呼ぶ
     → ZipUtils が未定義のため ReferenceError
  → catch で alert('ZIP作成エラー: ' + error.message)
```

### スクリプト読み込み順の比較（事実）

**pdf.html（486–497行付近）**
```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>
<script src=".../file-validation.js"></script>
<script src=".../file-utils.js"></script>
<script src=".../tool-runner.js"></script>   <!-- ZipUtils を参照するが、zip-utils.js は未読み込み -->
<script src=".../pdf-range.js"></script>
...
<script src=".../pdf-extract-images.js"></script>
```
→ **zip-utils.js が含まれていない。**

**image-cleanup.html（454–464行付近）**
```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>
<script src=".../file-validation.js"></script>
<script src=".../file-utils.js"></script>
<script src=".../tool-runner.js"></script>
<script src=".../image-load.js"></script>
...
```
→ **zip-utils.js が含まれていない。**

**image-batch.html（508–517行付近）**
```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>
<script src=".../file-validation.js"></script>
<script src=".../file-utils.js"></script>
<script src=".../image-convert.js"></script>
...
<script src=".../zip-utils.js"></script>   <!-- ここだけ読み込みあり -->
<script src=".../tool-runner.js"></script>
```
→ **zip-utils.js を tool-runner.js の直前に読み込んでおり、ZIPダウンロードが動作する。**

---

## 5. 原因分析

### 5-1. 事実（コードとログから確定していること）

1. **ZipUtils の定義場所**  
   - `static/js/zip-utils.js` にクラス `ZipUtils` が定義されている（6行目 `class ZipUtils {`）。  
   - export はしておらず、`<script src="...zip-utils.js">` で読み込んだときに **グローバル** に `ZipUtils` が定義される前提。

2. **ToolRunner の参照方法**  
   - `static/js/tool-runner.js` の 426 行目で `ZipUtils.createZip(...)` を呼んでいる。  
   - このファイル内に `ZipUtils` の import や require はなく、**グローバル変数としての ZipUtils に依存している**。

3. **読み込みの有無**  
   - `zip-utils.js` を読み込んでいるテンプレートは **image-batch.html のみ**（grep 結果: `templates/tools/image-batch.html` のみに `zip-utils.js` の script タグあり）。  
   - **pdf.html** と **image-cleanup.html** には `zip-utils.js` の script タグが **ない**。

4. **エラーがユーザーにどう見えるか**  
   - `downloadAllZip()` 内の `catch`（tool-runner.js 445–446 行）で `throw new Error(\`ZIP作成に失敗しました: ${error.message}\`)` と再スローしている。  
   - 元の `ReferenceError: ZipUtils is not defined` の `error.message` がそのまま含まれるため、アラートは「ZIP作成エラー: ZipUtils is not defined」となる。

5. **実行環境**  
   - 本リポジトリは **Flask + Jinja2** のサーバーサイドレンダリングでHTMLを返し、ZIP処理はすべて **ブラウザ内のクライアント側JavaScript** で実行されている。  
   - Next.js / Node ランタイムのSSRは使っておらず、ZipUtils 未定義は「どの script をどのページで読み込むか」の不足が原因。

### 5-2. 仮説（可能性）を複数提示

| # | 仮説 | 内容 |
|---|------|------|
| H1 | **zip-utils.js が pdf / image-cleanup で読み込まれていない** | 上記の script タグ比較の通り、該当2ページで zip-utils.js が欠けている。 |
| H2 | JSZip が読み込まれる前に ZipUtils が実行されている | pdf.html では JSZip CDN は読み込まれており、ZipUtils の「定義」そのものが無いため、実行順ではなく「定義スクリプト未読み込み」が本質。 |
| H3 | 本番だけバンドルや minify で ZipUtils が落ちている | 本リポジトリは Vite/Webpack 等のバンドルをしておらず、静的ファイルをそのまま配信。ローカルと本番で同じHTML/JSが使われるため、本番だけ落ちる要因はない。 |
| H4 | 別オリジン・CSP で zip-utils.js がブロックされている | 未確認。本番で DevTools の Network タブで zip-utils.js が 404 またはブロックされていないかは確認推奨。 |

### 5-3. 検証結果（仮説を潰した根拠）

- **H1**: コード上、pdf.html と image-cleanup.html に `zip-utils.js` の `<script>` が存在しないことが確定。**成立。**
- **H2**: 問題は「実行順」ではなく「ZipUtils を定義するスクリプトがページに無い」こと。JSZip の有無は二次的（zip-utils.js が無いので ZipUtils が未定義で落ちる）。**本質は H1。**
- **H3**: リポジトリにフロント用バンドル設定がなく、静的JSをそのまま配信している。**本番限定の tree-shaking 等は考えにくい。**
- **H4**: コードベースからは判断できない。**未確認**のままとする。

### 5-4. 結論（最も筋の良い原因）

**原因**: **PDFツール（pdf.html）と画像クリーンアップツール（image-cleanup.html）で、`ZipUtils` を定義する `zip-utils.js` を読み込んでいないため、`tool-runner.js` の `downloadAllZip()` 実行時にグローバル `ZipUtils` が未定義となり `ReferenceError` が発生している。**

- **なぜ「本番でだけ」に見えることがあるか**  
  - 実際にはローカルでも同じ条件で再現する。  
  - 「画像一括変換ではZIPが動くが、PDFの埋め込み画像抽出では動かない」という使い分けをしている場合、本番でPDFツールを主に使うと「本番でだけ」のように感じられる。  
  - あるいは、image-batch では最初から zip-utils.js を入れていたが、pdf / image-cleanup に ZIP機能を後から追加した際に script の追加を漏らした、という経緯が考えられる。

---

## 6. 修正方針（実装はしない）

### 最短の修正案（推奨）

- **pdf.html** と **image-cleanup.html** の両方で、**tool-runner.js の直前に** `zip-utils.js` を読み込む `<script>` を1行ずつ追加する。
- 順序の目安:  
  - 既存の JSZip CDN の後、  
  - `file-utils.js` の後、  
  - **zip-utils.js**（新規追加）、  
  - **tool-runner.js**  
  とする（image-batch.html の並びに揃える）。

**理由**: 既存の image-batch.html で実績のある読み込み順を、同じグローバル前提の他ツールに揃えるだけなので、変更量が少なく、影響範囲が明確。

### 代替案（メリット/デメリット）

| 案 | 内容 | メリット | デメリット |
|----|------|----------|------------|
| A | 上記の script タグ追加（推奨） | 最小変更で即解消、他ツールと一貫 | グローバル依存はそのまま |
| B | tool-runner.js 内で ZipUtils 未定義時に動的で zip-utils.js を読み込む | 1ファイル修正で済む場合あり | 非同期読み込みの制御が複雑、既存の同期前提と合わない可能性 |
| C | ZipUtils を ES module 化し、tool-runner も module として import する | 依存関係が明示的になる | 全ツールの script を type="module" に変更する必要があり、影響が大きい |

### 影響範囲

- **変更ファイル**: `templates/tools/pdf.html`、`templates/tools/image-cleanup.html` の2ファイル。  
- **影響する機能**: PDFツールの「埋め込み画像抽出」のZIP一括ダウンロード、画像クリーンアップの複数ファイルZIPダウンロード。  
- **副作用**: zip-utils.js は JSZip にのみ依存し、他スクリプトを書き換えないため、読み込み順さえ守れば他機能への影響はないと判断できる。

### 追加で必要なテスト

- PDFツール: 埋め込み画像抽出を実行 → 複数画像が出力されるケースで「ZIPで一括ダウンロード」をクリックし、ZIPがダウンロードされ、中身のファイル数・ファイル名・破損がないことを確認。  
- 画像クリーンアップ: 複数ファイルを処理し、同様にZIP一括ダウンロードが成功することを確認。  
- 既存の画像一括変換のZIPダウンロードが従来どおり動作することを確認（リグレッション）。

---

## 7. UIに追加する説明文案（ユーザー向け）

### 7-1. 「埋め込み画像抽出とは？」（短い説明）

- **案**: 「PDFの中に含まれる画像を、1枚ずつ画像ファイルとして取り出す機能です。スキャンした書類や、画像が入ったPDFからイラストや写真だけをまとめて取り出したいときに使えます。」

### 7-2. 「対応ファイルと抽出の仕組み」（噛み砕いた説明）

- **案**: 「対象はPDFファイルです。PDFはページごとの見た目（ラスター画像）として読み込み、各ページを1枚の画像として出力します。※試験版のため、PDFの種類によっては『ページ全体を画像として保存する』形になり、元のPDF内の『図として埋め込まれた画像だけ』を完全に分離できない場合があります。正式版では、埋め込み画像だけをより正確に取り出す改良を予定しています。」

### 7-3. 「うまく抽出できないケース」（例と対処）

- **案**  
  - 「**ベクターのみのページ** … 線や図形だけで画像データが無いページは、そのページを1枚の画像として出力します。」  
  - 「**暗号化・制限付きPDF** … 閲覧のみ許可されているPDFでは、正常に処理できない場合があります。」  
  - 「**極端に多いページ数** … 1PDFあたりの抽出数に上限（例: 200枚）を設けています。必要な範囲だけを別PDFに分けてから実行するとよいです。」  
  - 「**抽出結果が0件** … そのPDFからは画像として取り出せるデータが検出されなかった場合です。別のPDFでお試しください。」

### 7-4. 「ZIPダウンロードの流れ」（ユーザー操作の案内）

- **案**: 「複数の画像が出力された場合は、画面上の『📦 ZIPで一括ダウンロード』ボタンを押すと、すべての画像を1つのZIPファイルにまとめてダウンロードできます。ZIPを解凍すると、画像が個別のファイルとして保存されています。」

---

## 8. 受け入れ条件（Definition of Done）

- [ ] エラーが消える: 「ZIPで一括ダウンロード」クリック時に「ZipUtils is not defined」が出ない。
- [ ] ZIPが期待通り生成される: 画像数・ファイル名・階層・文字化けなしで、ZIPがダウンロードされ、解凍して開ける。
- [ ] 主要ブラウザで動く: Chrome / Edge / Safari / Firefox の最新版で、PDFツール・画像クリーンアップのZIPダウンロードが動作する。
- [ ] 既存の画像一括変換のZIPダウンロードにリグレッションがない。

---

## 9. 次ステップ

### このレポートを踏まえた「実装用Cursorプロンプト案」（短く1つ）

```
【依頼】ZIP作成エラー「ZipUtils is not defined」を解消する。
原因: templates/tools/pdf.html と templates/tools/image-cleanup.html で
zip-utils.js を読み込んでいないため、tool-runner.js の downloadAllZip() 実行時に
ZipUtils が未定義で ReferenceError になる。
対応: 上記2ファイルで、tool-runner.js の直前に
<script src="{{ url_for('static', filename='js/zip-utils.js') }}"></script>
を追加すること。読み込み順は templates/tools/image-batch.html（516–517行付近）を参考にし、
JSZip CDN → file-validation.js → file-utils.js → (必要なら他) → zip-utils.js → tool-runner.js
とする。変更後、PDFの埋め込み画像抽出と画像クリーンアップの「ZIPで一括ダウンロード」が
動作することを確認する。
```

---

## 補足: 未確認・追加調査の指示

- **H4（CSP/ネットワーク）**: 本番で「ZIPで一括ダウンロード」実行時に、DevTools の Console に出るエラー全文と、Network タブで `zip-utils.js` や `jszip.min.js` が 200 で読み込まれているかを確認すると、より確実です。  
- **本番のみ再現する要因**: コード上はローカルと本番で同じHTML/JSが使われる想定のため、本番のみでる場合はキャッシュ（古いHTMLに zip-utils が無い）や、別ブランチのデプロイになっていないかの確認を推奨します。
