# ④ Web/SEOユーティリティ 現状分析レポート v1

---

## 1. 対象とゴール（4-1〜4-3）

| ID | 課題 | ゴール |
|----|------|--------|
| 4-1 | OGP画像が生成されない | 原因を特定し、分割実装で修正できるようにする |
| 4-2 | PageSpeed改善チェックリストの「使い方説明」をUIに追加したい | 追加する説明文案と配置を決める |
| 4-3 | sitemap.xml/robots.txt生成でURLリストをユーザーに用意させず、URL入力→クロールでURL一覧自動生成→sitemap生成を検討したい | 現行要件の整理と改善案（方式A/B）・技術設計を出す |

**注意:** 本レポートではコード修正は行わない。事実と推測を区別し、断定できない点は未確認とし追加調査手順を記載する。

---

## 2. 調査手順（再現手順）

### 2.1 対象画面の特定と再現

**対象URL**
- 本番: `https://jobcan-automation.onrender.com/tools/seo`
- ローカル: `http://localhost:5000/tools/seo`（または環境に応じる）

**4-1 OGP画像が生成されない 再現手順**
1. 上記URLでWeb/SEOユーティリティを開く。
2. 左のモードで「OGP画像」を選択（初期表示の想定）。
3. **タイトル**に任意の文字列を入力（必須。未入力だと `alert('タイトルを入力してください')` で処理が止まる）。
4. 「画像を生成」ボタンをクリック → `generateOgp()` が実行され、成功時は右側の「出力」にプレビュー表示・ダウンロード可能になる。失敗時は `alert(\`OGP画像生成エラー: ${error.message}\`)` が表示される。

**本番/ローカルでの確認事項（実施推奨）**
- 本番で上記手順を実行し、OGP生成が失敗する場合:
  - **DevTools → Console**: エラー全文をコピーして記録する。
  - **DevTools → Network**: 「画像を生成」クリック前後で、失敗しているリクエスト（XHR/Fetch 等）があれば、ステータスコード・レスポンス本文を記録する。
  - 本レポート作成時点では、**本番・ローカル双方のConsole/Networkログは未取得**のため、再現手順のみ記載し、原因分析はコードベースと「想定される失敗パターン」に基づく。

**4-2 PageSpeedチェックリスト**
- モードで「PageSpeedチェックリスト」を選択 → 対象URL（任意）・目的・フレームワーク・優先指標・チェックボックスを設定 → 「チェックリストを生成」で右側にMarkdownが表示される。現行UIには「使い方説明」はない。

**4-3 sitemap/robots**
- モードで「sitemap/robots」を選択 → ベースURLと「URLリスト（1行1URLまたは1行1パス）」を手動入力 → 「sitemap.xmlを生成」「robots.txtを生成」で出力。現行はURLリストの自動収集機能はない。

---

## 3. エラーログ（Console/Network 原文）

**現時点の記載**
- **未取得**。本番またはローカルで上記「2.1」の手順を実施し、OGP生成失敗時にConsoleおよびNetworkの該当エラー・レスポンスを取得し、本レポートの「3. エラーログ」に追記することを推奨する。
- 追記例: 「本番で 2025-xx-xx に再現。Console: `Uncaught ReferenceError: SeoOgpCanvas is not defined` / Network: 特になし（すべてクライアント処理）」など。

---

## 4. 関連コードマップ（ファイル一覧と呼び出しの流れ）

### 4.1 ルート・テンプレート

| ファイル | 役割 | 該当箇所（抜粋） |
|----------|------|------------------|
| `app.py` | `/tools/seo` ルート定義 | 792-799行: `@app.route('/tools/seo')` → `tools_seo()` → `render_template('tools/seo.html', ...)` |
| `templates/tools/seo.html` | SEOツール単一ページ。左: 設定、右: 出力。モード切替で表示を切り替え | 259行〜: `#ogp-settings`, 333行〜: `#pagespeed-settings`, 425行〜: `#sitemap-settings` |

**app.py 792-799行付近**
```python
@app.route('/tools/seo')
def tools_seo():
    """Web/SEOユーティリティ"""
    from lib.routes import get_product_by_path, get_available_products
    product = get_product_by_path('/tools/seo')
    ...
    return render_template('tools/seo.html', product=product, related_products=related_products)
```

### 4.2 スクリプト読み込み順（seo.html 548-558行）

