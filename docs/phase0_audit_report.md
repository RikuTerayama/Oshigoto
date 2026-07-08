# Phase 0：現状棚卸しレポート（AdSense承認〜拡散向け）

**目的**: 欠けている箇所を事実ベースで確定し、次フェーズの実装バックログ（URL×状態×直す内容）を1枚に落とす。  
**証跡取得日**: コードベース＋Flask test client（本番URL未使用時は「テストクライアント」と明記）。  
**BASE_URL（本番想定）**: `https://jobcan-automation.onrender.com`

---

## A. サイトマップ（主要URL一覧）

| URL | 役割 | テンプレート | route定義（file:line） |
|-----|------|-------------|------------------------|
| / | LP（製品ハブ） | landing.html | app.py:800-823 |
| /autofill | LP（メイン機能） | autofill.html | app.py:910-914 |
| /tools | ツール一覧 | tools/index.html | app.py:1258-1269 |
| /tools/image-batch | ツール | tools/image-batch.html | app.py:1016-1021 |
| /tools/pdf | ツール | tools/pdf.html | app.py:1023-1028 |
| /tools/image-cleanup | ツール | tools/image-cleanup.html | app.py:1137-1142 |
| /tools/seo | ツール | tools/seo.html | app.py:1156-1161 |
| /tools/csv | ツール | tools/csv.html | app.py:1163-1168 |
| /tools/minutes | 廃止→リダイレクト | — | app.py:1144-1147 → 301 /tools |
| /guide | ガイド一覧 | guide/index.html | app.py:942-950 |
| /guide/autofill | ガイド | guide/autofill.html | app.py:953-956 |
| /guide/getting-started | ガイド | guide/getting-started.html | app.py:959-962 |
| /guide/excel-format | ガイド | guide/excel-format.html | app.py:965-968 |
| /guide/troubleshooting | ガイド | guide/troubleshooting.html | app.py:971-974 |
| /guide/complete | ガイド | guide/complete-guide.html | app.py:976-979 |
| /guide/comprehensive-guide | ガイド | guide/comprehensive-guide.html | app.py:981-984 |
| /guide/image-batch | ガイド | guide/image-batch.html | app.py:986-989 |
| /guide/pdf | ガイド | guide/pdf.html | app.py:991-994 |
| /guide/image-cleanup | ガイド | guide/image-cleanup.html | app.py:996-999 |
| /guide/minutes | 廃止→リダイレクト | — | app.py:1001-1004 → 301 /guide |
| /guide/seo | ガイド | guide/seo.html | app.py:1006-1009 |
| /guide/csv | ガイド | guide/csv.html | app.py:1011-1014 |
| /privacy | 法的 | privacy.html | app.py:927-930 |
| /terms | 法的 | terms.html | app.py:932-935 |
| /about | 運営者・会社概要 | about.html | app.py:1281-1284 |
| /contact | 問い合わせ | contact.html | app.py:937-940 |

**head_meta の適用**: 上記いずれも `{% include 'includes/head_meta.html' %}` を参照（各テンプレート先頭付近）。  
**canonical 生成**: templates/includes/head_meta.html:30 — `https://jobcan-automation.onrender.com` + `request.path`（末尾スラッシュは before_request で 301 されるため、正規化後はスラッシュなしで表示）。

---

## B. 監査結果（URLごと）

### 検査項目のコード上の事実

**head_meta（AdSense / GA4 / canonical / OGP）**

| 項目 | 事実（file:line） |
|------|-------------------|
| AdSense script | templates/includes/head_meta.html:48-49 — 全ページ共通で配置（条件なし）。`client=ca-pub-4232725615106709` |
| GA4 読み込み条件 | head_meta.html:2-13 — `{% if GA_MEASUREMENT_ID %}`。app.py:341 で `GA_MEASUREMENT_ID = os.getenv('GA_MEASUREMENT_ID', '')` を注入。未設定時は gtag 未読み込み。 |
| canonical | head_meta.html:30 — 固定ドメイン + `request.path`（末尾スラッシュはサーバ側で 301 されるため実質スラッシュなしで表示）。 |
| OGP | head_meta.html:33-37 — og:type, og:title, og:url, og:image。description は各テンプレの block og_description。 |
| robots | head_meta 内に meta robots なし。動的パス用 X-Robots-Tag は app.py:391-396（NOINDEX_PATHS）で after_request 付与。 |

**末尾スラッシュ・301・canonical（証跡: Flask test client）**

