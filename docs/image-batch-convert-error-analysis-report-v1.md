# ② 画像一括変換（ImageBatchConvert is not defined） 現状分析レポート v1

---

## 1. 事象サマリ

| 項目 | 内容 |
|------|------|
| **いつ** | ユーザーが画像一括変換ツールで画像を選択し「実行」したあと、変換処理中 |
| **どこで** | /tools/image-batch（画像一括変換ツール） |
| **何をすると** | 任意の画像（例: Invoice_2_p1.jpg）を選択し、複数バリアント（例: 2000px, 1200px, 800px）で変換を実行すると発生 |
| **期待動作** | 各バリアント幅ごとに変換された画像が生成され、一括ダウンロード（ZIP）できる |
| **実際の動作** | 全バリアントで「ImageBatchConvert is not defined」となり、変換が失敗する。ユーザーには「すべてのバリアントでエラー」として 2000px / 1200px / 800px それぞれに同じ未定義エラーが表示される |

---

## 2. 再現手順

### 本番手順
1. https://jobcan-automation.onrender.com/tools/image-batch を開く
2. 画像ファイルを1つ以上選択（例: Invoice_2_p1.jpg）
3. バリアントを複数設定（例: ECサイト用プリセットで 2000px, 1200px, 800px）
4. 「実行」をクリック
5. → 進捗または結果エラーで「2000px: ImageBatchConvert is not defined」等が表示される。DevTools Console に `ReferenceError: ImageBatchConvert is not defined` が出る

### ローカル手順
1. `python app.py` で起動し、http://127.0.0.1:5000/tools/image-batch を開く
2. 上記と同様に画像選択・バリアント設定・実行
3. → 同じコードベースであれば再現する場合としない場合がある（後述「原因分析」参照）。本番のみで再現する場合は、配信されているHTML/キャッシュ差分の可能性あり

---

## 3. エラーログ（原文）

### ユーザー報告（要約）
```
Invoice_2_p1.jpg: すべてのバリアントでエラー
2000px: ImageBatchConvert is not defined
1200px: ImageBatchConvert is not defined
800px: ImageBatchConvert is not defined
```

### Consoleエラー全文（想定）
```
ReferenceError: ImageBatchConvert is not defined
```

### スタックトレース（想定）
```
ReferenceError: ImageBatchConvert is not defined
    at runBatch のコールバック内 (image-batch.html のインライン script 内)
    at ImageBatchConvert.convertImageWithVariant (呼び出し元: 776行付近)
    at ToolRunner.runBatch 内のタスク実行
```
※ 実際の行番号はビルド/配信形態により変動する可能性あり。本番で再現した場合は DevTools のスタックトレースをそのまま取得することを推奨。

---

## 4. 関連コードマップ

### 関連ファイル一覧

| 種別 | ファイルパス | 役割 |
|------|--------------|------|
| **定義元** | `static/js/image-batch-convert.js` | `ImageBatchConvert` クラスをグローバルに定義。`convertImageWithVariant`, `generateSuffix`, `loadImageElement` 等を提供 |
| 依存 | `static/js/image-convert.js` | `ImageConverter` クラス（グローバル）。`image-batch-convert.js` のフォールバックで `ImageConverter.loadImageElement`、インライン側で `ImageConverter.applyRenameTemplate` を参照 |
| プリセット | `static/js/image-batch-presets.js` | バリアントプリセット（例: ECサイト用 2000/1200/800）の定義 |
| ページ | `templates/tools/image-batch.html` | ツールUI・script 読み込み・実行時の `runBatch` コールバックで `ImageBatchConvert` を参照 |
| 共通 | `static/js/tool-runner.js` | `ToolRunner.runBatch` でファイルごとにコールバックを実行 |

### 呼び出しの流れ（バリアント変換）

```
ユーザーが「実行」クリック
  → runOperation() 内で toolRunner.runBatch(callback) を呼ぶ
  → ToolRunner が選択ファイルごとに callback(files, ctx) を実行
  → callback 内（image-batch.html インライン script）:
        for (各バリアント) {
          result = await ImageBatchConvert.convertImageWithVariant(file, options, variant, ctx);  // 776行付近
          suffix = variant.suffix || ImageBatchConvert.generateSuffix(variant.width);            // 788行付近
          outputFilename = ImageConverter.applyRenameTemplate(...);                              // 790行付近
          outputs.push(...);
        }
  → ここで ImageBatchConvert が未定義だと ReferenceError
  → catch で variantErrors.push({ variant: '2000px' 等, message: error.message })              // 806-811行付近
  → 全バリアント分ループするため、2000px / 1200px / 800px のすべてで同じ「ImageBatchConvert is not defined」が積み上がる
```