```html
<script src=".../file-validation.js"></script>
<script src=".../file-utils.js"></script>
<script src=".../minutes-export.js"></script>
<script src=".../js/seo-ogp-presets.js"></script>
<script src=".../js/seo-ogp-canvas.js"></script>
<script src=".../js/seo-ogp-export.js"></script>
<script src=".../js/seo-pagespeed-checklist.js"></script>
<script src=".../js/seo-html-inspector.js"></script>
<script src=".../js/seo-sitemap.js"></script>
<script src=".../js/seo-robots.js"></script>
```

- **OGP**: `SeoOgpPresets` → `SeoOgpCanvas` → `SeoOgpExport` の順で依存。playwright / html2canvas は未使用。

### 4.3 4-1 OGP画像生成の流れ

| ファイル | 関数/クラス | 役割 |
|----------|-------------|------|
| `templates/tools/seo.html` | `generateOgp()` | タイトル必須チェック → options 収集 → `SeoOgpExport.exportOgpImage(options)` 呼び出し。成功時は `currentOgpBlob` に格納しプレビュー表示。失敗時は `alert` |
| `static/js/seo-ogp-export.js` | `SeoOgpExport.exportOgpImage(options)` | `SeoOgpCanvas.createOgpCanvas(options)` → `SeoOgpCanvas.canvasToBlob(...)` → blob/filename/mime を返す |
| `static/js/seo-ogp-canvas.js` | `SeoOgpCanvas.createOgpCanvas(options)` | `SeoOgpPresets.getPresetById(options.presetId)` でサイズ取得 → Canvas作成 → `drawOgp` で描画（fillRect/fillText のみ、外部画像なし） |
| `static/js/seo-ogp-canvas.js` | `SeoOgpCanvas.canvasToBlob(canvas, format, quality)` | `canvas.toBlob(callback, mimeType, quality)` で Blob 化。blob が null の場合は `reject(new Error('画像変換に失敗しました'))` |
| `static/js/seo-ogp-presets.js` | `SeoOgpPresets.getPresetById(id)` | プリセット定義から width/height 等を返す。無効IDなら null の想定 |

**seo.html 602-641行付近（generateOgp）**
```javascript
async function generateOgp() {
    const title = document.getElementById('ogp-title').value.trim();
    if (!title) {
        alert('タイトルを入力してください');
        return;
    }
    const options = { presetId: ..., title, ... };
    try {
        const result = await SeoOgpExport.exportOgpImage(options);
        currentOgpBlob = result.blob;
        // プレビュー表示
        ...
    } catch (error) {
        alert(`OGP画像生成エラー: ${error.message}`);
    }
}
```

**seo-ogp-canvas.js 177-198行付近（canvasToBlob）**
```javascript
static async canvasToBlob(canvas, format = 'png', quality = 0.9) {
    return new Promise((resolve, reject) => {
        const mimeType = format === 'jpeg' || format === 'jpg' ? 'image/jpeg' : 'image/png';
        ...
        canvas.toBlob(
            (blob) => {
                if (blob) resolve(blob);
                else reject(new Error('画像変換に失敗しました'));
            },
            mimeType,
            options.quality
        );
    });
}
```

### 4.4 4-2 PageSpeedチェックリストの流れ

| ファイル | 関数/クラス | 役割 |
|----------|-------------|------|
| `templates/tools/seo.html` | `generateChecklist()` | 671-691行: フォームから options を収集 → `SeoPageSpeedChecklist.buildChecklistMarkdown(options)` → `#pagespeed-preview` に `<pre>` で表示。コピー/ダウンロードは `currentChecklist` を利用 |
| `static/js/seo-pagespeed-checklist.js` | `SeoPageSpeedChecklist.buildChecklistMarkdown(options)` | 目的・フレームワーク・優先指標に応じたMarkdownチェックリストを生成（Core Web Vitals、画像/フォント/JS・CSS/キャッシュ/外部スクリプト等）。**PageSpeed InsightsやLighthouseの計測は行わず、テンプレートベースのチェックリストのみ** |

- **実装の所在**: すべて**クライアント側**。サーバAPIなし。

### 4.5 4-3 sitemap/robots の流れ

| ファイル | 関数/クラス | 役割 |
|----------|-------------|------|
| `templates/tools/seo.html` | `#sitemap-url-list` (textarea) | 432行: 「URLリスト（1行1URLまたは1行1パス）」を**ユーザーが手動入力**。434行: パス/完全URL、空行・#コメント行は無視の説明 |
| `templates/tools/seo.html` | `generateSitemap()` | テキストエリアとベースURLから `SeoSitemap.normalizeUrls(baseUrl, urlList)` を呼び出し、得た `urls` で `SeoSitemap.buildSitemapXml(...)` → 出力エリアに表示・ダウンロード |
| `static/js/seo-sitemap.js` | `SeoSitemap.normalizeUrls(baseUrl, urlList)` | 12-82行: 1行1URL/1行1パスをパース。ベースURLと結合して重複排除・ソート。無効行は warnings に追加 |
| `static/js/seo-sitemap.js` | `SeoSitemap.buildSitemapXml(urls, options)` | 94-127行: urlset 形式の XML 文字列を生成 |

