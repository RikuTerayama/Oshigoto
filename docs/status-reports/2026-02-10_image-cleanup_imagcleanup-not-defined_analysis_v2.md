# 画像クリーンアップ「ImageCleanup is not defined」分析レポート v2

**作成日**: 2026-02-10  
**目的**: 一次原因を断定できる証拠付きで特定し、最小修正方針まで整理する。**実装は行わない。**

---

## 1. Summary（結論と一次原因）

- **結論（証拠付き）**:  
  - **事実**: `ImageCleanup` は `static/js/image-cleanup.js` の **6 行目**で `class ImageCleanup {` として定義されている（**static/js/image-cleanup.js:6**）。参照は `templates/tools/image-cleanup.html` の **759 行**（`ImageCleanup.generateFilename`）と **762 行**（`ImageCleanup.runCleanupPipeline`）のみ。同テンプレート **529 行**で `<script src="{{ url_for('static', filename='js/image-cleanup.js') }}"></script>` により読み込まれており、**type="module" / defer / async は付与されていない**（**templates/tools/image-cleanup.html:529, 533**）。エラー表示「ファイル名: ImageCleanup is not defined」は **880 行**の `errorMessage.innerHTML += \`<li>${file.name}: ${message}</li>\`` で生成されている（**templates/tools/image-cleanup.html:878-880**）。
  - **本レポート作成時の観測**: 本番 URL `https://jobcan-automation.onrender.com/tools/image-cleanup` の取得ではページ本文は取得できたが、view-source 相当の生 HTML（script タグの有無）はツールの都合で確認できていない。本番の `https://jobcan-automation.onrender.com/static/js/image-cleanup.js` の取得は **エラー**（要ブラウザでの Network 確認）。
  - **一次原因の断定**: コード上は「定義・参照・読み込み順・スコープ」に矛盾はない。**一次原因を断定するには、本番ブラウザで以下が必須**である: (1) Network で `/static/js/image-cleanup.js` の Status（200/404/500）と Response 先頭（JS か HTML か）、(2) Console の `typeof ImageCleanup` / `typeof window.ImageCleanup`。  
  - **最も確度の高い仮説**: **A（ロード失敗）**。本番で当該 script が 404・500・または HTML（エラーページ）で返っていると、`ImageCleanup` は未定義のままとなる。B（先行エラー）・C（スコープ）・D（デプロイ不整合）・E（テンプレ欠落）は、上記ブラウザ観測で否定または肯定できる（後述）。

- **最短対処のたたき台**: A なら静的パス・配置・本番ビルドの確認と修正。C なら `image-cleanup.js` 末尾に `window.ImageCleanup = ImageCleanup;` を追加。B なら Console の「最初のエラー」の行を修正。

---

## 2. 症状（UI/エラー文言/再現手順）

| 項目 | 内容 |
|------|------|
| **UI 表示** | 「Gemini_Generated_Image_*.png: ImageCleanup is not defined」のように、**ファイル名: メッセージ** の形式でエラーが表示される。 |
| **エラー文言の出所** | インライン script 内の **showErrors** で、`errors.forEach` の `message` が `ReferenceError` の `.message`（"ImageCleanup is not defined"）であり、**880 行**で `file.name` と結合されて `<li>` に出力されている（**templates/tools/image-cleanup.html:878-880**）。 |
| **再現手順** | (1) 本番またはローカルで `/tools/image-cleanup` を開く。(2) PNG（例: Gemini_Generated_Image_*.png）をドロップまたは選択して追加。(3) オプションを選び「処理開始」をクリック。(4) 処理開始後、**processor**（756 行の `async (file, ctx) => { ... }`）が実行され、**759 行**または **762 行**で `ImageCleanup` を参照した時点で `ReferenceError: ImageCleanup is not defined` が発生し、その message が上記 UI に表示される。 |

---

## 3. コード根拠（定義/参照/読み込み/表示箇所：行番号付き）

### 3-1. 定義