### 定義元コード（抜粋）

**static/js/image-batch-convert.js（先頭〜クラス定義）**
```javascript
/**
 * 画像一括変換処理（v2: バリアント対応）
 */

class ImageBatchConvert {
    static MAX_PIXELS = 80000000; // 80,000,000ピクセル

    static async getImageSize(file) { ... }
    static validatePixelCount(width, height) { ... }
    static async convertImageWithVariant(file, options, variant, ctx = {}) {
        // ...
        const img = await ImageConverter.loadImageElement(file);  // フォールバック時のみ
        // ...
    }
    static loadImageElement(file) { ... }
    static generateSuffix(width) { ... }
}
```
- **export なし**。`<script src="...image-batch-convert.js">` で読み込んだ時点で **グローバル** に `ImageBatchConvert` が定義される前提。

### 呼び出し元コード（抜粋）

**templates/tools/image-batch.html（766〜812行付近）**
```javascript
                for (let vIndex = 0; vIndex < variants.length; vIndex++) {
                    const variant = variants[vIndex];
                    try {
                        const result = await ImageBatchConvert.convertImageWithVariant(
                            file,
                            { outputFormat, quality, preventUpscale },
                            variant,
                            ctx
                        );
                        const suffix = variant.suffix || ImageBatchConvert.generateSuffix(variant.width);
                        const outputFilename = ImageConverter.applyRenameTemplate(...);
                        // ...
                    } catch (error) {
                        variantErrors.push({
                            variant: variant.width === 0 ? 'original' : `${variant.width}px`,
                            message: error.message
                        });
                    }
                }
```

### スクリプト読み込み順（image-batch.html 508〜517行付近）

```html
    <script src=".../jszip.min.js"></script>
    <script src=".../file-validation.js"></script>
    <script src=".../file-utils.js"></script>
    <script src=".../image-convert.js"></script>        <!-- ImageConverter -->
    <script src=".../image-batch-presets.js"></script>
    <script src=".../image-batch-convert.js"></script>  <!-- ImageBatchConvert -->
    <script src=".../zip-utils.js"></script>
    <script src=".../tool-runner.js"></script>
    <script>
        // 上記の直後にインラインで toolRunner / runBatch / ImageBatchConvert 参照
    </script>
```

- 現在のテンプレートでは **image-batch-convert.js は tool-runner.js およびインライン script より前に** 読み込まれており、読み込み順としては問題ない。

---

## 5. 原因分析

### 5-1. 事実（コードとログから確定していること）

1. **ImageBatchConvert の定義**
   - `static/js/image-batch-convert.js` の 5 行目で `class ImageBatchConvert { ... }` として定義されている。
   - export はなく、グローバル変数として参照される想定。

2. **参照箇所**
   - `templates/tools/image-batch.html` のインライン script 内、776 行付近で `ImageBatchConvert.convertImageWithVariant(...)`、788 行付近で `ImageBatchConvert.generateSuffix(...)` を参照している。

3. **読み込み順（現在のテンプレート）**
   - image-batch.html では `image-batch-convert.js` をインライン script の直前に読み込んでいる。ZipUtils と同様、**読み込み順だけを見れば ImageBatchConvert は利用可能なはず**。

4. **「全バリアントで同じエラー」になる理由**
   - 1ファイルごとに `runBatch` のコールバックが実行され、その中で `variants` のループ（2000px → 1200px → 800px 等）が回る。
   - ループの先頭で `ImageBatchConvert.convertImageWithVariant(...)` を呼ぶため、**ImageBatchConvert が未定義だと最初のバリアントで ReferenceError**。
   - このエラーは `catch` で `variantErrors.push({ variant: '2000px', message: error.message })` のように記録される。
   - その後もループは続くが、**ImageBatchConvert は依然として未定義**なので、1200px / 800px でも同じ `ReferenceError` が発生し、同じメッセージが各バリアントに記録される。
   - したがって「2000px / 1200px / 800px すべてで ImageBatchConvert is not defined」と表示されるのは、**1つの原因（クラス未定義）が全バリアントで同じように表面化している**ため。

