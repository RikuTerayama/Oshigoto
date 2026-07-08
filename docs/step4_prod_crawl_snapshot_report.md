# Step 4 本番クロールスナップショット監査レポート

**作成日**: 2026-02-27  
**対象**: 本番環境 `https://jobcan-automation.onrender.com`  
**目的**: GSC「クロール済み-インデックス未登録」6URLの阻害要因を実測で特定する（実装は行わない）

---

## 1) 結論サマリ（最大8行）

- 対象7URL（6URL＋/case-studies）はすべて **HTTP 200**、canonical 自己参照、x-robots-tag なし、meta robots なし。技術的にインデックス阻害要因は見当たらない。
- **/（LP）** は hero 直下に /guide・/blog・glossary・tools・case-studies へのリンクがあり、内部導線は Step 3 で強化済み。
- **/blog** と **/best-practices** から /case-studies へのリンクあり。**/glossary** にはショートカットアンカー（basic-terms, jobcan-terms, autofill-terms, it-security）が存在。
- **robots.txt**: 200、Sitemap 行は BASE と一致（`https://jobcan-automation.onrender.com/sitemap.xml`）。Googlebot は Allow: / でブロックされていない。
- **sitemap.xml**: 200、47件、/case-studies 含む。**lastmod が全47件同一日付（2026-02-26）** のため、ページごとの差分が出ていない。
- 本文文字数は / が約1,972文字、/case-studies が約1,803文字とやや少なめだが、極端に少ない水準ではない。他ページは 2,800〜5,500 文字程度。
- インデックス未登録の典型的技術原因（canonical 誤り・noindex・robots ブロック・内部リンク欠如）は本スナップショットでは確認されなかった。
- lastmod 同一化は sitemap 品質として改善余地あり（P1）。未登録はクロール頻度・コンテンツの独自性評価など、本レポート外要因の可能性がある。

---

## 2) URL別スナップショット

| Path | Status | final_url | canonical | meta robots | body_chars | 内部リンク数 | /guide | /blog | /glossary | /tools | /case-studies |
|------|--------|-----------|-----------|-------------|------------|-------------|--------|-------|-----------|--------|---------------|
| / | 200 | BASE/ | 自己 | なし | 1,972 | 30 | ✓ | ✓ | ✓ | ✓ | ✓ |
| /best-practices | 200 | BASE/best-practices | 自己 | なし | 5,521 | 30 | ✓ | ✓ | ✓ | ✓ | ✓ |
| /privacy | 200 | BASE/privacy | 自己 | なし | 2,886 | 30 | ✓ | ✓ | ✓ | ✓ | ✓ |
| /blog | 200 | BASE/blog | 自己 | なし | 3,413 | 44 | ✓ | ✓ | ✓ | ✓ | ✓ |
| /guide/excel-format | 200 | BASE/guide/excel-format | 自己 | なし | 5,086 | 30 | ✓ | ✓ | ✓ | ✓ | ✓ |
| /glossary | 200 | BASE/glossary | 自己 | なし | 5,117 | 30 | ✓ | ✓ | ✓ | ✓ | ✓ |
| /case-studies | 200 | BASE/case-studies | 自己 | なし | 1,803 | 33 | ✓ | ✓ | ✓ | ✓ | ✓ |

### 補足

- **cache-control**: 全ページ `no-store, max-age=0`
- **x-robots-tag**: 全ページ空
- **content-type**: 全ページ `text/html; charset=utf-8`
- **JSON-LD**: 全ページに `script type="application/ld+json"` あり（2〜4ブロック）
- **/glossary ショートカットアンカー**: basic-terms, jobcan-terms, autofill-terms, it-security の4つとも存在

---

## 3) robots.txt チェック結果

| 項目 | 結果 |
|------|------|
| HTTP status | 200 |
| Sitemap 行 | `Sitemap: https://jobcan-automation.onrender.com/sitemap.xml`（BASE と一致） |
| User-agent: * | Allow: /、Disallow: /status/, /api/, /sessions, /download-template, /download-previous-template, /cleanup-sessions |
| User-agent: Googlebot | 上記と同様。Allow: / あり、主要ページはブロックされていない |
| User-agent: AdsBot-Google | 上記と同様 |
| 問題 | なし（想定どおり） |

---

## 4) sitemap.xml チェック結果

| 項目 | 結果 |
|------|------|
| HTTP status | 200 |
| loc 件数 | 47 |
| /case-studies 含む | ✓ 含む |
| lastmod 件数 | 47 |
| lastmod ユニーク数 | **1**（全件同一日付 2026-02-26） |
| 問題 | lastmod がページごとに差分が出ておらず、全件同一 |

---

## 5) 問題の疑いがある項目（優先度 P0/P1/P2）

| 優先度 | 項目 | 内容 |
|--------|------|------|
| P1 | sitemap lastmod 同一 | 全47件の lastmod が 2026-02-26 で同一。テンプレート mtime ベースの実装がデプロイ日で固定されている可能性。検索エンジンに「更新の差異」が伝わりにくい。 |
| P2 | / の文字数 | 約1,972文字。極端に少ないわけではないが、LP としてはやや控えめ。価値提示文は Step 3 で追加済み。 |
| P2 | /case-studies の文字数 | 約1,803文字。事例一覧ページとして許容範囲。 |
| - | その他 | canonical・noindex・robots ブロック・主要リンク欠如は確認されず。 |

**P0 相当の技術的阻害要因は見当たらない。**

---

## 6) 次の実装候補（コードは書かない）

- **sitemap lastmod の差分化（P1）**: 各ページのテンプレートファイルやコンテンツの最終更新日を個別に取得し、lastmod に反映する。現状の「全件同一」を解消し、更新頻度の違いを sitemap から伝えられるようにする。
- **LP の価値提示強化（P2、任意）**: Step 3 で追加した hero 直下の一文に加え、ツール紹介セクション等でテキストを補足する余地はあるが、現状の文字数でも致命的ではない。
- **GSC での再クロールリクエスト（運用）**: 本レポートで技術的問題は見当たらないため、GSC の「URL検査」からインデックス登録をリクエストし、再クロール後の状況を確認する。
- **構造化データの拡充（任意）**: 既に JSON-LD は複数ページにある。Article や BreadcrumbList の検証を GSC で確認し、エラーがあれば修正する。

---

*収集スクリプト: `scripts/step4_prod_crawl_snapshot.py`*  
*生データ: `docs/step4_prod_crawl_raw.json`*