- 実行: `python -c "from app import app; ... c.get(path, follow_redirects=False)"`（プロジェクトルートで実行）。
- 結果: `/` 200, `/autofill` 200, `/contact` 200, `/privacy` 200, `/terms` 200, `/about` 200, `/tools` 200, `/guide` 200；`/tools/pdf/` 301 → Location: `/tools/pdf`；`/contact/` 301 → Location: `/contact`。
- 末尾スラッシュ正規化: app.py:372-388 `normalize_trailing_slash()` — GET/HEAD で末尾 `/` を 301 でスラッシュなしへリダイレクト（/static/, /api/ 除く）。存在するルートのみリダイレクト。

**verify_deploy_routes.py 証跡（Flask test client）**

- 実行: `python scripts/verify_deploy_routes.py`
- 結果: /tools/seo 200, /tools/csv 200, /guide/csv 200；/tools/minutes 301 → /tools；/guide/minutes 301 → /guide；/tools/pdf/ 301 → /tools/pdf。いずれも期待どおり。

---

### B-1. LP（/）

| 観点 | 事実 | 推測・証跡不足 |
|------|------|----------------|
| 薄さ | landing.html: h1=1（hero）, h2=3（製品一覧・こんな場面で・セキュリティとプライバシー）, 製品カードは products ループで h3+説明。見出し・段落数は十分なボリューム。 | 文字数は未計測。必要なら wc 等で取得推奨。 |
| 導線 | ヘッダ（lib/nav.py の nav_sections）: Home, Tools, Guide, Resource。フッター（footer_columns）: ツール一覧・ガイド・リソース・法的情報。landing.html:258 CTA → /autofill；265-272 product.path → 各ツール/autofill。 | LP 本文に「お問い合わせ」直リンクはなし（ヘッダ・フッター経由のみ）。 |
| 開示 | 本文に cookie/AdSense 文言なし。プライバシー・利用規約・問い合わせはフッターから。 | — |
| 404/301/canonical | 上記のとおり / は 200。canonical は head_meta で /。 | — |
| GA4 | head_meta 経由で GA_MEASUREMENT_ID 設定時のみ page_view（gtag config）。LP 専用イベント送信コードはなし。 | — |

---

### B-2. /autofill