| ファイル | 行番号 | 内容 |
|----------|--------|------|
| static/js/image-cleanup.js | **6** | `class ImageCleanup {`（トップレベル。export なし・IIFE なし） |
| static/js/image-cleanup.js | 357-376 | `static generateFilename(...)` とクラス閉じ `}` |

### 3-2. 参照

| ファイル | 行番号 | 内容 |
|----------|--------|------|
| templates/tools/image-cleanup.html | **759** | `ImageCleanup.generateFilename(file.name, outputFormat === 'jpg' ? 'jpg' : outputFormat, ctx.index + 1, filenameTemplate, bgRemoved)` |
| templates/tools/image-cleanup.html | **762** | `return await ImageCleanup.runCleanupPipeline(file, { ... }, ctx);` |

上記参照は **インライン script 内の processor**（**756-784 行**）に含まれる。processor は **runCleanup()**（**725 行**付近）内で定義され、ユーザーが「処理開始」を押したあと **toolRunner.run(...)** によって呼ばれる。

### 3-3. 読み込み（script タグ）

| ファイル | 行番号 | 内容 |
|----------|--------|------|
| templates/tools/image-cleanup.html | **521-532** | 共通ライブラリの script 列。**529 行**が `image-cleanup.js`。 |
| templates/tools/image-cleanup.html | **529** | `<script src="{{ url_for('static', filename='js/image-cleanup.js') }}"></script>`（**type="module" / defer / async は付いていない**） |
| templates/tools/image-cleanup.html | **533** | `<script>`（インライン開始）。**type="module" は付いていない**。 |

読み込み順: 522→523→524→525→526→527→528→**529（image-cleanup.js）**→530→531→532 のあと、533 行目のインライン script が評価される。同期読み込みのため、529 の実行完了後にグローバルに `ImageCleanup` が存在する設計。

### 3-4. エラー表示を生成している箇所

| ファイル | 行番号 | 内容 |
|----------|--------|------|
| templates/tools/image-cleanup.html | **873-884** | **showErrors(errors)**。**880 行**: `errorMessage.innerHTML += \`<li>${file.name}: ${message}</li>\``。ここで `message` が `ReferenceError` の `.message`（"ImageCleanup is not defined"）となる。 |

### 3-5. ImageCleanup を呼び出している script ブロックが module かどうか

- **529 行**の script タグ: **type="module" は付いていない**（該当行のみで、属性は `src="..."` のみ）。
- **533 行**のインライン script: **type="module" は付いていない**（`<script>` のみ）。

したがって、**参照側は古典的グローバルスコープ**であり、`ImageCleanup` は window 上に存在すれば参照可能な設計である（根拠: **templates/tools/image-cleanup.html:529, 533**）。

---

## 4. ブラウザ観測結果（view-source / Network / Console）

### 4-1. 本レポート作成時の自動取得

- **本番ページ**: `https://jobcan-automation.onrender.com/tools/image-cleanup` を取得したところ、**レンダリング後のテキストコンテンツ**は取得できたが、**生 HTML（view-source 相当）は取得できておらず**、`<script src="...image-cleanup.js">` の有無・属性はこのツールでは確認していない。
- **本番静的ファイル**: `https://jobcan-automation.onrender.com/static/js/image-cleanup.js` の取得は **エラー**（接続/タイムアウト/その他）。Status・Content-Type・Response 先頭の 80 文字は取得できていない。

### 4-2. 要手動確認（本番ブラウザで実施し、結果を貼る）

以下を本番環境のブラウザで実施し、結果をレポートに追記または別メモに残すと、原因の断定が可能になる。

#### 4-2-1. view-source / DOM

- [ ] image-cleanup ページで **view-source**（または「ページのソースを表示」）を開く。
- [ ] `/static/js/image-cleanup.js` を含む `<script src=...>` が **存在するか** → **Yes / No**
- [ ] その script タグに **type="module" / defer / async** が付いているか → **付いている場合、該当タグをそのまま抜粋**

例（記入用）:
```
<script src="...image-cleanup.js"...></script>
（type="module" の有無: 無 / 有）
```