- **実装の所在**: すべて**クライアント側**。URLの取得・クロールは行っていない。

### 4.6 検索で確認したキーワードと結果

| 検索語 | ヒット概要 | クライアント/サーバ |
|--------|------------|---------------------|
| ogp / OGP / open graph | `seo.html`（OGP設定・ボタン・出力）、`seo-ogp-presets.js`、`seo-ogp-canvas.js`、`seo-ogp-export.js` | すべてクライアント |
| sitemap / robots.txt | `seo.html`（sitemap/robots設定・出力）、`seo-sitemap.js`、`seo-robots.js` | すべてクライアント |
| pagespeed / lighthouse / checklist | `seo.html`（PageSpeed設定・生成ボタン）、`seo-pagespeed-checklist.js` | すべてクライアント。Lighthouse API は未使用 |
| playwright | リポジトリ内にヒットなし | - |
| html2canvas | リポジトリ内にヒットなし | - |
| /tools/seo | `app.py` 792行 | サーバはルートとテンプレート返却のみ |

---

## 5. 4-1 OGP画像が生成されない 原因分析（事実/仮説/検証/結論）

### 5.1 事実（コードから確定できること）

- **生成方式**: クライアント側の **HTML5 Canvas API**（`getContext('2d')`、`fillRect`/`fillText`、`canvas.toBlob()`）。playwright・html2canvas・サーバ側スクショ・テンプレ画像合成は使っていない。
- **描画内容**: 外部画像の読み込みは行っていない。背景色・グラデーション・テキストのみのため、**CORS/tainted canvas による toBlob 失敗の可能性は低い**。
- **エラー露出**: 例外は `generateOgp()` の `catch` で `alert(\`OGP画像生成エラー: ${error.message}\`)` として表示される。
- **必須入力**: タイトル未入力の場合は `alert('タイトルを入力してください')` で処理が止まり、OGP生成処理には入らない。

### 5.2 仮説（失敗原因の候補）

1. **スクリプトのロード/実行失敗**
   - `seo-ogp-presets.js` / `seo-ogp-canvas.js` / `seo-ogp-export.js` のいずれかが 404 や構文エラーで読み込めず、`SeoOgpPresets` / `SeoOgpCanvas` / `SeoOgpExport` が未定義になる。
   - その状態で「画像を生成」を押すと `SeoOgpExport.exportOgpImage` 呼び出しで `Uncaught ReferenceError` となり、ユーザーには「OGP画像生成エラー: ...」と出る。

2. **無効なプリセットID**
   - `SeoOgpPresets.getPresetById(options.presetId)` が null を返す場合、`seo-ogp-canvas.js` の `createOgpCanvas` 内で `throw new Error('無効なプリセットIDです')` が発生する。
   - UIの `<select id="ogp-preset">` の value とプリセットIDが一致している限りは起きにくいが、初期値欠落や別タブでのDOM操作などでずれる可能性はある。

3. **canvas.toBlob が null を返す**
   - ブラウザやセキュリティ設定によっては `toBlob` のコールバックで blob が null になる場合がある。その場合 `reject(new Error('画像変換に失敗しました'))` となり、メッセージがそのまま alert に出る。

4. **ユーザー認識**
   - タイトル未入力で「画像を生成」を押し、「タイトルを入力してください」を見て「OGP画像が生成されない」と感じている可能性。

### 5.3 検証（推奨する確認）

- **Console ログ**: 本番またはローカルで「画像を生成」実行時のエラー全文を取得する（例: `ReferenceError`, `TypeError`, 「画像変換に失敗しました」）。
- **Network**: 本ツールはOGP生成にサーバリクエストを使っていないため、OGP用の 4xx/5xx は想定しにくい。念のため「画像を生成」前後のリクエストで失敗がないか確認する。
- **スクリプトの存在**: 本番の `/static/js/seo-ogp-presets.js` 等が 200 で返っているか確認する。

### 5.4 結論

- **コード上、最も筋が良い失敗原因**は、**いずれかのOGP用スクリプトが読み込めず `SeoOgpExport` 等が未定義になり、`generateOgp()` 内で ReferenceError が発生している**パターン。
- 実際の環境でConsoleに `SeoOgpCanvas is not defined` 等が出ていれば、そのスクリプトの配信経路（パス・CDN・キャッシュ）の確認が有効。
- **断定はしない**: Console/Network の実ログがないため「未確認」とし、上記検証を実施したうえで原因を確定することを推奨する。

