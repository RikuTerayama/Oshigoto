# GSC「クロール済み - インデックス未登録」6URL ページ別改善案特定レポート（Step 3）

**作成日**: 2026-02-26  
**対象**: 本リポジトリ（Flask サイト）  
**目的**: 未登録6URLについて、コードとテンプレートから原因を特定し、最小差分で改善できる具体策をページ別に提示する（**本ステップでは実装しない。現状分析レポートのみ**）

---

## 対象6URL（GSCの例）

| # | URL | 前回のクロール |
|---|-----|----------------|
| 1 | https://jobcan-automation.onrender.com/best-practices | 2026/02/23 |
| 2 | https://jobcan-automation.onrender.com/privacy | 2026/02/20 |
| 3 | https://jobcan-automation.onrender.com/blog | 2026/02/20 |
| 4 | https://jobcan-automation.onrender.com/guide/excel-format | 2026/02/18 |
| 5 | https://jobcan-automation.onrender.com/ | 2026/01/21 |
| 6 | https://jobcan-automation.onrender.com/glossary | 2025/11/14 |

---

## 1. 結論サマリ（最大7行）

- 6URLはいずれも技術面（status 200、noindex なし、canonical 自己参照）は問題なし。コンテンツの「付加価値の明示」と「導線の強化」が共通の改善軸となる。
- **LP（/）**：最終クロールが1月21日と古く、トップからの主要ハブ（/guide, /blog）への明示導線が hero 直下に無い。
- **best-practices / privacy / blog / guide/excel-format / glossary**：冒頭で「誰の何を解決するか」が一文で伝わる強化と、トップ・ハブからのリンクの見直しが有効。
- **glossary**：クロールが 2025/11 と最も古く、トップ・trust セクションからの導線が弱い可能性。カテゴリ導線や代表用語へのショートカットで独自性を高める余地あり。
- **横断案**：トップに主要ハブ（/guide, /blog, /glossary）の明示導線を追加、各ハブで「このページの価値」を一文で補強する。

---

## 2. ページ別診断

### 2-1 URL: /best-practices

**役割の一文定義**  
「Jobcan AutoFill を安全・効果的に使うための運用ルールとチェックリストをまとめた実践ガイド（入口ハブ）」

**現状の弱点**

| 観点 | 所見 |
|------|------|
| **技術** | status 200、noindex なし、canonical 自己参照。問題なし。 |
| **コンテンツ** | H1 と冒頭はあるが「誰の何を解決するか」がやや抽象的。「月次締めを効率化したい担当者向けの実践チェック」と明示すると意図が伝わる。 |
| **導線** | ナビ・フッターにリンクあり（Step1対応済み）。LP の trust セクションからもリンクあり。ブログから「ベストプラクティス」へのリンクあり。 |
| **役割** | 運用ガイドの入口としての役割は明確。内容は十分あるが、冒頭での価値提示が弱い。 |

**改善案（P0 / P1 / P2）**

- **P0**：H1 直下のリードに「月次締めを効率化したい担当者向けに、Excel準備・セキュリティ・Jobcan側設定・エラー対処のポイントをチェック形式でまとめています」と1文追加する。
- **P1**：末尾のナビリンクに「導入事例一覧」へのリンクを1本追加し、事例との相互導線を強化する。
- **P2**：各セクションの冒頭に「この章で分かること」を1行で補足する（任意）。

**証拠**

- ルート: `app.py` 1368行 `@app.route('/best-practices')`
- テンプレ: `templates/best-practices.html`
- インクルード: `includes/head_meta.html`, `header.html`, `breadcrumb.html`, `footer.html`
- 冒頭（36行）: `<p>Jobcan AutoFillを効果的に活用するための、実践的なベストプラクティスをご紹介します。...`

---

### 2-2 URL: /privacy

**役割の一文定義**  
「個人情報・Cookie・広告配信の取り扱いを説明する法的必須ページ」

**現状の弱点**

