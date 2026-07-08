# Phase A: 事実確認メモ（トピカリティ Phase B 実装前）

**日付**: 2026-02-10  
**目的**: 実装前の現状を記録し、実装方針とテストの期待値を決める。

---

## 1. URL ステータス確認（本番・ローカル）

以下を本番とローカルで実施し、結果をメモする。

| URL | 期待（実装前の想定） | 本番 ステータス | ローカル ステータス | 備考 |
|-----|----------------------|-----------------|---------------------|------|
| GET /tools/pdf | 200 | （要確認） | （要確認） | 存在するページ |
| GET /tools/pdf/ | 200 または 404 | （要確認） | （要確認） | 末尾スラッシュあり |
| GET /guide/pdf | 200 | （要確認） | （要確認） | 存在するページ |
| GET /guide/pdf/ | 200 または 404 | （要確認） | （要確認） | 末尾スラッシュあり |
| GET /blog | 200 | （要確認） | （要確認） | 存在するページ |
| GET /blog/ | 200 または 404 | （要確認） | （要確認） | 末尾スラッシュあり |
| GET /path | 404 | （要確認） | （要確認） | 存在しないURL |
| GET /path/ | 404 | （要確認） | （要確認） | 存在しないURL（リダイレクトしてはいけない） |

**確認方法（例）**

- ブラウザの開発者ツールの Network でステータスを確認。
- または `curl -I -s -o /dev/null -w "%{http_code}" https://本番ドメイン/tools/pdf` でコード取得。

**実装後の期待**

- 存在するページの末尾スラッシュ版（例: /tools/pdf/）→ 301 で末尾なし（/tools/pdf）へリダイレクト。
- 存在しない URL（/path/）→ 301 にしない。404 のまま。

---

## 2. ツールページの「ガイド」リンク有無

| ファイル | ガイドへの明示リンク | 備考 |
|----------|------------------------|------|
| templates/tools/pdf.html | あり（`tool_guide_link.html` include） | product.guide_path で /guide/pdf |
| templates/tools/image-batch.html | あり | 同上 /guide/image-batch |
| templates/tools/image-cleanup.html | あり | 同上 /guide/image-cleanup |
| templates/tools/minutes.html | あり | 同上 /guide/minutes |
| templates/tools/seo.html | あり | 同上 /guide/seo |

**結論**: 全ツールページに「当該ツールの使い方ガイド」へのリンクあり。P1 で共通パーツ化・アンカーを「〇〇の使い方ガイド」に統一済み。

---

## 3. meta description が空になる可能性

- **head_meta.html**: `{% block description_meta %}{% endblock %}` のみの場合、子テンプレートでブロックを定義しないと description が空になる。
- **確認**: 各ページで `{% block description_meta %}<meta name="description" content="...">{% endblock %}` を定義しているか。未定義のテンプレートがあるとそのページで description が空。
- **対応**: Phase B で `head_meta.html` のブロック内にデフォルトの `<meta name="description">` を記述し、未定義時も空にならないようにした。

---

## 4. 実装方針の決定（Phase B に反映）

- **末尾スラッシュ**: 末尾スラッシュを除いたパスが **Flask の url_map で解決できる場合のみ** 301 リダイレクト。存在しない URL（/path/）はリダイレクトしない。GET/HEAD のみ対象。`/api`・`/static` は除外。
- **X-Robots-Tag**: /status/・/api/ および一時的エンドポイントに付与。通常ページには付けない。
- **description**: デフォルトを head_meta に追加。
- **ツール→ガイド**: 共通パーツで「〇〇の使い方ガイド」を表示（済）。

以上。
