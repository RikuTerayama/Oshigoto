# 画像ユーティリティ（Image Cleanup）「ImageCleanup is not defined」不具合 分析レポート

**作成日**: 2026-02-10  
**目的**: 画像ユーティリティで PNG 投入時に「ImageCleanup is not defined」が表示される原因を、根拠付きで整理する。**本レポートは分析のみで実装は行わない。**

---

## 0. Executive Summary（結論と最短対処案）

- **結論**: `ImageCleanup` は `static/js/image-cleanup.js` の **6 行目でクラスとして定義**されており、`templates/tools/image-cleanup.html` の **529 行目で同ファイルを `<script src="...">` で読み込み**、**759・762 行目のインライン script 内で `ImageCleanup.generateFilename` / `ImageCleanup.runCleanupPipeline` を参照**している。コード上は「読み込み順・名前・スコープ」は一致しており、**「image-cleanup.js がロードに失敗している」可能性が最も高い**（404・ネットワークエラー・キャッシュ等）。断定にはブラウザの Network タブで `/static/js/image-cleanup.js` のステータス確認と、Console で `window.ImageCleanup` の有無確認が有効。
- **最短対処案（たたき台）**: (1) Network で 404 なら静的ファイルパスと `url_for('static', filename='js/image-cleanup.js')` の出力を確認し、ファイル配置と一致させる。(2) ロード成功しているのに未定義なら、`image-cleanup.js` 先頭で `window.ImageCleanup = ...` を明示代入するか、インライン側で `typeof ImageCleanup !== 'undefined'` をガードしてメッセージを改善する。

---

## 1. 症状の再整理（UI、Console、Network）

| 項目 | 内容 |
|------|------|
| **画面表示** | 「Gemini_Generated_Image_rft3jrft3jrft3jr.png: ImageCleanup is not defined」 |
| **表示箇所** | エラー表示は `templates/tools/image-cleanup.html` の **878–884 行**で、`errors.forEach` により `file.name + ': ' + message` の形式で `<li>` を積み、**880 行** `errorMessage.innerHTML += \`<li>${file.name}: ${message}</li>\`` で描画している（根拠: **templates/tools/image-cleanup.html:878–884**）。 |
| **想定される JS エラー** | `ReferenceError: ImageCleanup is not defined`。`runCleanup()` 内の **processor**（756 行目付近の `async (file, ctx) => { ... }`）が実行され、**759 行**の `ImageCleanup.generateFilename(...)` または **762 行**の `ImageCleanup.runCleanupPipeline(...)` を評価した時点で、グローバル `ImageCleanup` が未定義のため発生（根拠: **templates/tools/image-cleanup.html:756–762**）。 |
| **Console** | 再現環境で取得できていれば、上記 ReferenceError のスタックに `runCleanup` / `processor` および該当行番号が含まれる想定。 |
| **Network** | `/static/js/image-cleanup.js` が **200 で返っているか**、**404/500 やブロックされていないか**を確認する必要がある（本レポート時点では未取得のため「断定手順」で記載）。 |

---

## 2. 再現手順（ローカルと本番想定）

### 2-1. ローカル起動

- **環境**: Python 3.x、必要なら `requirements.txt` の依存をインストール。
- **起動例**: `set FLASK_APP=app`（Windows）または `export FLASK_APP=app`（Mac/Linux）のうえ、`flask run` または `python -m flask run`。必要に応じて `app.py` の `if __name__ == '__main__'` で `app.run()` している場合は `python app.py`。
- **ルート**: `app.py` の **975–980 行**で `@app.route('/tools/image-cleanup')` が定義され、`render_template('tools/image-cleanup.html', product=product)` で表示（根拠: **app.py:975–980**）。

### 2-2. 操作と発生タイミング

1. ブラウザで `http://localhost:5000/tools/image-cleanup` を開く。
2. PNG ファイル（例: `Gemini_Generated_Image_rft3jrft3jrft3jr.png`）をドロップまたはファイル選択で投入。
3. オプションを選び「実行」ボタンをクリック。
4. **実行開始後、processor が各ファイルに対して呼ばれたタイミング**で、`ImageCleanup` が未定義なら ReferenceError が発生し、`toolRunner` のエラー収集を経て、画面に「ファイル名: ImageCleanup is not defined」と表示される（根拠: **templates/tools/image-cleanup.html:719–780, 878–884**）。

### 2-3. ブラウザで取得すべき情報（再現時）

