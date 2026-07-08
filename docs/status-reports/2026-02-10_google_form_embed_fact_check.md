# Google Form 埋め込み 事実確認・実装方針

**日付**: 2026-02-10  
**目的**: LP（/autofill）からリンクしている Google Form を外部遷移ではなく埋め込みにしたい。現状の実装箇所と制約を事実ベースで特定し、変更最小の実装方針を選べる情報を揃える。

---

## A. 事実（ファイル:行番号）

### ルーティング

- **/autofill**: app.py 910–914 行。`@app.route('/autofill')` → `render_template('autofill.html')`
- **/contact**: app.py 937–940 行。`@app.route('/contact')` → `render_template('contact.html')`

### テンプレート（render 先）

- **/autofill**: templates/autofill.html
- **/contact**: templates/contact.html

### 「お問い合わせフォームへ」リンク（/autofill 側）

- **templates/autofill.html 950 行**: `<a href="/contact" ...>お問い合わせフォームへ</a>`（同一ページ内の CTA セクション）

### /contact の Google Form リンク

- **templates/contact.html 131 行**: `<a href="https://docs.google.com/forms/d/e/1FAIpQLSfAV8D2vxo7sCIvd3z9_1PBbFf3wLpST_bA8Y-P0Ab6WRM3gQ/viewform?usp=publish-editor" target="_blank" ...>お問い合わせフォームを開く</a>`
- **templates/contact.html 133 行**: 注釈「※ Googleフォームを使用しています。外部サイトに移動します。」

### 現行の Google Form URL（フォームID）

- **URL（閲覧用）**: `https://docs.google.com/forms/d/e/1FAIpQLSfAV8D2vxo7sCIvd3z9_1PBbFf3wLpST_bA8Y-P0Ab6WRM3gQ/viewform?usp=publish-editor`
- **埋め込み用 URL（Google の慣例）**: `https://docs.google.com/forms/d/e/1FAIpQLSfAV8D2vxo7sCIvd3z9_1PBbFf3wLpST_bA8Y-P0Ab6WRM3gQ/viewform?embedded=true`  
  （`embedded=true` を付与すると iframe 用のレスポンスになる）

### セキュリティヘッダ（コード上）

- **Content-Security-Policy**: app.py 内に設定なし（検索: Content-Security-Policy → 0 件）
- **X-Frame-Options**: app.py 内に設定なし（検索: X-Frame-Options → 0 件）
- **after_request で付与しているヘッダ**: app.py 134–139 行（X-Request-ID）、396–402 行（X-Robots-Tag のみ。特定パス用）。frame 関連の付与なし。
- **結論**: 自サイトが iframe で docs.google.com を表示することを妨げるヘッダはコード上ない。将来 CSP を付ける場合は `frame-src` に `https://docs.google.com` を許容する必要がある。

### 共通 head（head_meta.html）で読み込む外部 script

- **templates/includes/head_meta.html** を contact.html / autofill.html はいずれも 5 行で `{% include 'includes/head_meta.html' %}` している（contact.html 5 行、autofill.html は head 内で include）。
- **head_meta.html 内の外部読み込み**:
  - 2–14 行: GA4（gtag.js）— `GA_MEASUREMENT_ID` がある場合のみ。googletagmanager.com
  - 47–48 行: AdSense（adsbygoogle.js）— 全ページ。pagead2.googlesyndication.com
  - 51–52 行: Google Fonts（preconnect + css）。fonts.googleapis.com / fonts.gstatic.com
- **結論**: /contact と /autofill は同じ head_meta を include しており、GA4（環境変数次第）・AdSense・Fonts が乗る。iframe 埋め込みそのものをブロックする script はない。

### UX 上の制約（テンプレ構造）

- **contact.html**: .container は max-width: 900px、padding: 50px（19–24 行）。footer は 218 行で `{% include 'includes/footer.html' %}`。iframe を入れる場合、.contact-methods 内（119–155 行）の「お問い合わせフォーム（推奨）」ブロックの直下か、ブロック内に置くのが自然。親コンテナの幅は 900px 以内で、padding により実表示幅はさらに狭い。モバイルでは viewport 幅いっぱいになるため、iframe に min-height（例: 500px〜800px）を指定しないと高さ不足になりやすい。
- **autofill.html**: 950 行付近は CTA セクション（944–952 行）。ここに iframe を置くと LP が重くなり、初回表示が遅れる可能性がある。折りたたみや「フォームを表示」ボタンで遅延読み込み（lazy）にすると軽量化できる（推測）。