| 観点 | 所見 |
|------|------|
| **技術** | status 200、noindex なし、canonical 自己参照。問題なし。 |
| **コンテンツ** | 必須項目は揃っている。一般的なプライバシーポリシーと差別化しづらく、「低付加価値」と見なされやすい。 |
| **導線** | ナビ・フッター・LP の trust セクションからリンクあり。 |
| **役割** | 法務ページとしての役割は明確。コンテンツそのものの差別化は難しいが、冒頭で「本サービス固有の取り扱い」を強調する余地あり。 |

**改善案（P0 / P1 / P2）**

- **P0**：「1. はじめに」の直後に「本サービスでは、Jobcan AutoFill ではサーバー一時処理、その他ツールはブラウザ内処理のみと、機能ごとに処理方式が異なります。本ポリシーで各機能の取り扱いを区別して説明しています」と1〜2文追加する。
- **P1**：LP・footer からの到達性は十分。追加の導線は不要。
- **P2**：最終更新日を実際の更新日に合わせて維持する。

**証拠**

- ルート: `app.py` 1009行 `@app.route('/privacy')`
- テンプレ: `templates/privacy.html`
- 冒頭（82–84行）: `1. はじめに`、`Jobcan AutoFill（以下「本サービス」）は...`

---

### 2-3 URL: /blog

**役割の一文定義**  
「勤怠自動化・DX・運用ノウハウの記事を一覧するコンテンツハブ」

**現状の弱点**

| 観点 | 所見 |
|------|------|
| **技術** | status 200、noindex なし、canonical 自己参照。問題なし。 |
| **コンテンツ** | H1・2段落のリード・カテゴリ3ブロック・最新記事カードあり。「コンテンツハブ」としての意図はあるが、記事リンクが主で一覧型の薄さリスクがある。 |
| **導線** | ナビ・フッター・LP trust からリンクあり。LP の hero 直下には /tools と /guide/excel-format のみで /blog は無い。 |
| **役割** | ハブとしての役割は明確。カテゴリ説明はあるが、「検索で辿り着いた人が得られること」を一言で補強する余地あり。 |

**改善案（P0 / P1 / P2）**

- **P0**：H1 直下のリードの直前に「勤怠管理の自動化・月末締めの効率化・社内展開のヒントを、開発者視点の記事で解説しています」と1文追加する。
- **P1**：LP の hero 直下のリンク群に「ブログ」を追加し、トップから 1 クリックで到達できるようにする。
- **P2**：「導入事例」セクションまたはリンクを1本追加し、/case-studies への導線を強化する。

**証拠**

- ルート: `app.py` 1386行 `@app.route('/blog')`、`return render_template('blog/index.html')`
- テンプレ: `templates/blog/index.html`
- 冒頭（14–18行）: H1、リード2段落、Excel形式・ベストプラクティス・ツール一覧への誘導
- LP（318行）: trust セクションで blog・glossary・guide/excel-format・best-practices へのリンクあり

---

### 2-4 URL: /guide/excel-format

**役割の一文定義**  
「Jobcan AutoFill 用 Excel の正しい書き方とよくあるエラーを解説する形式ガイド」

**現状の弱点**

| 観点 | 所見 |
|------|------|
| **技術** | status 200、noindex なし、canonical 自己参照。問題なし。 |
| **コンテンツ** | H1・目的の明示・ファイル構造・例表・注意点・エラー対策あり。他ガイドと似た構造だが、内容は独自で十分。 |
| **導線** | ナビ・フッター・LP・ブログ・ツール一覧・best-practices・glossary からリンクあり。導線は十分。 |
| **役割** | 形式ガイドとしての役割は明確。冒頭の「このガイドの目的」で意図は伝わる。 |

**改善案（P0 / P1 / P2）**

- **P0**：H1 直下の「このガイドの目的」の前に「形式エラーでつまずきやすいポイントに絞り、日付・時刻の正しい書き方と NG 例を具体的に説明します」と1文追加する。
- **P1**：目次またはアンカーリンクを冒頭に追加し、長文の構造を伝えやすくする（任意）。
- **P2**：トラブルシューティングとの相互リンクは既にある。追加は不要。