- **Console**: エラー全文とスタックトレース（ReferenceError のファイル・行番号）。
- **Network**: `image-cleanup.js` のリクエスト URL、HTTP ステータス、レスポンス有無。可能なら「Disable cache」をオンにして再実行。

---

## 3. コード調査結果（検索結果、参照と定義、読み込み経路）

### 3-1. ImageCleanup の参照・定義の検索結果

| 種類 | ファイル | 行番号 | 内容 |
|------|----------|--------|------|
| **定義** | `static/js/image-cleanup.js` | **6** | `class ImageCleanup {`（トップレベルでクラス定義、export なし・type="module" なし） |
| **参照** | `templates/tools/image-cleanup.html` | **759** | `ImageCleanup.generateFilename(file.name, ...)` |
| **参照** | `templates/tools/image-cleanup.html` | **762** | `return await ImageCleanup.runCleanupPipeline(file, { ... })` |
| ドキュメント等 | `docs/tools-mvp-implementation-report.md` | 571 | 「ImageCleanupクラスで処理（image-cleanup.js）」 |
| ドキュメント等 | `docs/feature-plans/01_image-style-v1.md` | 85 | `ImageCleanup.runCleanupPipeline` 内の記述 |
| ドキュメント等 | `docs/ops/where-is-image-style-v1.md` | 38 | 呼び出し元の説明 |

名前の揺れ（ImageCleaner / ImageCleanUp / imageCleanup）をリポジトリ内で検索した結果、**定義・参照とも `ImageCleanup`（大文字 C）で統一**されている。過去名称の不一致は見当たらない（根拠: リポジトリ全体の grep 結果）。

### 3-2. 読み込み経路

- **Script タグ**: `templates/tools/image-cleanup.html` の **521–532 行**で、次の順に読み込み（根拠: **templates/tools/image-cleanup.html:521–532**）。
  1. JSZip CDN（519）
  2. `file-validation.js`（522）
  3. `file-utils.js`（523）
  4. `zip-utils.js`（524）
  5. `tool-runner.js`（525）
  6. `image-load.js`（526）
  7. `image-export.js`（527）
  8. `image-style.js`（528）
  9. **`image-cleanup.js`（529）** ← ここで `ImageCleanup` がグローバルに定義される想定
  10. `image-style-preview.js`（530）
  11. `image-background-removal.js`（531）
  12. `image-aspect.js`（532）
- **いずれも `type="module"` や `defer`/`async` は付与されていない**（同ファイル内に該当なし）。したがって同期読み込みで、529 の実行が完了した時点でグローバルに `ImageCleanup` が存在する設計。
- **インライン script**: 533 行目以降の `<script>` 内で `runCleanup()` およびその中の `processor`（756–762 行付近）が `ImageCleanup` を参照。実行タイミングは「ユーザーが実行ボタンを押した後」であり、通常は全 script 読み込み完了後である。

### 3-3. image-cleanup.js のスコープ

- **static/js/image-cleanup.js**: 先頭は `/** ... */` コメントと **6 行目の `class ImageCleanup {`**。ファイル末尾は **378 行目の `}`**（クラス閉じ）。`export` や IIFE によるラップはなく、**古典的 script として読み込んだ場合、グローバルに `ImageCleanup` が定義される**（根拠: **static/js/image-cleanup.js:1–6, 357–378**）。
- クラス内では `FileUtils`（358 行）、`FileValidation`（335 行）を参照しているが、これらはメソッド実行時のみ評価され、クラス定義時には評価されない。`file-utils.js` と `file-validation.js` は 523・522 行で先に読み込まれており、実行順序上は問題ない（根拠: **static/js/image-cleanup.js:335, 358** および **templates/tools/image-cleanup.html:522–523**）。

---

## 4. 原因候補ランキング（根拠付き）