5. **実行環境**
   - 画像一括変換はすべてブラウザ内のクライアント側 JavaScript で実行される。サーバー側で ImageBatchConvert を参照する処理はない。

### 5-2. 仮説（複数）

| # | 仮説 | 内容 |
|---|------|------|
| H1 | **image-batch-convert.js が HTML に含まれていない** | 本番や特定環境で、image-batch.html から `image-batch-convert.js` の script タグが抜けている、または別ブランチ/古いデプロイでタグが無い。 |
| H2 | **スクリプトが 404 / ブロックで読み込めていない** | script の URL が誤っている、静的ファイルのパス/配信設定の違い、CSP やネットワークエラーで image-batch-convert.js が読み込めず、クラスが定義されない。 |
| H3 | **読み込み順の入れ替わり** | テンプレート改修やインライン script の位置変更で、ImageBatchConvert を参照するコードが image-batch-convert.js より前に実行されている（現行コードでは該当せず）。 |
| H4 | **image-batch-convert.js のパースまたは実行時エラー** | スクリプトは読み込まれるが、構文エラーやスクリプト先頭の依存（未定義のグローバル等）で実行が止まり、`class ImageBatchConvert` に到達する前に失敗している。 |
| H5 | **type="module" やバンドルによるスコープ** | image-batch-convert.js が type="module" で読み込まれている、またはバンドルで export のみされ window に露出していない（現行は通常の script で export なしのため、該当しにくい）。 |

### 5-3. 検証結果（仮説を潰す／裏付ける根拠）

- **H1**: 現行の `templates/tools/image-batch.html` には 515 行付近で `image-batch-convert.js` の script タグが存在する。**本番で配信されている HTML が同じかは未確認**（キャッシュ・デプロイ差分の確認が必要）。
- **H2**: コード上は `url_for('static', filename='js/image-batch-convert.js')` でパスは一貫。**本番で 404 や CSP でブロックされていないかは未確認**（DevTools の Network タブで確認推奨）。
- **H3**: 現行テンプレートでは image-batch-convert.js → zip-utils → tool-runner → インラインの順で、**参照より前に定義が読み込まれる**。H3 は現状のコードでは成立しない。
- **H4**: image-batch-convert.js はクラス定義のみでトップレベルの実行は少なく、依存は `ImageConverter`（image-convert.js、その前に読み込み済み）と `createImageBitmap`（ブラウザ標準）。**本番で Console に image-batch-convert.js 由来の別エラーが出ていないかは未確認**。
- **H5**: 該当ファイルは通常の `<script src="...">` で、export なし。**H5 は通常考えにくい**。

### 5-4. 結論（最も筋の良い原因）

**原因**: **ImageBatchConvert を定義する `image-batch-convert.js` が、エラーが発生している環境（本番または特定の表示）で「読み込まれていない」か「実行に失敗している」ため、グローバルの `ImageBatchConvert` が未定義のままになっている。**

- **なぜ全バリアントで同じ未定義エラーになるか**  
  上記「5-1. 事実」の 4 のとおり、1ファイルあたりの処理で「バリアントのループ」が回り、その都度 `ImageBatchConvert` を参照する。クラスが一度も定義されていないため、**どのバリアント（2000px / 1200px / 800px）でも同じ ReferenceError が発生し、同じメッセージが各バリアントに記録される**構造になっている。

- **本番のみで再現する場合に考えられること**  
  - 本番にデプロイされている HTML が古く、`image-batch-convert.js` の script タグが入っていない。  
  - キャッシュ（ブラウザや CDN）で古い HTML が返されている。  
  - 本番のみ静的ファイルのパスや配信設定が異なり、image-batch-convert.js が 404 になっている。

---

## 6. 修正方針（実装はしない）

### 最短の修正案（推奨）

1. **本番の HTML と Network の確認**
   - 本番の /tools/image-batch を開き、DevTools の Elements で `image-batch-convert.js` の `<script>` が存在するか確認する。
   - Network タブで `image-batch-convert.js` が 200 で読み込まれているか、404/CSP でブロックされていないかを確認する。
   - タグが無い、または 404 の場合は、デプロイ内容・キャッシュ・静的ファイル設定を見直し、**現在の image-batch.html（515 行付近で image-batch-convert.js を読み込んでいる形）が本番に反映されているようにする**。

