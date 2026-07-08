# Phase 1 実装と検証（AdSense承認〜拡散向け）

**日付**: 2026-02-12  
**目的**: Phase 0 棚卸しの P1 地雷を最小差分で潰す（運営者/連絡先フォールバック、BASE_URL 化、一覧ページ導入文、LP 問い合わせ CTA）。

---

## 1) 事実確認（コード）

| 対象 | 箇所（file:line） |
|------|-------------------|
| about.html OPERATOR_* 条件 | 309-335: `{% if OPERATOR_NAME or OPERATOR_EMAIL or OPERATOR_LOCATION %}` で運営者情報ブロック。未設定時は何も表示されない状態だった。 |
| contact.html OPERATOR_EMAIL 条件 | 140-148: `{% if OPERATOR_EMAIL %}` でメール案内。未設定時はフォーム＋GitHub のみで「主導線」の説明がなかった。 |
| head_meta canonical/og:url | 30行目 canonical, 36行目 og:url — いずれも `https://jobcan-automation.onrender.com` 固定。 |
| app.py env 注入 | 307-368: `inject_env_vars()` で OPERATOR_*, GA_MEASUREMENT_ID, GSC_VERIFICATION_CONTENT 等を注入。BASE_URL は未注入だった。 |

---

## 2) 実装サマリ（コミット単位）

### Commit 1: fix(about/contact): add fallback when OPERATOR_* missing

**変更ファイル**
- `templates/about.html`
- `templates/contact.html`

**差分要約**
- **about.html**: `{% if OPERATOR_NAME or ... %}` の `{% endif %}` の直前に `{% else %}` を追加。運営者情報が空のときも「運営者情報」見出し＋「お問い合わせはお問い合わせページから」の短文と /contact リンクを表示。
- **contact.html**: `{% if OPERATOR_EMAIL %}` の `{% endif %}` の直前に `{% else %}` を追加。メール未設定時は「お問い合わせの受け付けについて」＋「上記フォームが主な窓口」「返信はフォーム記入アドレスへ」の案内を表示。

**受け入れ基準**
- OPERATOR_* を空にした状態でも /about, /contact が不自然に空にならない → 確認済み（verify_phase1.py）
- 表示崩れなし → 既存スタイルの article/div で統一

---

### Commit 2: chore(meta): make base url configurable

**変更ファイル**
- `app.py`
- `templates/includes/head_meta.html`

**差分要約**
- **app.py**: `inject_env_vars()` の return 辞書（成功・失敗両方）に `'BASE_URL': os.getenv('BASE_URL', 'https://jobcan-automation.onrender.com').rstrip('/')` を追加。
- **head_meta.html**: canonical の href を `{{ BASE_URL|default('https://jobcan-automation.onrender.com') }}{% if request and request.path %}{{ request.path }}{% else %}/{% endif %}` に変更。og:url も同様。

**受け入れ基準**
- BASE_URL 未設定 → 今と同じ canonical/og:url → 確認済み（デフォルト値）
- BASE_URL 設定 → その値に切り替わる → テンプレートで {{ BASE_URL }} を参照するため保証

---

### Commit 3: content(tools/guide): add intro paragraphs

**変更ファイル**
- `templates/tools/index.html`
- `templates/guide/index.html`

**差分要約**
- **tools/index.html**: page-header 内に2段落目を追加。「Jobcan自動入力・画像一括変換・PDF・CSV/Excel・Web/SEO など、Automation Hub で提供しているツールの入口です。各ツールはブラウザ内で完結…」。
- **guide/index.html**: h1 と lead の下に1段落追加。「Automation Hub のツールを初めて使う方は…」「トラブルシューティング」「Excelファイルの作成方法」を参照、の案内。

**受け入れ基準**
- 見出し構造維持 → h1 のあと lead＋1文のため変更なし
- 独自説明文・表示崩れなし → 既存 class とスタイルで追加

---

### Commit 4: content(lp): add contact CTA

**変更ファイル**
- `templates/landing.html`

**差分要約**
- 「セキュリティとプライバシー」セクション内、trust-badges の直後に1行追加: 「ご質問・ご要望はお問い合わせからどうぞ。」（/contact へのリンク）。

**受け入れ基準**
- 表示崩れなし → 既存 .trust-section 内の p タグで追加

---

## 3) 検証証跡

| コマンド | 結果 | 要点 |
|----------|------|------|
| `python scripts/smoke_test.py --deploy` | exit 0 | tools/seo, tools/csv, guide/csv=200；minutes 301；/tools/pdf/ 301 |
| `python scripts/verify_deploy_routes.py` | exit 0 | 上記と同様の curl 風証跡を出力、全 OK |
| `python scripts/verify_phase1.py` | exit 0 | canonical デフォルトドメイン、LP お問い合わせ CTA、about/contact フォールバック文言を確認 |

**view-source 確認（手動）**
- BASE_URL 未設定時: canonical および og:url が `https://jobcan-automation.onrender.com` + path となること。
- BASE_URL 設定時: 設定した値 + path となること（本番で必要に応じて確認）。

**OPERATOR_* 空での確認**
- ローカルで環境変数なし（または空）で起動し、/about に「運営者情報」＋「お問い合わせページ」リンクが表示されること、/contact に「お問い合わせの受け付けについて」および「主な窓口」の案内が表示されること（verify_phase1.py で自動確認済み）。

---

## 4) 追加スクリプト

- `scripts/verify_phase1.py`: Phase1 の受け入れ条件（canonical デフォルト、LP contact CTA、about/contact フォールバック）をテストクライアントで検証。CI やデプロイ前の実行を推奨。

---

**以上、Phase 1 実装と検証の記録とする。**
