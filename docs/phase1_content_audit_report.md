# Phase 1-Content 現状分析レポート（AdSense承認前・薄いコンテンツ解消）

**目的**: 審査落ち要因（薄い/重複/導線不足/noindex誤設定）を事実ベースで洗い出し、最小差分で直せるバックログを作成する。**本ターンは分析のみ（実装なし）。**  
**証跡取得日**: コードベース＋Flask test client。  
**前提**: Phase 1（about/contact フォールバック、BASE_URL 化、/tools・/guide 導入文、LP contact CTA）完了済み。smoke_test --deploy / verify_deploy_routes / verify_phase1 は OK。

**分析用スクリプト**: `scripts/audit_content_thinness.py` — 実行: `python scripts/audit_content_thinness.py`。主要URLの status / X-Robots-Tag / 本文文字数 / h1・h2・h3 数 / FAQ・注意点有無 / 薄さ判定を TSV 出力。

---

## 1) noindex / robots / canonical の棚卸し（コード＋テスト）

### コード上の事実（file:line）

| 項目 | 箇所 | 内容 |
|------|------|------|
| NOINDEX 対象パス | app.py:394-396 | `_NOINDEX_PATHS = frozenset(('/download-template', '/download-previous-template', '/sessions', '/cleanup-sessions'))` |
| X-Robots-Tag 付与 | app.py:398-405 | `add_noindex_for_dynamic(response)`: `path.startswith('/status/')` または `path.startswith('/api/')` または `path in _NOINDEX_PATHS` のとき `response.headers['X-Robots-Tag'] = 'noindex, nofollow'` |
| canonical 生成 | templates/includes/head_meta.html:30 | `{{ BASE_URL\|default('...') }}{% if request and request.path %}{{ request.path }}{% else %}/{% endif %}`（末尾スラッシュは before_request で 301 されるため実質スラッシュなし） |
| og:url | head_meta.html:36 | 上記と同様の式 |

### テスト証跡（Flask test client）

**実行コマンド**: `python scripts/audit_content_thinness.py`（主要URLを GET。follow_redirects=True）

**X-Robots-Tag**: 以下いずれも **付与なし**（ヘッダに `X-Robots-Tag` なし → インデックス許可）。

| URL | status | X-Robots-Tag | 備考 |
|-----|--------|--------------|------|
| / | 200 | - | OK |
| /autofill | 200 | - | OK |
| /tools | 200 | - | OK |
| /guide | 200 | - | OK |
| /privacy | 200 | - | OK |
| /terms | 200 | - | OK |
| /about | 200 | - | OK |
| /contact | 200 | - | OK |
| /tools/pdf | 200 | - | OK |
| /guide/pdf | 200 | - | OK |

**廃止URLの 301 確認**（実行: `python scripts/check_canonical_301.py` 相当を手動実行）  
- /tools/minutes → 301, Location: /tools  
- /guide/minutes → 301, Location: /guide  
- /tools/pdf/ → 301, Location: /tools/pdf  

**canonical の実値（/ のレスポンス）**:  
`<link rel="canonical" href="https://jobcan-automation.onrender.com/">`  
→ BASE_URL 未設定時は現行ドメイン＋request.path で一貫。

**結論（事実）**: 主要コンテンツURLに noindex は付いていない。廃止パスは想定どおり 301。canonical は head_meta で request.path と一致（末尾スラッシュは 301 で正規化済み）。

---

## 2) “薄いページ”の定量（HTML テキスト量）の証跡

### 計測方法

- **スクリプト**: `scripts/audit_content_thinness.py` を新規追加。
- **処理**: 各パスを GET → レスポンス body から `<script>`/`<style>` とタグを除去 → 空白正規化後のテキスト文字数、`<h1>`/`<h2>`/`<h3>` の出現数、FAQ（キーワード: FAQ|よくある質問|faq-item|faq-question）、注意点（注意|※|重要|warning|info-box 等）の有無を出力。
- **しきい値（暫定）**: thin 判定 = WARN: <200字, LOW: <500字, MID: 500–1200字, OK: ≥1200字。
- **実行コマンド**: `python scripts/audit_content_thinness.py`

### 実行出力（証跡）