2. **再発防止ガードの追加（ZipUtils と同様）**
   - 実行開始時（例: runBatch に渡すコールバックの先頭、または runOperation 内）で、`typeof ImageBatchConvert === 'undefined'` なら分かりやすいメッセージで throw する。
   - 例: `throw new Error('画像変換機能の読み込みに失敗しました（image-batch-convert.js）。ページを再読み込みしてください。');`
   - これにより、今後読み込み漏れや 404 が起きても「ImageBatchConvert is not defined」ではなく、原因が伝わりやすいメッセージになる。

### 代替案（メリット・デメリット）

| 案 | 内容 | メリット | デメリット |
|----|------|----------|------------|
| A | 上記 1＋2（本番確認＋ガード追加） | 原因切り分けと再発防止を両立できる | 本番確認は手作業が必要 |
| B | インラインで ImageBatchConvert の存在チェックのみ追加 | 変更が最小 | 読み込み漏れの根本（タグ不足や 404）は解消されない |
| C | image-batch-convert.js を ES module 化し import で参照 | 依存が明示的になる | 他 script も module 化が必要で影響が大きい。今回は非推奨 |

### 影響範囲

- **確認・修正対象**: `templates/tools/image-batch.html`（script タグの有無・順序）、および本番の静的ファイル配信・キャッシュ。
- **ガード追加する場合**: インライン script 内の runBatch コールバック先頭、または runOperation 内の実行前のいずれか 1 箇所。既存の正常系の動作は変えない。

### 追加テスト

- 本番と同等の URL（/tools/image-batch）で、DevTools の Network により image-batch-convert.js が 200 で読み込まれていることを確認する。
- 複数バリアント（2000px / 1200px / 800px 等）で変換を実行し、全バリアントが成功して ZIP ダウンロードできることを確認する。
- 意図的に image-batch-convert.js を外した場合、ガードを入れたなら「画像変換機能の読み込みに失敗しました（image-batch-convert.js）。ページを再読み込みしてください。」に近いメッセージになることを確認する。

---

## 7. 受け入れ条件（Definition of Done）

- [ ] 画像一括変換で複数バリアント（例: 2000px, 1200px, 800px）を指定して実行したとき、**「ImageBatchConvert is not defined」が出ない**。
- [ ] 各バリアントの変換が正常に完了し、**ZIP で一括ダウンロードできる**。
- [ ] 本番（または対象環境）の /tools/image-batch で、**image-batch-convert.js が 200 で読み込まれている**ことが確認されている。
- [ ] （ガードを入れた場合）読み込み失敗時は、**「image-batch-convert.js」を明示した分かりやすいエラーメッセージ**がユーザーに表示される。

---

## 8. 次ステップ

### 実装用 Cursor プロンプト案（短く1つ）

```
【依頼】画像一括変換の「ImageBatchConvert is not defined」を解消する。
原因: ImageBatchConvert を定義する image-batch-convert.js が、表示中のページで読み込まれていないか実行に失敗している。
対応:
1) templates/tools/image-batch.html で、image-batch-convert.js の <script> が tool-runner.js より前（現状は image-batch-presets.js の直後）に存在することを確認。無ければ追加。
2) 実行開始時（runBatch に渡すコールバックの先頭、または runOperation 内で runBatch を呼ぶ直前）で、typeof ImageBatchConvert === 'undefined' なら throw new Error('画像変換機能の読み込みに失敗しました（image-batch-convert.js）。ページを再読み込みしてください。'); を追加する。
3) 本番で /tools/image-batch を開き、DevTools の Network で image-batch-convert.js が 200 で読み込まれていることを確認する。404 の場合は静的ファイルのパス・デプロイ・キャッシュを確認する。
```

---

## 補足: 未確認・追加調査の指示

- **本番 HTML**: 実際に配信されている /tools/image-batch の HTML に `image-batch-convert.js` の script タグが含まれているか、**Elements タブで未確認**。含まれていない場合はデプロイ・キャッシュを確認すること。
- **本番 Network**: image-batch-convert.js のリクエストが 200 か、CSP やネットワークエラーでブロックされていないか、**未確認**。再現手順実行時に Network タブで記録すること。
- **Console の他エラー**: image-batch-convert.js 読み込み時やパース時に別のエラーが出ていないか、**未確認**。ReferenceError の前にスクリプトエラーが出ていないか確認すると、H4 の検証になる。