**証拠**

- ルート: `app.py` 1047行 `@app.route('/guide/excel-format')`
- テンプレ: `templates/guide/excel-format.html`
- 冒頭（152–153行）: info-box、H1「Excelファイルの作成方法」、「このガイドの目的: 日付・時刻の形式...」

---

### 2-5 URL: /

**役割の一文定義**  
「業務効率化ツールの入口。Jobcan 自動入力・画像・PDF 等のツールを紹介する LP」

**現状の弱点**

| 観点 | 所見 |
|------|------|
| **技術** | status 200、noindex なし、canonical 自己参照。問題なし。hero 等に data-reveal はあるが、初期 HTML に H1・説明・製品カードは含まれる。 |
| **コンテンツ** | H1「業務効率化ツール集」、hero リード、製品グリッド、ユースケース、trust セクションあり。入口としての役割は明確。 |
| **導線** | hero 直下は「ツール一覧」「Excel形式ガイド」のみ。/guide（ガイド一覧）、/blog、/glossary は trust セクション以降にしか無い。トップで主要ハブへの明示導線が弱い。 |
| **役割** | クロール日が 2026/01/21 と古く、インデックス優先度が低い可能性。 |

**改善案（P0 / P1 / P2）**

- **P0**：hero のリード文に「使い方の解説は<a href="/guide">ガイド一覧</a>、事例・ノウハウは<a href="/blog">ブログ</a>・<a href="/glossary">用語集</a>もご利用ください」と1文追加する（既存のツール・Excel形式のリンクに続けて）。
- **P1**：製品グリッド直下かユースケース直前に、「はじめての方は<a href="/guide/getting-started">はじめての使い方</a>、形式で困った方は<a href="/guide/excel-format">Excel形式ガイド</a>から」のような短い導線ブロックを追加する。
- **P2**：trust セクションのリンク群に「導入事例」を追加し、/case-studies への導線を補強する。

**証拠**

- ルート: `app.py` 882行 `@app.route('/')`、905行 `return render_template('landing.html', products=products)`
- テンプレ: `templates/landing.html`
- hero（255–257行）: H1、リード「日々の業務を効率化する...」、/tools・/guide/excel-format へのリンク
- trust（318行）: privacy・blog・glossary・guide/excel-format・best-practices へのリンク

---

### 2-6 URL: /glossary

**役割の一文定義**  
「勤怠管理・Jobcan AutoFill の用語を解説する辞書型ページ」

**現状の弱点**

| 観点 | 所見 |
|------|------|
| **技術** | status 200、noindex なし、canonical 自己参照。問題なし。 |
| **コンテンツ** | H1・冒頭2段落・H2 カテゴリ・term-item（用語名・読み・定義・例）あり。用語の羅列になりがちだが、各項に「本ツールでは...」とサービス固有の説明を入れている。 |
| **導線** | ナビ・フッター・LP trust・ブログ・guide/excel-format からリンクあり。ただし LP の hero 直下には無く、trust セクションのみ。クロールが 2025/11 と最も古く、重要度シグナルが弱い可能性。 |
| **役割** | 辞書型ページとしての役割は明確。カテゴリ導線や代表用語へのショートカットが無く、一覧の価値が伝わりにくい。 |

**改善案（P0 / P1 / P2）**

- **P0**：H1 直下のリードに「打刻・開始時刻・終了時刻・テンプレートなど、導入検討や社内説明で使う代表的な用語を、このページからすぐに確認できます」と1文追加する。
- **P1**：H2 の前に「よく参照される用語：勤怠管理、打刻、開始時刻、終了時刻、テンプレートファイル、打刻修正」のようなショートカットリンク（アンカー）を1行追加する。
- **P2**：LP の hero 直下か製品一覧付近に「用語集」へのリンクを1本追加し、トップからの導線を強化する。