```
path	status	X-Robots-Tag	chars	h1	h2	h3	FAQ	notes	thin
/	200	-	1767	1	3	9	Y	N	OK
/autofill	200	-	4101	1	10	25	Y	Y	OK
/tools	200	-	1800	1	0	6	Y	N	OK
/guide	200	-	1279	1	1	0	Y	N	OK
/privacy	200	-	2592	1	10	0	Y	Y	OK
/terms	200	-	2815	1	11	0	Y	Y	OK
/about	200	-	5786	1	11	10	Y	Y	OK
/contact	200	-	2120	1	2	3	Y	Y	OK
/tools/pdf	200	-	3125	1	1	16	Y	Y	OK
/tools/csv	200	-	1313	1	0	4	Y	N	OK
/tools/seo	200	-	3620	3	1	13	Y	Y	OK
/tools/image-batch	200	-	2510	1	1	16	Y	Y	OK
/tools/image-cleanup	200	-	2745	1	1	16	Y	Y	OK
/guide/pdf	200	-	3572	1	8	15	Y	Y	OK
/guide/csv	200	-	3359	1	8	13	Y	Y	OK
/guide/seo	200	-	3986	1	8	13	Y	Y	OK
/guide/image-batch	200	-	4084	1	8	15	Y	Y	OK
/guide/image-cleanup	200	-	3569	1	8	15	Y	Y	OK
/guide/autofill	200	-	4288	1	10	15	Y	Y	OK
/guide/getting-started	200	-	3166	1	6	5	Y	Y	OK
```

- **WARN（<200字）**: 0 件。
- **LOW（<500字）**: 0 件。
- **MID（500–1200字）**: 0 件（/guide は 1279 で OK 判定）。
- **根拠**: 上記スクリプトでタグ除去後のテキスト文字数を計測。thin 判定は暫定しきい値に基づく。

---

## 3) ペア導線（/tools/* ↔ /guide/*）の相互リンク監査

### 事実（file:line）

| tool_url | guide_url | tools→guide | guide→tools | 欠けている箇所 | 最小追加案 |
|----------|-----------|-------------|-------------|----------------|------------|
| /tools/pdf | /guide/pdf | 有（includes/tool_guide_link.html, product.guide_path） | 有（guide/pdf.html:78, 189-194） | なし | — |
| /tools/csv | /guide/csv | 有（tool_guide_link） | 有（guide/csv.html:63, 165-170） | なし | — |
| /tools/seo | /guide/seo | 有（tool_guide_link） | 有（guide/seo.html:58, 148-153） | なし | — |
| /tools/image-batch | /guide/image-batch | 有（tool_guide_link） | 有（guide/image-batch.html:155, 268-273） | なし | — |
| /tools/image-cleanup | /guide/image-cleanup | 有（tool_guide_link） | 有（guide/image-cleanup.html:58, 136-141） | なし | — |
| /autofill | /guide/autofill | **なし** | 有（guide/autofill.html:52, 161） | autofill.html に /guide/autofill へのリンクがない（grep で 0 件） | autofill.html の「はじめての使い方」付近に「📚 Jobcan AutoFill の使い方ガイド」リンク（/guide/autofill）を 1 本追加 |

- **tools→guide**: 各 tools ページは `render_template(..., product=product)` で product を渡し、templates/includes/tool_guide_link.html（1-4行目）で `product.guide_path` があればガイドへのリンクを表示。lib/products_catalog.py で全ツールに guide_path 定義あり。  
- **/autofill**: autofill.html は product を渡さず tool_guide_link を含まない。793行目に /guide/getting-started、828行目に /guide/comprehensive-guide はあるが、**/guide/autofill への直リンクは存在しない**（grep で確認）。

---

## 4) 重複/工事中/空ページの検出

### 文字列検索（事実）

**実行**: `grep -ri "準備中|工事中|TBD|coming soon|comming|lorem" templates/*.html templates/**/*.html`（相当をコードベースで検索）

| ファイル | 行 | 内容 | 判定 |
|----------|-----|------|------|
| templates/landing.html | 269 | `{% if product.status ... %}利用可能{% else %}準備中{% endif %}` | 製品ステータス表示の分岐。許容。 |
| templates/tools/index.html | 252 | `準備中` | 製品カードの status 表示。許容。 |
| templates/includes/download_panel.html | 21 | `すべてをZIPでダウンロード（準備中）` | 機能未実装の明示。要対応なら P2。 |
| templates/includes/product_card.html | 10 | `{% else %}準備中{% endif %}` | 製品ステータス。許容。 |

- **工事中/TBD/coming soon/lorem**: 該当なし。
- **空ページ・極端に短い本文**: audit_content_thinness.py で全対象 URL の本文 ≥200 字。**<200 字のページは 0 件**。