---

## B. 実装案（2案）

### 案1: /contact に埋め込み（最小差分）

**概要**: /contact の「お問い合わせフォームを開く」リンクを残しつつ、その直上または直下に同一フォームの iframe を追加する。外部リンクは「新しいタブで開く」のフォールバックとして残す。

**推測**: ユーザーは /autofill → 「お問い合わせフォームへ」→ /contact に遷移したあと、同じページ内でフォームを閲覧・入力できる。遷移先は変わらないため、LP（autofill）の変更は不要。変更は contact 1 ファイルに集中する。

**変更ファイル候補**:
- **templates/contact.html**
  - 131 行付近: 既存の `<a href="...viewform?usp=publish-editor" target="_blank">` の直上に、`<iframe>` を追加。`src="https://docs.google.com/forms/d/e/1FAIpQLSfAV8D2vxo7sCIvd3z9_1PBbFf3wLpST_bA8Y-P0Ab6WRM3gQ/viewform?embedded=true"`、width 100%、min-height 例 600px（または 80vh）、border 0、loading="lazy" を指定。
  - 133 行の注釈を「※ 下のフォームは Google フォームです。別タブで開く場合は上のリンクから。」のように文言調整。
  - 必要なら .contact-method 内に .form-embed-wrap のようなラッパーを追加し、iframe に max-width: 100%、overflow: hidden をかけてレイアウト崩れを防ぐ。
- **app.py**: 変更不要（ルート・ヘッダとも現状のままで埋め込み可能）。

**受け入れ基準**: /contact を開いたとき、同一ページ内に Google Form が表示され、送信まで完了できること。モバイルで高さが切れないこと（min-height または vh で調整）。「お問い合わせフォームを開く」で別タブも開けること。

---

### 案2: /autofill に埋め込み（LP 完結・lazy/折りたたみ推奨）

**概要**: /autofill の CTA セクション（950 行付近）に、Google Form の iframe を配置する。LP で完結するが、iframe の読み込みで初回表示が重くなるため、折りたたみまたは「お問い合わせフォームを表示」ボタンで遅延表示（lazy）にする案。

**推測**: 「お問い合わせフォームへ」を「フォームをこのページで表示」に変え、クリックで iframe を挿入するか、アコーディオンで表示する。または初回から iframe を置き、`loading="lazy"` のみで軽量化する（効果は限定的）。LP が重くなるため、lazy または折りたたみのいずれかを推奨。

**変更ファイル候補**:
- **templates/autofill.html**
  - 944–952 行の CTA セクション: 「お問い合わせフォームへ」リンクの代わりに、またはリンクの下に「フォームを表示」ボタンと、非表示の `<div id="form-embed-wrap">` を用意。ボタン押下で `<iframe src="...?embedded=true" ...>` を挿入するか、既に iframe を置いておき display: none → block に切り替える。iframe の src は 案1 と同じ。
  - 必要なら .container または main の幅・padding の影響を受けないよう、iframe 用ラッパーのスタイルを追加（max-width: 100%, min-height: 500px 等）。
- **templates/contact.html**: 案2 のみ実施する場合は変更不要。案1 と併用する場合は、/contact にも埋め込みを入れてよい。
- **app.py**: 変更不要。

**受け入れ基準**: /autofill で「フォームを表示」等の操作後に、同一ページ内で Google Form が表示・送信できること。初回表示で iframe を読み込まない場合は、LP の LCP 等が悪化しないこと。

---

## 埋め込み可否の補足（Google 側）

- Google Forms の「送信」で「リンクを送信」を選び、表示される URL の末尾に `?embedded=true` を付けた URL を iframe の `src` にすると、埋め込み用のレスポンスが返る（公式ドキュメント・一般的な運用に基づく。本番フォームの設定が「埋め込みを許可」になっているかは、ブラウザで該当 URL を開いて確認する必要がある）。

---

## 変更ファイル一覧（案ごと）

| 案 | 変更するファイル |
|----|------------------|
| 案1（/contact に埋め込み） | templates/contact.html |
| 案2（/autofill に埋め込み） | templates/autofill.html |

案1 と案2 を両方実施する場合: 上記 2 ファイル。案1 のみなら contact.html のみで済む。