---

## 6. 4-2 PageSpeedチェックリスト 使い方説明の追加案（UI文案付き）

### 6.1 現行の出力のされ方・形式

- **表示場所**: 右パネル `#pagespeed-output` 内の `#pagespeed-preview`。`generateChecklist()` で生成した Markdown を `<pre>` に `textContent` で表示。
- **形式**: Markdown（見出し・リスト）。内容は `SeoPageSpeedChecklist.buildChecklistMarkdown(options)` によるテンプレートベース（Core Web Vitals、画像/フォント/JS・CSS/キャッシュ/外部スクリプト、目的・フレームワーク別の節）。**PageSpeed Insights / Lighthouse の実測値は使っておらず、一般的な改善項目のチェックリスト**。
- **出力**: 「コピー」「Markdownをダウンロード」でクリップボードまたは `.md` ファイルとして利用可能。

### 6.2 ユーザーが詰まりそうなポイント

- このチェックリストを**どこで計測するか**（PageSpeed Insights / Lighthouse / Chrome DevTools）が書かれていない。
- **優先順位**（どの指標を先に対応すべきか）が画面内では説明されていない。
- チェックリストを**どう使うか**（計測 → 項目に沿って対応 → 再計測で確認）の流れが明示されていない。
- 「対象URL」が任意のため、**URLを入れないとチェックリストだけが生成され、実サイトと紐づけて使うイメージが持ちにくい**可能性。

### 6.3 追加する説明文案（案）

以下はツール説明用の短文。配置案は次節。

**短文（ツール説明パネルやページ上部用）**
```text
このチェックリストは、PageSpeed Insights や Lighthouse で計測した結果を改善するための「やるべきこと」をまとめたものです。使い方の流れ: (1) 対象URLで PageSpeed Insights または Lighthouse を実行してスコアを確認 (2) このツールで目的・フレームワークに合わせてチェックリストを生成 (3) リストに沿って対応（画像最適化・フォント・キャッシュ等） (4) 再度計測して改善を確認してください。対象URLはチェックリストのメモ用で任意入力です。
```

**もう少し短いラベル（結果エリアの直上など）**
```text
使い方: PageSpeed Insights / Lighthouse で計測 → このチェックリストで改善項目を確認 → 対応後に再計測で確認。
```

### 6.4 追加場所の提案

| 案 | 場所 | 内容 |
|----|------|------|
| A | ページ上部（ツール名の下） | 上記「短文」を常時表示。全モード共通の説明としても使える |
| B | PageSpeedモードの左設定エリアの先頭 | `#pagespeed-settings` の先頭に「使い方」折りたたみまたは常時表示で「短文」を配置。OGP/メタ/sitemap には出さない |
| C | 右側「出力」の、チェックリスト結果の直上 | 「使い方」の短いラベル（2行程度）を表示。生成ボタンを押したあと結果を見るユーザーに届きやすい |

**推奨**: **B + C**。左で「何に使うツールか」を説明し、右で「得たチェックリストをどう使うか」を短く補足する。

---

## 7. 4-3 sitemap/robots 自動URL収集案（方式A/B、制約、実装方針）

### 7.1 現行の入力要件と実装箇所

- **入力**: `templates/tools/seo.html` の `#sitemap-base-url`（ベースURL）と `#sitemap-url-list`（textarea、1行1URL または 1行1パス）。コメント行（#）と空行は無視。
- **処理**: クライアントで `SeoSitemap.normalizeUrls(baseUrl, urlList)` → `SeoSitemap.buildSitemapXml(urls, options)`。サーバAPIはなし。
- **要件**: ユーザーが**自前でURL一覧を用意**する必要がある。

### 7.2 改善案

**方式A: URLを1つ入力 → 同一ドメイン内をクロールしてURL一覧生成 → sitemap生成**

- ユーザーが「開始URL」を1つ入力する。
- サーバ側でそのURLを起点に、同一ドメイン内のみをクロール（最大URL数・深さを制限）してURL一覧を取得。
- 得た一覧を既存の sitemap 生成パイプライン（`normalizeUrls` 相当の正規化 → `buildSitemapXml`）に渡して sitemap.xml を生成。
- **メリット**: 入力が1URLで済む。**デメリット**: クロールの実装・負荷・タイムアウト・robots.txt 尊重などの設計が必要。