---

## 5) AdSense 観点の必須ページ品質（legal & contact）

### /privacy（事実・見出しとキーワード）

| 要素 | 有無 | 根拠（file:line または キーワード） |
|------|------|--------------------------------------|
| 第三者配信 | 有 | h2「8. 第三者配信事業者による広告配信について」、Google AdSense・Cookie の記述（131-135行目） |
| Cookie | 有 | h2「7. Cookie（クッキー）の使用」（128-129行目） |
| 計測 | 有 | 利用状況・アクセスログ（2. 収集する情報） |
| オプトアウト | 有 | Google 広告設定・aboutads.info へのリンク（134行目） |
| 問い合わせ | 有 | h2「10. お問い合わせ」、/contact リンク（140-141行目） |

### /terms（事実）

| 要素 | 有無 | 根拠 |
|------|------|------|
| 免責 | 有 | 第5条（免責事項）、第2条・第4条の注意 |
| 禁止事項 | 有 | 第4条（禁止事項） |
| 責任範囲 | 有 | 第5条・第7条 |
| 準拠法 | 有 | 第9条（日本法・東京地裁） |
| 個人情報・広告 | 有 | 第6条、/privacy 参照 |

### /about（事実）

| 要素 | 有無 | 根拠 |
|------|------|------|
| 誰が運営 | 有 | 運営者情報（OPERATOR_*）または Phase1 フォールバック「お問い合わせは /contact から」 |
| 提供価値 | 有 | 開発の背景・技術・セキュリティ・運営者プロフィール |
| 連絡先導線 | 有 | 複数箇所で /contact リンク（294-295, 306, 367-368, 377） |

### /contact（事実）

| 要素 | 有無 | 根拠 |
|------|------|------|
| 連絡手段複数 | 有 | フォーム（埋め込み）＋ OPERATOR_EMAIL または「フォームが主な窓口」案内＋ GitHub Issues |
| 運営者情報への導線 | 有 | ヘッダ・フッターから /about 到達可能（nav_sections / footer_columns） |

---

# 出力フォーマット（必須）

## A. noindex/robots/canonical 監査（事実）

| URL | status | X-Robots-Tag | canonical（テンプレ定義） | 備考 |
|-----|--------|--------------|---------------------------|------|
| / | 200 | - | BASE_URL + request.path → / | 付与なし＝インデックス可 |
| /autofill | 200 | - | 同左 /autofill | 同左 |
| /tools | 200 | - | 同左 /tools | 同左 |
| /guide | 200 | - | 同左 /guide | 同左 |
| /privacy | 200 | - | 同左 /privacy | 同左 |
| /terms | 200 | - | 同左 /terms | 同左 |
| /about | 200 | - | 同左 /about | 同左 |
| /contact | 200 | - | 同左 /contact | 同左 |
| /tools/pdf | 200 | - | 同左 /tools/pdf | 同左 |
| /guide/pdf | 200 | - | 同左 /guide/pdf | 同左 |
| /tools/minutes | 301 | - | — | Location: /tools |
| /guide/minutes | 301 | - | — | Location: /guide |
| /tools/pdf/ | 301 | - | — | Location: /tools/pdf |

---

## B. 薄さランキング（事実・定量）

| URL | テキスト文字数 | h1/h2/h3数 | FAQ有無 | 注意点有無 | “薄い”判定 | 根拠（計測方法） |
|-----|----------------|------------|---------|------------|------------|------------------|
| /guide/getting-started | 3166 | 1/6/5 | Y | Y | OK | audit_content_thinness.py |
| /guide | 1279 | 1/1/0 | Y | N | OK | 同上 |
| /tools/csv | 1313 | 1/0/4 | Y | N | OK | 同上 |
| /tools | 1800 | 1/0/6 | Y | N | OK | 同上 |
| /contact | 2120 | 1/2/3 | Y | Y | OK | 同上 |
| /privacy | 2592 | 1/10/0 | Y | Y | OK | 同上 |
| /tools/image-batch | 2510 | 1/1/16 | Y | Y | OK | 同上 |
| / | 1767 | 1/3/9 | Y | N | OK | 同上 |
| /terms | 2815 | 1/11/0 | Y | Y | OK | 同上 |
| /tools/image-cleanup | 2745 | 1/1/16 | Y | Y | OK | 同上 |
| /tools/pdf | 3125 | 1/1/16 | Y | Y | OK | 同上 |
| /guide/pdf | 3572 | 1/8/15 | Y | Y | OK | 同上 |
| /guide/csv | 3359 | 1/8/13 | Y | Y | OK | 同上 |
| /guide/seo | 3986 | 1/8/13 | Y | Y | OK | 同上 |
| /guide/image-cleanup | 3569 | 1/8/15 | Y | Y | OK | 同上 |
| /autofill | 4101 | 1/10/25 | Y | Y | OK | 同上 |
| /guide/image-batch | 4084 | 1/8/15 | Y | Y | OK | 同上 |
| /guide/autofill | 4288 | 1/10/15 | Y | Y | OK | 同上 |
| /tools/seo | 3620 | 3/1/13 | Y | Y | OK | 同上 |