| 順位 | 原因候補 | 根拠・観点 |
|------|----------|------------|
| **1** | **image-cleanup.js が読み込まれていない（404・ネットワークエラー・ブロック）** | エラーが「ImageCleanup is not defined」であることから、グローバルにクラスが存在しない。定義は **static/js/image-cleanup.js:6** のみで、ここが実行されていなければ未定義のまま。script タグのパスは **529 行** `url_for('static', filename='js/image-cleanup.js')`。本番/環境によっては静的ファイルのルート違い・大文字小文字・キャッシュで 404 や別ファイルが返り、該当 script が実行されない可能性がある。 |
| **2** | **image-cleanup.js のロードは成功しているが、実行時エラーでクラス定義に到達していない** | 同じファイル内で、クラス定義の前（1–5 行はコメントのみ）やクラス本体の評価中に例外が発生すると、`ImageCleanup` がグローバルに代入されない。現状のコードではトップレベルで他モジュールを参照しておらず、クラス定義のみなので可能性はやや低いが、実行環境や minify 時の不具合では否定できない。Console に image-cleanup.js 由来の別エラーが出ていないか確認するとよい。 |
| **3** | **スコープ問題（ESM で export のみで window に出していない）** | 現状の **image-cleanup.js は `export` も `type="module"` も使っていない**（根拠: **static/js/image-cleanup.js** 全体）。テンプレート側の script タグにも **type="module" はない**（根拠: **templates/tools/image-cleanup.html** の script 一覧）。したがって「module のまま window に露出していない」という原因は、**現行コードでは該当しない**。 |
| **4** | **テンプレート分岐で script が読み込まれない** | image-cleanup.html の 521–532 行は条件分岐内にない（**templates/tools/image-cleanup.html:518–532**）。`{% include %}` で footer 等を挟むが、script は include の後に並んでいるため、分岐による読み込み漏れの可能性は低い。 |
| **5** | **実行順序（ImageCleanup を使うコードが先に実行）** | `ImageCleanup` を参照しているのは **インライン script 内の `processor`**（756–762 行）であり、これは **runCleanup() が呼ばれたとき**（ユーザーが実行ボタンを押したとき）に初めて実行される。ページロード時の同期 script の並びでは、529 の image-cleanup.js が 533 以降のインラインより先に実行されるため、通常は順序問題は起きない。 |
| **6** | **minify / bundler の影響** | リポジトリに **image-cleanup.min.js やバンドル成果物は見当たらず**、**template は生の image-cleanup.js を参照**している（**templates/tools/image-cleanup.html:529**）。本番で別ビルドを差し替えている場合は要確認。 |

---

## 5. 原因の断定（決め手となる観測）

- **「読み込み漏れ」と確定するには**
  - ブラウザの **Network** で `image-cleanup.js`（または `js/image-cleanup.js`）をフィルタし、**ステータスが 404/500 や Failed** になっていないか確認する。200 でかつレスポンス本文がクラス定義を含む JS であることを確認する。
  - **Console** でページ読み込み直後に `window.ImageCleanup` を入力し、**`undefined` なら未読み込みまたは実行失敗**、**function/class なら読み込みは成功**している。
- **「module スコープ問題」と確定するには**
  - 該当 script タグに `type="module"` が付いているか、または image-cleanup.js 内に `export` のみで `window.ImageCleanup = ...` がないかを確認する。現行コードでは **いずれも該当しない** ため、この原因はほぼ除外できる。
- **「名前不一致」と確定するには**
  - 参照側（759・762 行）と定義側（image-cleanup.js:6）の識別子が完全に一致しているか確認する。現状は **いずれも `ImageCleanup`** で一致している（根拠: 本レポート 3-1）。大文字小文字の違いがあれば ReferenceError になり得るが、今回のコードでは不一致はない。

**追加で必要な観測**: 実際の環境で **Network の image-cleanup.js のステータス** と **Console の `window.ImageCleanup`** を取得すると、原因を「読み込み失敗」に絞り込める。

---

## 6. 修正方針 2 から 3 案（差分方針のみ・実装しない）

### 案 A: 読み込み失敗対策（パス・静的配信の確認と明示的なグローバル露出）

- **ファイル**: `app.py`（静的ルート・ディレクトリ設定）、`static/js/image-cleanup.js`（必要なら末尾に `window.ImageCleanup = ImageCleanup;` を追加）。
- **内容**: (1) Flask の `static` ルートと実際の `static/js/image-cleanup.js` の存在・URL を確認し、404 の原因（パス、大文字小文字、本番の静的配信）を解消する。(2) 読み込みは成功するが何らかの理由でグローバルに出ていない場合に備え、**image-cleanup.js の末尾（378 行の直後）に `window.ImageCleanup = ImageCleanup;` を 1 行追加**し、グローバルを明示する。
- **互換性・リスク**: `window.ImageCleanup` の明示代入は、既にグローバルで読んでいるページにのみ影響し、他ツールは ImageCleanup を参照していないため影響は小さい。キャッシュ対策として、本番で `?v=...` を付与する場合は、デプロイ後にハードリロードやキャッシュ無効化の案内があるとよい。