**証拠**

- ルート: `app.py` 1361行 `@app.route('/glossary')`
- テンプレ: `templates/glossary.html`
- 冒頭（98–101行）: H1「勤怠管理・Jobcan用語集」、2段落のリード、guide/excel-format・best-practices・faq への誘導
- H2（102行）: 「勤怠管理の基本用語」、以降「Jobcan関連用語」「Jobcan AutoFill関連用語」「IT・セキュリティ用語」

---

## 3. 横断改善案（最大5件）

| # | 改善案 | 対象ページ | 効果 |
|---|--------|------------|------|
| 1 | **トップ（LP）の hero 直下に主要ハブへの明示導線を追加** | / | /guide、/blog、/glossary を hero から 1 クリックで到達可能にし、トップの重要度シグナルを強化。 |
| 2 | **各ハブの冒頭に「このページで分かること」を1文追加** | /blog, /best-practices, /glossary, /guide/excel-format | 検索意図との整合を明確にし、付加価値の判断をしやすくする。 |
| 3 | **glossary に代表用語へのショートカットを追加** | /glossary | 辞書ページの利便性と構造を伝え、薄いコンテンツ判定を軽減する。 |
| 4 | **blog に「導入事例」へのリンクを1本追加** | /blog | /case-studies との相互導線を強化し、事例ページの重要度シグナルを高める。 |
| 5 | **trust セクションに「導入事例」を追加** | /（landing.html） | LP から /case-studies への導線を補強し、事例の回遊を促進する。 |

---

## 4. 次の実装ステップ案（優先順・最大10件・コードは書かない）

| 優先度 | タスク | 対象 |
|--------|--------|------|
| 1 | LP の hero リードに /guide・/blog・glossary へのリンク1文を追加する | `templates/landing.html` 257行付近 |
| 2 | best-practices の H1 直下に「誰の何を解決するか」を1文追加する | `templates/best-practices.html` 36行付近 |
| 3 | privacy の「1. はじめに」直後に本サービス固有の処理方式説明を1〜2文追加する | `templates/privacy.html` 84行付近 |
| 4 | blog の H1 直下に「このページで分かること」を1文追加する | `templates/blog/index.html` 14行付近 |
| 5 | guide/excel-format の H1 直下に「形式エラーでつまずきやすいポイントを具体的に説明」を1文追加する | `templates/guide/excel-format.html` 152行付近 |
| 6 | glossary の H1 直下に「代表的な用語をすぐ確認できる」旨を1文追加する | `templates/glossary.html` 99行付近 |
| 7 | glossary の H2 前に代表用語へのアンカーショートカットを1行追加する | `templates/glossary.html` 101行付近 |
| 8 | LP の trust セクションに「導入事例」へのリンクを追加する | `templates/landing.html` 318行付近 |
| 9 | blog に「導入事例」へのリンクを1本追加する（カテゴリ付近か記事一覧前） | `templates/blog/index.html` |
| 10 | best-practices の末尾ナビに「導入事例一覧」へのリンクを追加する | `templates/best-practices.html` 末尾付近 |

---

## 証拠一覧（共通）

| 項目 | 証拠 |
|------|------|
| canonical・noindex | `templates/includes/head_meta.html` 43行。通常ページに noindex なし。`app.py` 479–485行で `/status/`・`/api/`・`_NOINDEX_PATHS` のみ X-Robots-Tag。 |
| ナビ・フッター | `lib/nav.py` の `get_nav_sections`・`get_footer_columns`。best-practices・blog・glossary・privacy・guide は Resource または リソース/ガイド カラムに含まれる。 |
| LP の hero | `templates/landing.html` 255–257行。H1、リード、/tools・/guide/excel-format へのリンク。 |
| LP の trust | `templates/landing.html` 318行。privacy・blog・glossary・guide/excel-format・best-practices へのリンク。 |

以上が Step 3 の分析レポートである。次の工程で、上記タスクを実装に落とし込む。