| 観点 | 事実 | 推測・証跡不足 |
|------|------|----------------|
| 薄さ | autofill.html: h1/h2/h3 と p タグが多数（grep で約72箇所の h1/h2/h3/p 系）。ガイド・FAQ・ブログ・問い合わせへの導線あり。 | 同上、文字数は未計測。 |
| 導線 | 793行目 /guide/getting-started；828 /guide/comprehensive-guide；919 /faq；933-962 /blog/*, /blog；973-987 /contact#contact-form。ヘッダ・フッター共通。 | 迷子になりうる箇所は特になし。 |
| 開示 | 同上。AdSense/cookie は privacy に記載。問い合わせは /contact へ誘導。 | — |
| 404/301/canonical | 200。canonical は /autofill。 | — |
| GA4 | autofill.html:1069-1070（autofill_start）, 1104-1105（autofill_error）, 1114-1115（autofill_error）, 1150-1152（autofill_success）。 | 実運用で GA4 が有効かは env 次第。 |

---

### B-3. /tools（ツール一覧）

| 観点 | 事実 | 推測・証跡不足 |
|------|------|----------------|
| 薄さ | tools/index.html:227 に h1「ツール一覧」。製品カードは products ループ。 | ツール一覧ページ単体の本文量は少なめ。導線で各ツール・ガイドに分散。 |
| 導線 | ヘッダ・フッター＋製品カードから各 product.path / guide_path。 | — |
| 開示 | 同上。 | — |
| 404/301/canonical | 200。canonical /tools。 | — |
| GA4 | page_view のみ（ツール個別ページでは tool-runner.js で tool_run_start / tool_download）。 | — |

---

### B-4. /guide（ガイド一覧）

| 観点 | 事実 | 推測・証跡不足 |
|------|------|----------------|
| 薄さ | guide/index.html:31 h1「ガイド一覧」、35 h2「ツール別ガイド」。以降はリンク一覧中心。 | ガイド一覧は薄め。詳細は各 /guide/* にあり。 |
| 導線 | nav + footer + ガイド一覧リンク。 | — |
| 開示 | 同上。 | — |
| 404/301/canonical | 200。canonical /guide。 | — |
| GA4 | page_view のみ。 | — |

---

### B-5. /privacy

| 観点 | 事実 | 推測・証跡不足 |
|------|------|----------------|
| 薄さ | privacy.html: h1=1, h2=10（はじめに〜お問い合わせ）。段落・リストで構成。 | 十分な構造。 |
| 導線 | 140-141: お問い合わせは /contact へ。143: 「← トップページに戻る」→ /。77: header, 147: footer。 | — |
| 開示 | 128行目: Cookie（クッキー）の使用。131-135: 第三者配信事業者（Google AdSense）、Cookie、オプトアウトリンク（Google広告設定、aboutads.info）。140-141: お問い合わせは /contact。 | AdSense 必須開示は揃っている。 |
| 404/301/canonical | 200。canonical /privacy。 | — |
| GA4 | page_view のみ。 | — |

---

### B-6. /terms

| 観点 | 事実 | 推測・証跡不足 |
|------|------|----------------|
| 薄さ | terms.html: h1, 複数 h2。138行目に AdSense 言及。 | 十分。 |
| 導線 | 138: プライバシーポリシー「第三者配信事業者」節へ /privacy リンク。ヘッダ・フッター。 | — |
| 開示 | 138: AdSense 配信予定・個人情報は /privacy 参照。 | 問い合わせ先は /contact（フッター等で到達可能）。 |
| 404/301/canonical | 200。canonical /terms。 | — |
| GA4 | page_view のみ。 | — |

---

### B-7. /about

| 観点 | 事実 | 推測・証跡不足 |
|------|------|----------------|
| 薄さ | about.html: h1, 複数 h2/h3。開発背景・技術・セキュリティ・運営者プロフィール等。 | 十分。 |
| 導線 | 294-295, 306, 367-368, 377: /contact へのリンク。ヘッダ・フッター。 | — |
| 開示 | 308-330: 運営者情報（OPERATOR_NAME, OPERATOR_EMAIL, OPERATOR_LOCATION, OPERATOR_NOTE）。app.py:342-346 で env 注入。未設定時は「運営者情報」ブロック非表示。 | 本番で OPERATOR_* が未設定だと運営者情報が空になる。AdSense 審査では明示推奨のため証跡として「本番 env 確認」を推奨。 |
| 404/301/canonical | 200。canonical /about。 | — |
| GA4 | page_view のみ。 | — |

---

### B-8. /contact

| 観点 | 事実 | 推測・証跡不足 |
|------|------|----------------|
| 薄さ | contact.html: h1=1, h2=2（FAQ・お問い合わせの前に）。問い合わせ方法（フォーム・メール・GitHub）＋FAQ。 | 十分。 |
| 導線 | フォーム iframe、OPERATOR_EMAIL 時はメールリンク、GitHub Issues リンク。ヘッダ・フッター。 | — |
| 開示 | 問い合わせ先: Google フォーム埋め込み＋OPERATOR_EMAIL が設定時はメール表示（contact.html:140-145）。運営者名・所在地は /about の OPERATOR_*。 | OPERATOR_EMAIL 未設定時は「フォーム＋GitHub」のみ。審査で「連絡先が分かりにくい」と指摘される可能性は推測。 |
| 404/301/canonical | 200。/contact/ は 301 → /contact。canonical /contact。 | — |
| GA4 | page_view のみ。 | — |

---

### B-9. ツール代表（/tools/seo, /tools/csv, /guide/csv）

| 観点 | 事実 | 推測・証跡不足 |
|------|------|----------------|
| ステータス | verify_deploy_routes.py および smoke_test.py --deploy で 200 確認。 | — |
| GA4 | static/js/tool-runner.js:111-114（tool_run_start）, 419-423（tool_download）, 454-457（tool_download ZIP）。ツール利用時に発火。 | page_view に加え conversion 寄りのイベントあり。 |

---

## C. バックログ1枚（TSV・コピペ用）

以下は優先度順。問題は「事実」に基づき記載。最小修正案は差分を小さくする観点。

```
優先度(P0/P1/P2)	URL	問題（事実）	影響	最小修正案	必要な証跡（不足なら）
P1	/about, /contact	運営者情報・問い合わせ先が OPERATOR_* 未設定時に非表示（about.html:309-330, contact.html:140-148）。コード上は「設定されていれば表示」のみ。	AdSense/利用者から「運営者・連絡先が不明」と見なされる可能性。	本番で OPERATOR_NAME / OPERATOR_EMAIL / OPERATOR_LOCATION を設定。未設定時は about に「お問い合わせは /contact から」等のフォールバック文言を表示するようテンプレを1行追加。	本番 env の有無（証跡として一覧取得推奨）。
P1	全ページ	canonical のドメインが head_meta.html:30,36 で固定（jobcan-automation.onrender.com）。ドメイン変更時や staging で誤 canonical になる。	検索・OGP が別ドメインに飛ぶ。	設定可能なら BASE_URL を env 化し、canonical/og:url を {{ BASE_URL }}{{ request.path }} に変更。	現状は本番固定で問題ない場合は P2 に繰り下げ可。
P2	/（LP）	LP 本文に「お問い合わせ」への明示リンクなし（ヘッダ・フッター経由のみ）。	迷子リスクは低いが、審査で「問い合わせ先が分かりにくい」と指摘される可能性。	「セキュリティとプライバシー」セクション付近に「お問い合わせはこちら」を1行追加（/contact へのリンク）。	—
P2	/guide, /tools	ガイド一覧・ツール一覧の本文が薄い（h1+リンク中心）。	AdSense「薄いコンテンツ」判定の要因になりうる。	各1〜2段落の導入文を追加（独自の説明文）。	文字数・類似ページとの差の証跡は未取得。
P2	全ページ	GA4 は GA_MEASUREMENT_ID 未設定時は読み込まれない（head_meta.html:2-13）。	本番で ID 未設定だと page_view/custom イベントが取れない。	本番 env に GA_MEASUREMENT_ID を設定。設定済みかは証跡として確認推奨。	本番環境変数一覧（GA_MEASUREMENT_ID の有無）。
P0	—	特になし。	—	—	404/301/canonical/必須開示はコード上・テストで問題なし。
```

**TSV のみ（表計算用）**

| 優先度 | URL | 問題（事実） | 影響 | 最小修正案 | 必要な証跡 |
|--------|-----|-------------|------|------------|------------|
| P1 | /about, /contact | 運営者・問い合わせ先が OPERATOR_* 未設定時は非表示 | 審査・利用者から不明と見なされる可能性 | 本番で OPERATOR_* 設定、または未設定時フォールバック文言 | 本番 env 一覧 |
| P1 | 全ページ | canonical/og:url がドメイン固定 | ドメイン変更時に誤 canonical | BASE_URL を env 化して差し替え（任意） | — |
| P2 | / | LP 本文にお問い合わせ直リンクなし | 問い合わせ導線がやや弱い | セクションに「お問い合わせはこちら」1行追加 | — |
| P2 | /guide, /tools | 一覧ページが薄い（h1+リンク中心） | 薄いコンテンツ判定の要因になりうる | 導入文1〜2段落追加 | — |
| P2 | 全ページ | GA_MEASUREMENT_ID 未設定時は GA4 未読み込み | 計測が取れない | 本番で ID 設定 | 本番 env 確認 |
| P0 | — | 404/301/canonical/必須開示はコード上問題なし | — | — | — |

---

## D. 追加で取るべき証跡リスト

1. **本番環境変数**  
   - `OPERATOR_NAME`, `OPERATOR_EMAIL`, `OPERATOR_LOCATION`, `OPERATOR_NOTE` が設定されているか。  
   - `GA_MEASUREMENT_ID` が設定されているか。  
   - （任意）`BASE_URL` や canonical 用のドメイン設定の有無。

2. **本番 HTTP 証跡（--live 使用時）**  
   - `python scripts/verify_deploy_routes.py --live https://jobcan-automation.onrender.com` の出力を保存。  
   - 上記主要URL（/, /autofill, /contact, /privacy, /terms, /about, /tools, /guide）の status と Location（301 時）を記録。

3. **AdSense 審査**  
   - 審査結果メール・管理画面の「理由」があれば保管。コード上の開示（cookie/第三者/問い合わせ/運営者）と突き合わせ用。

4. **Search Console**  
   - インデックス状況・カバレッジ・canonical の扱い。必要に応じて URL 検査で主要ページの「正規 URL」を確認。

5. **文字数・独自性（薄さの定量）**  
   - 各主要ページの本文文字数（HTML タグ除く）を取得。必要なら `analyze_adsense_content.py` 等で再利用。

---

**以上、Phase 0 の棚卸しレポートとする。バックログは C の TSV/表を最優先度順に実装し、D の証跡で本番状態を補足することを推奨する。**
