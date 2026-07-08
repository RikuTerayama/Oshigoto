# Search Console「クロール済み - インデックス未登録」6ページ 原因特定レポート（Step2）

**作成日**: 2026-02-26  
**対象**: 本リポジトリ（Flask サイト）  
**目的**: GSCで発生している「クロール済み - インデックス未登録」6ページを最短で改善するため、コード・ページ構造・内部リンク・重複/正規化の観点から原因を特定し、修正優先度付きの改善方針を出す（**本ステップでは実装しない。現状分析レポートのみ**）

---

## 前提（Step1対応済み）

- /best-practices と /sitemap.html はナビ/フッターに追加済み
- sitemap.xml の base_url は BASE_URL 環境変数優先（未設定時はフォールバック）
- canonical は head_meta で自己参照（BASE_URL + request.path）
- robots.txt は 200 で配信、/api・/status 等は noindex/Disallow
- 主要ツール5ページに intro ブロック追加済み
- preflight は全て PASS

---

## A. 結論サマリ（最重要な指摘を5つまで）

1. **未登録6ページの実体はGSCで要確認**  
   リポジトリ上では「どの6URLか」は特定できない。候補として、既存監査で言及されたインデックス対象5件（/, /privacy, /blog, /glossary, /guide/excel-format）に加え、/sitemap.html や /guide、事例1件などが考えられる。**GSCの「クロール済み - インデックス未登録」一覧のURL・理由名を確認しないと断定できない。**

2. **canonical と sitemap の BASE_URL はコード上は同一ソース**  
   context_processor と sitemap() のいずれも `os.getenv('BASE_URL', 'https://jobcan-automation.onrender.com').rstrip('/')` を参照。本番で同一プロセス・同一環境であれば一致する設計。**一方、robots.txt の Sitemap 行は静的ファイルでハードコード**（`static/robots.txt`）のため、本番で BASE_URL を変更している場合、robots の Sitemap URL と sitemap.xml の実際のドメインがずれる余地がある。

3. **lastmod が全URLで同一日付**  
   sitemap の全エントリで `lastmod` に `today`（当日）を付与。優先度の差が lastmod で伝わらず、クロール優先のシグナルとして弱い可能性がある。