- しきい値: WARN <200, LOW <500, MID 500–1200, OK ≥1200。全 URL OK。
- 計測: タグ除去後テキスト文字数・見出し数・FAQ/注意キーワードは scripts/audit_content_thinness.py で取得。

---

## C. ペア導線監査（事実）

| tool_url | guide_url | tools→guideリンク有無 | guide→toolsリンク有無 | 欠けている箇所（file:line） | 最小追加案 |
|----------|-----------|------------------------|------------------------|------------------------------|------------|
| /tools/pdf | /guide/pdf | 有 | 有 | なし | — |
| /tools/csv | /guide/csv | 有 | 有 | なし | — |
| /tools/seo | /guide/seo | 有 | 有 | なし | — |
| /tools/image-batch | /guide/image-batch | 有 | 有 | なし | — |
| /tools/image-cleanup | /guide/image-cleanup | 有 | 有 | なし | — |
| /autofill | /guide/autofill | **なし** | 有 | templates/autofill.html に /guide/autofill の直リンクなし | 793行付近に「📚 Jobcan AutoFill の使い方ガイド」→ /guide/autofill を 1 本追加 |

---

## D. バックログ TSV（最重要）

**ファイル**: `docs/phase1_content_backlog.tsv`（コピペ用）

| 優先度 | URL | 問題（事実） | 影響 | 最小修正案 | 受け入れ基準 | 必要証跡 |
|--------|-----|-------------|------|------------|--------------|----------|
| P1 | /autofill | /guide/autofill への直リンクなし | ペア導線欠落 | autofill.html に「使い方ガイド」→/guide/autofill を1本追加 | 1クリックで到達・表示崩れなし | — |
| P2 | download_panel.html | 「準備中」文言（21行目） | 未完成感 | 文言変更または条件付き非表示 | 工事中感を弱める | — |
| P2 | /guide | h2 が 1 つのみ | 見出し構造が薄い可能性 | h2 を 1 本追加 | h2≥2・表示崩れなし | — |

---

## C) Search Console / インデックス観点のリスク一覧

| リスク | 状態（事実） | 証跡 | 備考 |
|--------|--------------|------|------|
| noindex 誤設定 | 主要コンテンツURLに X-Robots-Tag なし | audit_content_thinness.py で全対象 200 かつヘッダなし | 誤って noindex が付与されているページはなし |
| robots.txt | 未検証（本分析ではコード未確認） | 証跡不足 | app.py に /robots.txt ルートあり。内容は要確認 |
| canonical 不整合 | 各ページで BASE_URL+request.path と一致 | head_meta.html:30, 36。/ で view-source 相当で確認済み | 末尾スラッシュは 301 で正規化 |
| 404 多発 | 主要URLはすべて 200 | 上記スクリプトで status 一覧取得 | 廃止パスは 301 で転送 |
| 301 チェーン | /tools/pdf/ → /tools/pdf のみ。多重リダイレクトなし | テストクライアントで Location 確認 | — |

- **証跡不足**: 本番の Search Console（インデックス数・カバレッジ・手動措置）は未確認。必要なら別途取得。

---

## E. 推測・注意（事実と分離）

- **Search Console**: 本分析では未参照。インデックス数・カバレッジ・手動ペナルティの有無は証跡なし。コード上 noindex 誤設定は検出されず。
- **AdSense 審査の個別理由**: 未確認。薄さ・導線・legal はコード上は要件を満たしているが、審査結果は外部依存のため推測。
- **download_panel「準備中」**: ZIP 一括ダウンロードは未実装。審査で「未完成機能」と見なされる可能性は推測。必要なら P2 で文言変更または非表示。
- **/guide の h2 が 1 つのみ**: 文字数は 1279 で OK だが、見出し構造が薄い可能性は事実。強化するかは P2 で検討可。