### 案 B: 未定義時のガードとメッセージ改善（UX）

- **ファイル**: `templates/tools/image-cleanup.html`（runCleanup 内の processor、または runCleanup の先頭）。
- **内容**: **processor の先頭**（756 行付近）で `if (typeof ImageCleanup === 'undefined') { throw new Error('画像処理エンジンの読み込みに失敗しました。ページを再読み込みするか、ネットワークを確認してください。'); }` のようにガードし、**runCleanup() の先頭**で同様のチェックを入れてもよい。これにより「ImageCleanup is not defined」ではなく、ユーザー向けの短いメッセージにできる。
- **互換性・リスク**: 既存の「定義されている場合」の挙動は変えない。原因の根本（読み込み失敗）は解消しないが、表示メッセージと再読み込みの案内で UX は改善できる。

### 案 C: script の defer なし・順序の明文化とフォールバック表示

- **ファイル**: `templates/tools/image-cleanup.html`（script タグのコメントまたは順序の明文化、および実行ボタン付近のフォールバック）。
- **内容**: (1) image-cleanup.js が「image-style.js の後・インライン script の前」であることをコメントで明記し、将来の変更で順序が崩れないようにする。(2) 実行ボタン表示前に `typeof ImageCleanup !== 'undefined'` をチェックし、未定義ならボタンを無効化または「読み込み中です」と表示し、数秒後に再チェックする。これにより、読み込み遅延や失敗時にユーザーが実行して ReferenceError に遭う前に案内できる。
- **互換性・リスク**: ボタン無効化やメッセージ表示の条件を誤ると、正常時にもボタンが押せなくなる可能性があるため、条件式と再チェック間隔は慎重に設計する。defer は付けない（現状の同期読み込みを維持）。

---

## 7. 検証チェックリスト（ローカル、本番）

### ローカル

- [ ] `http://localhost:5000/tools/image-cleanup` が 200 で開ける（**app.py:975–980**）。
- [ ] 開発者ツールの Network で `image-cleanup.js` が 200 で返り、レスポンス本文に `class ImageCleanup` が含まれる。
- [ ] Console で `window.ImageCleanup` が `undefined` でない（class/function）。
- [ ] PNG を 1 枚投入し、実行ボタンでクリーンアップが完了し、エラーが出ない。
- [ ] 複数ファイル（PNG/JPEG/WebP）、キャンセル（あれば）でも同様に動作する。

### 本番（Render 等）

- [ ] `/tools/image-cleanup` が 200。`/static/js/image-cleanup.js` が 200 で返る（キャッシュ無効やハードリロードで再確認）。
- [ ] 本番ドメインで Console の `window.ImageCleanup` を確認。
- [ ] キャッシュや CDN により古い HTML が配信され、script タグが無い／パスが違うページになっていないか確認。

### Network / Console で見る項目

- `image-cleanup.js` のリクエスト URL、Status Code、Size。
- Console の ReferenceError のスタック（ファイル名・行番号）。
- 他 script（file-utils.js, file-validation.js 等）が 404 になっていないか（ImageCleanup は image-cleanup.js のみで定義されているが、実行時には FileUtils 等も参照されるため）。

---

## 8. 参照（ファイルパスと行番号一覧）

| ファイル | 行番号 | 内容 |
|----------|--------|------|
| app.py | 975–980 | `/tools/image-cleanup` ルート、`tools/image-cleanup.html` をレンダリング |
| templates/tools/image-cleanup.html | 521–532 | 共通ライブラリの script 読み込み順（image-cleanup.js は 529） |
| templates/tools/image-cleanup.html | 533–891 | インライン script（toolRunner, runCleanup, processor, handleError 等） |
| templates/tools/image-cleanup.html | 756–762 | processor 内で `ImageCleanup.generateFilename` / `ImageCleanup.runCleanupPipeline` を参照 |
| templates/tools/image-cleanup.html | 878–884 | エラー表示（file.name + ': ' + message） |
| static/js/image-cleanup.js | 1–6 | コメントと `class ImageCleanup {` の開始 |
| static/js/image-cleanup.js | 335, 358 | FileValidation.sanitizeFilename / FileUtils.getFilenameWithoutExtension の参照 |
| static/js/image-cleanup.js | 357–378 | generateFilename とクラス閉じ |

---

以上。