4. **事例3ページはナビ/フッターにリンクが無い**  
   /case-study/* は sitemap.html・完全ガイド・総合ガイド・一部ブログからのみリンク。トップ・ツール一覧・フッターからは到達しない。内部リンクが少なく「重要でないページ」と判断され、未登録になりやすい候補。

5. **一覧・薄めページのコンテンツリスク**  
   /glossary（用語の羅列）、/guide（リンク一覧＋短い説明）、/sitemap.html（リンク＋短い説明）は、Googleの「薄いコンテンツ」判定の対象になり得る。既に冒頭説明等はあるが、差別化・付加価値の明示を強める余地がある。

---

## B. 未登録6ページの“候補URL”仮説（最大10件・確度順）

| 順位 | 想定URL | 理由（仮説） |
|------|---------|--------------|
| 1 | / | LP。重要だが、テンプレ量・内部リンクのバランス次第で「選ばれない」ことがある。既存監査で未登録候補として言及済み。 |
| 2 | /privacy | 必須ページだが、テキスト中心で差別化が弱く「低付加価値」と見なされる可能性。既存監査で未登録候補。 |
| 3 | /blog | 一覧ページ。カテゴリ・冒頭説明はあるが、記事リンクの羅列が主で薄く見えるリスク。既存監査で未登録候補。 |
| 4 | /glossary | 用語集。用語＋説明の繰り返しで、意図・独自性が伝わりにくいと薄く判定されうる。既存監査で未登録候補。 |
| 5 | /guide/excel-format | ガイドの要だが、他ガイドとの類似構造で「重複」と見なされる可能性。既存監査で未登録候補。 |
| 6 | /sitemap.html | HTMLサイトマップ。リンク一覧＋短い説明が主で、薄いページになりやすい。ナビには無く、フッターからのみ。 |
| 7 | /guide | ガイド一覧。ツール別ガイド＋サブガイドのリンクが中心で、一覧型の薄さリスク。 |
| 8 | /case-study/contact-center のいずれか | 事例は3本とも構造が類似。ナビ/フッターに無く、内部リンクが少ない。1本が未登録になり得る。 |
| 9 | /tools | ツール一覧。フィルタUI＋カード一覧。no-results 文言はサーバーHTMLに含めない対応済みだが、JSで描画する部分が多く、初期HTMLの本文量が相対的に少ない可能性。 |
| 10 | /faq | FAQ。Q&Aはあるが、他ページとの重複表現が多ければ「重複」と判断されうる。 |

**注意**: 上記はコード・構造からの**推定**であり、実際の6ページは **GSC の「クロール済み - インデックス未登録」一覧および理由（該当する場合）** で確認する必要がある。

---

## C. 技術要因チェック結果

| 項目 | 結果 | 詳細 |
|------|------|------|
| **canonical と sitemap の BASE_URL 一致** | 設計上は一致 | `app.py`: context_processor 421行・443行で `BASE_URL = os.getenv('BASE_URL', '...').rstrip('/')`。sitemap() 2165行で `base_url = (os.getenv('BASE_URL') or '...').rstrip('/')`。同一プロセスなら同一値。本番でリクエストごとに環境が違う場合はズレる余地あり（通常は考えにくい）。 |
| **canonical 自己参照** | 問題なし | `templates/includes/head_meta.html` 43行: `href="{{ BASE_URL|default('...') }}{% if request and request.path %}{{ request.path }}{% else %}/{% endif %}"`。末尾スラッシュなしの path で自己参照。 |
| **末尾スラッシュ正規化** | 問題なし | `app.py` 453–470行: 存在するルートへの末尾スラッシュは 301 で正規化。sitemap には末尾スラッシュなしの URL のみ列挙（2254行 `full_url = base_url + url_path`）。301 先が sitemap に混入していない。 |
| **robots / noindex** | 問題なし | 重要ページに noindex は付与されていない。`app.py` 479–485行: `/status/`・`/api/`・`_NOINDEX_PATHS` のみ X-Robots-Tag: noindex, nofollow。error ページは `templates/error.html` で meta robots noindex。 |
| **robots.txt の Sitemap 行** | 要確認 | `static/robots.txt` 31行: `Sitemap: https://jobcan-automation.onrender.com/sitemap.xml` とハードコード。本番で BASE_URL を別ドメインにしている場合、robots の Sitemap と実際の sitemap.xml のドメインが一致しない可能性がある。 |
| **ステータスコード** | 問題なし | 重要URLは app.py で固定ルートとして 200 を返す。条件分岐で 404 になるルートは、/guide/minutes・/tools/minutes の 301 のみ。preflight で主要パス 200 を確認済み。 |
| **JS 依存** | 軽微 | 主要ページは Jinja2 でサーバー描画。ツール一覧の no-results は JS で挿入し、禁止文言はサーバーHTMLに含めない設計。初期HTMLに H1・説明・リンクは含まれる。 |
| **sitemap 品質** | 要改善の余地 | 301/404/noindex の URL は sitemap に含まれていない。全エントリで `lastmod` が同一日（`today`）のため、更新頻度の差が lastmod で伝わらない。 |

---

## D. コンテンツ要因チェック結果（薄さ/重複/意図不一致）

| ページタイプ | 該当URL例 | 所見 |
|--------------|-----------|------|
| **一覧（ブログ）** | /blog | H1・冒頭2段落・カテゴリ説明・最新記事カードあり。リンクの羅列だけでなく説明がある。「コンテンツハブ」としての意図は伝わる。薄さリスクは中。 |
| **一覧（ガイド）** | /guide | H1・lead・「はじめての方へ」「ツール別ガイド」のセクションとリンク。details でサブガイドを折りたたみ。リンクが主だが短い説明はある。薄さリスクは中。 |
| **一覧（用語集）** | /glossary | H1・冒頭説明・「Excel形式ガイド」「ベストプラクティス」「FAQ」への誘導あり。用語は term-item で名前・読み・定義・例。羅列感はあるが、各項に説明あり。薄さリスクは中。 |
| **一覧（HTMLサイトマップ）** | /sitemap.html | H1・短い説明・カテゴリ説明・リンク一覧。検索エンジン・ユーザー向けと明記。リンク中心で薄く見えるリスクはやや高。 |
| **事例3ページ** | /case-study/* | 各ページに H1・リード・企業プロフィール・課題・導入プロセス・効果の表・まとめ。構造は3本とも類似（H2 構成が似る）。数値・業種で差別化はある。重複感・薄さリスクは中。 |
| **ガイド（長文）** | /guide/excel-format, /guide/complete 等 | 見出し・手順・注意・FAQ 的要素あり。excel-format は長文で付加価値は高い。ツール別ガイド（image-batch, pdf 等）は1ページあたりの分量が少ない場合、薄く見える可能性あり。 |
| **ツールページ** | /tools/* | Step1で intro ブロック（できること・手順・注意・ガイドリンク）追加済み。入力UIが主だが、初期HTMLに説明は含まれる。 |

---

## E. 内部リンクの弱点（孤立ページ候補＋リンク追加案）

| 候補ページ | 現状の主なリンク元 | 弱点 | リンク追加案（方針のみ） |
|------------|--------------------|------|---------------------------|
| /case-study/contact-center | sitemap.html, guide/complete-guide, guide/comprehensive-guide, 複数ブログ | ナビ・フッターに無い。トップ・/guide・/blog から直接のリンクが少ない | フッター「リソース」またはブログ一覧付近に「導入事例」を1本追加し、/case-study/contact-center（または事例一覧）へ誘導 |
| /case-study/consulting-firm | 上記に同じ（complete-guide, sitemap 等） | 同上 | 同上。事例まとめリンクから3本に分散 |
| /case-study/remote-startup | 同上 | 同上 | 同上 |
| /sitemap.html | フッター「リソース」のみ（Step1で追加済み） | トップ・ナビには無い。1クリックでは到達可 | 現状でも許容範囲。必要なら LP フッター付近の「サイトマップ」をより目立たせる |
| /guide | ナビ・フッター・LP・ツール・ブログ | 十分 | 特になし |
| /blog | ナビ・フッター・LP | 十分 | 特になし |
| /glossary | ナビ・フッター・LP・ブログ・guide/excel-format | 十分 | 特になし |
| /guide/excel-format | ナビ・フッター・多数ガイド・ブログ | 十分 | 特になし |

**アンカーテキスト**: ブログ・ガイド内の「こちら」「続きを読む」はあるが、「導入事例：コンタクトセンター」など具体的な文言も混在。機械的すぎる「こちら」だらけにはなっていない。

---

## F. 優先修正案（P0/P1/P2、最大10件・理由付き）

| 優先度 | 改善案 | 理由 |
|--------|--------|------|
| **P0** | **GSCで「クロール済み - インデックス未登録」の対象6URLと理由を確認する** | どのURLが未登録か、理由が「クロールバジェット」「重複・薄い」等のどれかを知らないと、施策の優先順位が決められない。リポジトリだけでは断定できない。 |
| **P0** | **事例ページをナビまたはフッターから1クリックで到達できるようにする** | 3本ともナビ/フッターに無く、内部リンクが少ない。フッター「リソース」に「導入事例」を追加し、事例一覧または代表1本へリンクする（差分最小）。 |
| **P1** | **robots.txt の Sitemap URL を BASE_URL と一致させる** | 現状は `static/robots.txt` にハードコード。本番で BASE_URL を変えると、robots の Sitemap と sitemap.xml のドメインがずれる。動的生成またはビルド時差し替えで BASE_URL を反映する方針が望ましい。 |
| **P1** | **sitemap の lastmod をページ種別・更新頻度に応じて差をつける** | 全URL同一日だと、クロール優先のシグナルが弱い。固定ページは「最終更新想定日」、ブログは「記事の更新日」など、取得可能な範囲で lastmod を差し替える方針。 |
| **P1** | **未登録になりやすい一覧ページの冒頭に「このページの価値」を1〜2文追加** | /glossary, /guide, /sitemap.html など、既に短い説明はあるが、「検索から来た人が得られること」を明示すると、意図一致・付加価値が伝わりやすい。 |
| **P2** | **事例3本の差別化を確認・強化する** | 構造が似ているため、数値・業種・課題・ストーリーの違いを各ページの冒頭や見出しでより明確にし、重複判定を避ける。 |
| **P2** | **ツール別ガイド（/guide/image-batch 等）の本文量を確認する** | 1ページが極端に短い場合は、手順・注意・1問1答を少し足して薄さを防ぐ方針。 |
| **P2** | **ブログ一覧から事例へのリンクを1本入れる** | /blog に「導入事例」セクションまたはカードを1つ追加し、/case-study/contact-center または事例まとめへ誘導。回遊と重要度シグナルを強化。 |

---

## G. 証拠（ファイルパス・行番号・想定URL）

| 内容 | 証拠 |
|------|------|
| sitemap の URL リスト（固定） | `app.py` 2173–2221行。/, /autofill, /about, /contact, /privacy, /terms, /faq, /glossary, /best-practices, /sitemap.html, /guide（＋7本）, /tools, /blog（＋12記事）, /case-study/* 3本。 |
| sitemap に PRODUCTS を追加 | `app.py` 2224–2245行。`lib.routes` の PRODUCTS から `path` と `guide_path` を重複なく追加。 |
| BASE_URL（canonical と sitemap） | `app.py` 421行・443行（context_processor）、2165行（sitemap）。いずれも `os.getenv('BASE_URL', 'https://jobcan-automation.onrender.com').rstrip('/')`。 |
| canonical の出力 | `templates/includes/head_meta.html` 43行: `{{ BASE_URL|default('...') }}{% if request and request.path %}{{ request.path }}{% else %}/{% endif %}`。 |
| 末尾スラッシュ正規化 | `app.py` 453–470行。`normalize_trailing_slash`。存在ルートのみ 301。 |
| noindex 付与 | `app.py` 474–485行。`_NOINDEX_PATHS` と `/status/`・`/api/`。error は `templates/error.html`。 |
| robots.txt の Sitemap 行 | `static/robots.txt` 31行: `Sitemap: https://jobcan-automation.onrender.com/sitemap.xml`（ハードコード）。 |
| lastmod が同一 | `app.py` 2167行 `today = datetime.now().strftime('%Y-%m-%d')`、2258行で全エントリに `lastmod` に `today` を設定。 |
| フッター・ナビに事例なし | `lib/nav.py`。`resource_links`・`get_footer_columns()` に case-study のリンクは無い。 |
| 事例へのリンク元 | `templates/sitemap.html` 181–183行、`templates/guide/complete-guide.html` 307–325行・356–360行、`templates/guide/comprehensive-guide.html` 418行付近、複数ブログ（reduce-manual-work-checklist, month-end-closing-hell-and-automation 等）。 |
| ブログ一覧の構造 | `templates/blog/index.html`。H1・冒頭2段落・カテゴリ3ブロック・最新記事カード（タイトル・要約・続きを読む）。 |
| ガイド一覧の構造 | `templates/guide/index.html`。H1・lead・「はじめての方へ」「ツール別ガイド」「Jobcan AutoFill 詳細ガイド」details。 |
| 用語集の構造 | `templates/glossary.html`。H1・冒頭2段落・「勤怠管理の基本用語」H2・term-item（用語名・読み・定義・例）。 |

---

## 追加で確認が必要な点（リポジトリだけでは確定できないもの）

- **GSC「クロール済み - インデックス未登録」の対象6URL**  
  実際に未登録になっているURLのリスト。これがないと「どのページを優先して直すか」が決められない。
- **GSC の未登録理由（表示されている場合）**  
  「クロールバジェット」「重複・薄いコンテンツ」「サイトの重要度」など、理由名があれば原因の切り分けができる。
- **URL検査での「正規URL」表示**  
  各候補URLをURL検査したとき、Googleが正規と認識しているURL（canonical やリダイレクト先）が想定どおりか。
- **本番環境の BASE_URL**  
  Render 等で設定している値。robots.txt の Sitemap と sitemap.xml のドメインが一致しているかの確認に必要。

以上が Step2 の現状分析レポートである。次の工程で、GSC の実データを踏まえつつ、本レポートの P0/P1/P2 をタスク化し実装する。