#### 4-2-2. Network（最重要）

- [ ] 開発者ツールの **Network** を開き、ページを再読み込み（必要なら「Disable cache」をオン）。
- [ ] 一覧から **image-cleanup.js**（または `js/image-cleanup.js`）を特定する。
- [ ] 記録する項目:
  - **Status**: 200 / 304 / 404 / 500 / (その他)
  - **Response headers**: **Content-Type** の値
  - **Response の先頭 80 文字程度**（JS なら `/**` や `class ImageCleanup` を含む想定。HTML なら `<!doctype html>` 等）
  - **Size**: 概算で可
- [ ] 404/500 または HTML が返っている場合: Console の **Failed to load resource** 等のログがあればその全文を貼る。

例（記入用）:
```
Status: 
Content-Type: 
Response 先頭 80 文字: 
Size: 
```

#### 4-2-3. Console（最重要）

- [ ] **「ImageCleanup is not defined」より前にエラーが出ているか** → ある場合は **最初のエラーの全文**（メッセージ＋スタック）を貼る。
- [ ] 次の式を Console で実行した結果を貼る:
  - `typeof ImageCleanup` → 期待: `"function"`（class は function）。未定義なら `"undefined"`
  - `typeof window.ImageCleanup` → 同上
  - `window.ImageCleanup` → 期待: class の参照。未定義なら `undefined`
- [ ] エラー再現手順（2〜3 行）: 例「PNG を 1 枚ドロップ → 処理開始クリック → 数秒後にエラー表示」

---

## 5. 原因候補ランキング（A〜E、当てはまり/否定）

観測結果に応じて、以下を「当てはまる / 否定」で更新する。**本レポート作成時点では、自動取得では断定できていないため、ブラウザ観測後の記入を推奨する。**

| 候補 | 内容 | 当てはまり/否定 | 根拠（観測で分かること） |
|------|------|------------------|---------------------------|
| **A** | `/static/js/image-cleanup.js` がロードできていない（404/500/HTML 返却/パス不一致） | **要確認** | Network で Status が 200 以外、または Response が HTML/空。Console で `typeof ImageCleanup === "undefined"`。 |
| **B** | JS の先行エラーで `class ImageCleanup` まで到達していない（SyntaxError/ReferenceError 等） | **要確認** | Console に「ImageCleanup is not defined」より**前**のエラーがある。または image-cleanup.js の 6 行目より前で例外。 |
| **C** | スコープ問題（module 等）で参照側から `ImageCleanup` が見えていない | **コード上は否定** | テンプレートに type="module" なし（529, 533 行）。ただし **typeof window.ImageCleanup === "undefined"** かつ **他 script で ImageCleanup を window に代入していない**場合は C の可能性が残る（例: 何らかの理由でグローバルに登録されていない）。 |
| **D** | デプロイ不整合（本番配信される JS が古い/別物で class が含まれない） | **要確認** | Network で 200 だが Response 本文の先頭 80 文字に `class ImageCleanup` が含まれない。またはファイルサイズがローカルと大きく異なる。 |
| **E** | テンプレ差し替え/extends のブロック欠落で script タグが出ていない | **要確認** | view-source に `image-cleanup.js` の script タグが**無い**。 |

**コードから言えること**: E は「テンプレートに 529 行が存在し、extends で上書きされていない限り」否定できる。C は「古典 script かつ export なし」のため、**同じグローバルスコープで 529 が実行されていれば** ImageCleanup は見える設計であり、見えないなら A または B の可能性が高い。

---

## 6. 最小修正方針（原因別の最小修正案・実装はしない）