**方式B: URL入力 ＋ 既存 sitemap.xml の検出 → 不足分をクロールで補完**

- ユーザーが開始URLを入力。
- まず `https://{domain}/sitemap.xml`（または既知のsitemap URL）にGETして、存在すればその中から `<loc>` を抽出してURL一覧の初期値とする。
- 必要に応じて同一ドメイン内をクロールして不足分を補い、重複排除したうえで sitemap 生成。
- **メリット**: 既に sitemap があるサイトでは負荷が少ない。**デメリット**: sitemap のパースと、クロールとの重複排除・優先順位のルールが必要。

### 7.3 技術設計（安全策込み）

- **クロール範囲**
  - **同一オリジン/同一ドメインに限定**: 開始URLのホストと異なるドメインへのリンクは追わない。
  - **最大URL数**: 例 500〜1000 で上限を設ける。
  - **深さ制限**: 開始URLを深さ0とし、リンクをたどる深さに上限（例 3〜5）を設ける。
  - **除外**: クエリパラメータを除外するオプション、特定拡張子（.pdf, .zip 等）を除外するオプションを検討。
- **robots.txt**
  - **最低限**: クロール前に `https://{domain}/robots.txt` を取得し、`Disallow` に含まれるパスはクロール対象から外すことを推奨。完全準拠でなくとも、同一ドメイン内に限定しつつ主要な禁止パスを尊重する程度でよい。
- **実行環境**
  - **サーバ側で実行することを推奨**: クロールは複数HTTPリクエストが必要で、クライアントから他ドメインに多数リクエストするとCORS・レート制限・同一オリジンポリシーの制約が厳しい。サーバ側なら requests + BeautifulSoup（または lxml）等で実装しやすい。
- **その他**
  - **タイムアウト**: 1リクエストあたり 5〜10秒、全体で 60〜120秒 など上限を設ける。
  - **並列数**: 同一ドメインへの負荷を考慮し、並列数に上限（例 2〜5）を設ける。
  - **重複排除**: 正規化したURL（末尾スラッシュ統一等）で Set 管理。
- **依存**
  - サーバ側: `requests`、`beautifulsoup4` または `lxml`。Render 等の実行環境でネットワークアクセスが許可されているか要確認。必要なら `urllib.robotparser` で robots.txt 解釈。

### 7.4 結論

- 現行は**URLリストをユーザーが手で用意**する前提。自動化するなら**サーバ側でクロール（＋必要なら既存 sitemap 取得）を実装する**のが現実的。
- 方式Aは「常にクロールで一から取得」、方式Bは「sitemap があれば利用し、不足分だけクロール」という違い。まず方式Aでシンプルに実装し、のちに方式B（sitemap 検出）を足す構成もあり。
- クロールは**同一ドメイン・最大URL数・深さ・タイムアウト・robots.txt の簡易尊重**を必須とし、実装時は DoD に「クロール範囲と制限」を明記することを推奨する。

---

## 8. 受け入れ条件（DoD）

- **4-1**
  - 本番またはローカルでOGP生成を実行し、失敗時に Console/Network のエラーを取得し、レポートまたはチケットに記録していること。
  - 原因が特定できた場合、その原因に基づく修正案（コード修正は別PRで可）を記載していること。
- **4-2**
  - PageSpeedチェックリストについて「使い方説明」の文案（短文および短いラベル）を決め、追加場所（少なくとも1案）を選んでいること。
  - 実装時は、選んだ場所に上記文案を反映する。
- **4-3**
  - sitemap/robots の現行入力要件（1行1URL等）と実装箇所を文書化していること（本レポートで対応済み）。
  - 方式AまたはBのいずれか（または両方）について、クロール範囲・最大URL数・深さ・タイムアウト・robots.txt の扱いを設計に含めること。
  - クロールはサーバ側で実装する方針であることを合意していること。

---

## 9. 次ステップ（4-1の実装用 Cursor プロンプト案）

**4-1 OGP画像が生成されない 修正用（短いプロンプト）**

```text
本番の /tools/seo で「OGP画像」を選択し、タイトルを入力して「画像を生成」を押すとOGP画像が生成されない。Console では [ここに実ログを貼る] が出ている。原因を特定し、static/js の seo-ogp-*.js の読み込み順序や export/Canvas のエラーハンドリングを修正して、生成が成功するようにしてほしい。修正後はプレビュー表示とダウンロードができることを確認すること。
```

（実際にログを取得したら `[ここに実ログを貼る]` を置き換えて使用する。）

---

以上、④ Web/SEOユーティリティ 現状分析レポート v1 とする。