| 原因 | 最小修正案（1〜2 案） |
|------|------------------------|
| **A（404/ロード失敗）** | (1) Flask の static ルートと `static/js/image-cleanup.js` の実体の存在を確認する。本番のビルド/デプロイで当該ファイルが含まれているか、`url_for('static', filename='js/image-cleanup.js')` の出力 URL と実際のパスが一致しているかを確認する。(2) 404 の原因がキャッシュや CDN なら、キャッシュ無効化・ハードリロードの案内や、クエリ `?v=...` でバージョン付与を検討する。 |
| **B（先行エラー）** | (1) Console の「最初に表示されたエラー」のファイル名・行番号を特定し、その行を修正する（SyntaxError / ReferenceError の原因除去）。(2) image-cleanup.js の直前の script（image-style.js 等）がエラーで止まっている場合、そのファイルの修正または読み込み順の見直し。 |
| **C（スコープ）** | (1) `static/js/image-cleanup.js` の**末尾**（クラス定義の閉じ `}` の直後）に `window.ImageCleanup = ImageCleanup;` を 1 行追加し、グローバルに明示的に露出する。(2) 参照側（759, 762 行）で `(window.ImageCleanup || ImageCleanup).generateFilename(...)` のようにフォールバックするのは、原因が C の場合の暫定策として可能（推奨は (1)）。 |
| **D（デプロイ不整合）** | (1) 本番の Response 本文に `class ImageCleanup` が含まれるか確認する。含まれない場合は、デプロイ元のリポジトリ・ビルド成果物・静的ファイルのコピー先を点検する。(2) キャッシュ（ブラウザ・CDN・Render の静的配信）のクリアと再デプロイ。 |
| **E（テンプレ欠落）** | (1) view-source に script が無いことを根拠に、image-cleanup ページをレンダリングしているテンプレート（`templates/tools/image-cleanup.html`）の 521-532 行が本番に反映されているか確認する。extends や include で上書きされていないか、block の欠落がないかを確認し、529 行の script タグが必ず出力されるようにテンプレートを修正する。 |

---

## 7. 検証チェックリスト（修正後に何を確認するか）

- [ ] 本番で `/tools/image-cleanup` を開き、Network で `image-cleanup.js` が **200** で返る。
- [ ] Response の先頭に `/**` および `class ImageCleanup` が含まれる（JS であること）。
- [ ] Console で `typeof ImageCleanup` が `"function"`、`window.ImageCleanup` が定義されている。
- [ ] PNG を 1 枚投入し「処理開始」でクリーンアップが完了し、「ImageCleanup is not defined」が出ない。
- [ ] 複数ファイル（PNG/JPEG/WebP）でも同様に成功する。
- [ ] キャンセルやエラー表示（意図したエラー）が想定どおり動く。

---

## 8. 参考（ファイル・行番号一覧、観測ログ）

### 8-1. ファイル・行番号一覧

| ファイル | 行番号 | 内容 |
|----------|--------|------|
| app.py | 975-980 | `/tools/image-cleanup` ルート、`tools/image-cleanup.html` をレンダリング |
| templates/tools/image-cleanup.html | 521-532 | 共通 script 列（529 が image-cleanup.js） |
| templates/tools/image-cleanup.html | 529 | `<script src="{{ url_for('static', filename='js/image-cleanup.js') }}"></script>`（type/module/defer/async なし） |
| templates/tools/image-cleanup.html | 533 | `<script>` インライン開始（type="module" なし） |
| templates/tools/image-cleanup.html | 725, 756-784 | runCleanup、processor（ImageCleanup 参照は 759, 762） |
| templates/tools/image-cleanup.html | 878-880 | showErrors、`file.name: ${message}` でエラー表示 |
| static/js/image-cleanup.js | 1-6 | コメントと `class ImageCleanup {` |
| static/js/image-cleanup.js | 357-376 | generateFilename とクラス閉じ |

### 8-2. 観測ログ（本レポート作成時）

- 本番 `https://jobcan-automation.onrender.com/tools/image-cleanup`: ページ本文は取得済み。生 HTML/view-source 相当は未取得。
- 本番 `https://jobcan-automation.onrender.com/static/js/image-cleanup.js`: **取得エラー**（要ブラウザでの Network 確認）。

---

以上。原因を断定するには、**本番ブラウザでの 4-2（view-source / Network / Console）の実施と結果の記録**が必須である。
