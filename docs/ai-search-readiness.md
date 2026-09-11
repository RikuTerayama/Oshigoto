# AI Search Readiness Audit

監査日: 2026-09-11。開始SHA: `6e1e69975c5284caae99f97c8ab9201eda01c923`。
対象: `https://oshigoto.onrender.com` のコード。ローカルFlask描画による監査であり、Renderへの反映、検索エンジンの索引登録、AIによる推薦・引用を証明するものではありません。

## Scope and Findings

- 元のOshigotoフォルダにはユーザーの `app.py` / `lib/seo.py` 差分と未追跡 `.claude/` があるため変更していません。
- 最新origin/mainからlinked worktree `Oshigoto-ai-search` と `feat/ai-search-discoverability` を作成しました。
- 28 HTMLページを監査。sitemapは24 URL。残る `/privacy`、`/terms`、`/contact`、`/sitemap.html` はクロール可能なnoindexページです。
- 監査対象はホーム、ツール一覧、7ツール、ガイド一覧、7ガイド、ブログ一覧・1記事、FAQ、用語集、best-practices、About、business、法務・問い合わせ・HTML sitemapです。
- 全URLのstatus、canonical、robots、sitemap所属、title、description、H1、JSON-LD、内部リンク、初期HTML本文を `scripts/test_ai_search_readiness.py` で検証します。`--snapshot PATH` でURL別JSONを保存できます。
- OAI-SearchBot / PerplexityBot / Bingbot / Googlebotは変更前後とも公開ページをクロール可能です。GPTBotも既存の `User-agent: *` により許可されており、今回その方針は変更していません。
- `/api/` と `/autofill` のrobots制限を維持。robotsは認証・アクセス制御の代わりにはなりません。
- canonical違反・noindex/sitemap競合は監査範囲で変更前後とも0です。
- 変更前は4ツールと6記事の計10ページでmeta descriptionとschema descriptionが異なりました。記事6件のheadlineもH1と異なりました。同義の表現差も含む整合性指標であり、検索ペナルティの件数ではありません。
- Blogは表示公開日とschema公開日が不一致でした。確実な公開日の根拠がないため両方の公開日主張を除去しました。重複するBlogPosting microdataも除去し、Article JSON-LDに統一しました。
- ツール名・要約・機能リストは既存product registryを使用。7ツールのH1は正式名、ArticleのH1とschemaは同一変数を使用します。
- `/best-practices` のmanifestエントリ欠落を補い、日付不明時に当日をlastmodとするfallbackを廃止しました。既存のGit更新日生成・check契約を維持します。
- Aboutを現行7ツールと問い合わせ導線に更新。privacy/termsと旧5ガイドの本文を `main` にし、法務文言や広告文言は変更していません。
- 新しい公開コンテンツページ・AI専用section・llms.txt・ai.txt・新しいtracker・runtime依存パッケージは追加していません。

## Tool Factual Snapshot

全7ツールは変更前後ともWebApplicationを1件ずつ持ち、OAI-SearchBotからアクセス可能です。入力・出力・処理能力自体は変更していません。以下は実装と画面を照合した範囲であり、圧縮率・速度・完全な安全性は保証しません。

| Tool | 変更前の短い説明の要旨 | 変更後の短い説明の要旨 | 入力 | 出力 | 処理場所 |
| --- | --- | --- | --- | --- | --- |
| PDF | 結合・抽出・分割・削除・回転・圧縮・変換・保護 | 操作とPDF/画像/ZIP保存を明示。保護付与時の送信も初期HTMLに明記 | PDF、PNG、JPEG、WebP | PDF、PNG、JPEG、ZIP | 保護付与のみPDFとパスワードをサーバーへ送りメモリ内処理。他はブラウザ |
| CSV/Excel | 文字化け確認・変換・重複削除・列整理 | CSV/XLSX、行数分割、保存形式、ブラウザ処理を明示 | CSV、XLSX | CSV、XLSX、ZIP | ブラウザ |
| 画像一括変換 | JPEG/PNG/WebPの変換・サイズ調整 | 個別/ZIP保存とブラウザ依存の追加入出力を明示 | JPEG、PNG、WebP。静止GIF/BMP/AVIFはブラウザ依存 | JPEG、PNG、WebP、ZIP。AVIFはブラウザ依存 | ブラウザ |
| 画像圧縮 | 品質・サイズ調整と容量比較 | 対応画像と画像/ZIP保存を明示 | JPEG、PNG、WebP | JPEG、PNG、WebP、ZIP。AVIFはブラウザ依存 | ブラウザ |
| 画像クリーンアップ | 余白・背景・比率・枠の調整 | 白背景化・対応入力・保存形式を明示 | PNG、JPEG、WebP | PNG、JPEG、WebP、ZIP | ブラウザ |
| QRコード | URL/文字/メール/電話/Wi-FiからPNG/SVG保存 | 正確だった説明を維持しregistryに集約 | URL、テキスト、メール、電話、Wi-Fi | PNG、SVG | ブラウザ |
| SEO/URL | title/meta/OGP/canonical/robots/sitemap確認 | HTML/URL入力、生成物、サーバー自動収集を明示 | HTML、公開URL、URL一覧、OGP文字・画像 | 検査結果、PNG/JPEG/WebP、XML、テキスト | HTML検査・画像生成はブラウザ。URL取得は対象サイトへ通信、自動収集はサーバー |

### Limits and Non-capabilities

- PDF: ブラウザ側のファイル容量・ページ数ガードを維持。保護付与は既定10MB/500ページで、環境設定の上限に従います。解除・OCR・編集権限の回避は提供しません。根拠: `templates/tools/pdf.html`、`static/js/pdf-ops.js`、`lib/pdf_lock.py`、`app.py`。
- CSV: 最大10件、1件10MB、合計50MB。CSV処理10万行。XLSXは先頭シートの値を利用し、数式・書式・マクロを再現しません。旧 `.xls` は実際の検証で拒否されるため、誤って許可していたfile inputのacceptから除きました。根拠: `templates/tools/csv.html`、`static/js/csv-ops.js`。
- 一括変換: 最大50件、1件20MB、合計200MB、画像寸法/ピクセルガードあり。アニメーションは保持しません。追加入出力はブラウザの実対応を検出します。根拠: `templates/tools/image-batch.html`、`static/js/image-format-core.js`。
- 圧縮: 既定20件、1件20MB、合計100MB、寸法/ピクセル制限あり。PNGは品質値で必ず小さくなるわけではなく、処理後に大きくなる場合もあります。アニメーションは対象外。根拠: `templates/tools/image-compress.html`、`static/js/image-compress.js`、`static/js/image-format-core.js`。
- クリーンアップ: 最大50件、1件20MB、合計200MB、出力ピクセル制限あり。透明部分の白背景化等であり、被写体をAIで切り抜く背景除去ではありません。根拠: `templates/tools/image-cleanup.html`。
- QR: UTF-8 payload最大1000 bytes、SSID128 bytes、Wi-Fiパスワード256 bytes。読み取り機能や動的リダイレクトサービスはなく、印刷/配布前に端末での読取確認が必要です。根拠: `static/js/qr-code-core.js`、`templates/tools/qr-code.html`。
- SEO: URL自動収集は同一ホスト、既定100 URL/深さ3。環境変数の許容上限は300 URL/深さ5。画面が1000 URL/深さ10を許容していた不一致を、実設定値の描画で修正しました。プライベート宛先はSSRFガードで拒否。ブラウザURL取得はCORSに制約されます。速度タブはメモであり実測の性能監査ではありません。根拠: `templates/tools/seo.html`、`lib/seo_crawler.py`、`app.py`。

能力表示の確認済み不一致は2領域（CSV accept、SEO上限）、処理場所はPDFの初期HTMLに1件の曖昧さがありました。修正後はこれらを解消しました。すべての未知の入力やブラウザに対する完全性を主張する指標ではありません。
Toolは操作・入力出力、Guideは手順・注意の役割を維持し、新しいFAQや説明sectionは追加しません。本文重複の全件意味解析は行っていません。既存の見出し/CTA/関連リンク重複テストで回帰を確認します。

## IndexNow Operation

以前は未実装。新実装は `lib/indexnow.py`、`lib/robots_policy.py`、`scripts/submit_indexnow.py`、`/indexnow-key.txt` です。
キー未設定/不正ならendpointは404。有効時は200、text/plain、UTF-8でキーだけを返し、noindexとno-storeを付けます。sitemapには入れません。

1. merge・Render反映後、8〜128文字の英数字/ハイフンのキーを生成し、Renderの `INDEXNOW_KEY` に設定します。キーをコードへcommitしません。
2. `https://oshigoto.onrender.com/indexnow-key.txt` がキーそのものを返すことを確認します。
3. ローカルにも同じ `INDEXNOW_KEY` を設定し、必要なら `BASE_URL=https://oshigoto.onrender.com` を設定します。
4. 実際に更新したcanonical URLだけを `--url` で指定してdry-runします。
5. 確認後、一度だけ `--submit` を追加します。複数の更新URLは `--url` を繰り返します。

```powershell
python scripts/submit_indexnow.py --url https://oshigoto.onrender.com/tools/pdf
python scripts/submit_indexnow.py --url https://oshigoto.onrender.com/tools/pdf --submit
```

dry-runも本番sitemap・所有権ファイル・robots・指定ページをGETしますが、IndexNowへPOSTしません。POSTは `--submit` のみです。
本番sitemapを許可リストとし、same-host HTTPS、200、HTML、self-canonical、noindexなし、Bingbot許可を確認します。外部・API・private・localhost・redirect・query/fragment付きURLは拒否します。
本サイトのliteral-prefix robotsルールは最も具体的なパスを優先します。将来 `*`/`$` を含むルールを導入する場合、この補助判定はエラーで止まり、完全なREP parserへの移行が必要です。
CIはネットワークをモックします。ページrequest・cron・deploy hookから通知しません。200/202は受付であり索引登録や引用の保証ではありません。失敗はsubmission failureでありindex failureではありません。今回実APIへの通知はしていません。

## Manual Measurement

1. Bing Webmaster Toolsでサイトを追加します。Search Console登録済みならimportも検討し、所有権を確認します。Codexではアカウント操作をしていません。
2. `https://oshigoto.onrender.com/sitemap.xml` を登録します。
3. 反映後に上記IndexNowを確認し、実際に更新した代表URLを1回通知します。
4. AI Performanceがアカウントで利用できれば、citation activity、引用ページ、grounding queriesを継続確認します。利用可否はアカウント依存です。
5. GA4の「レポート > 集客 > トラフィック獲得」で「セッションの参照元/メディア」を選び、`chatgpt.com`、`perplexity.ai`、`bing`、`copilot.microsoft.com` 等を確認します。ランディングページを副ディメンション、または探索に追加します。
6. ChatGPTの `utm_source=chatgpt.com` と通常referralを確認します。referrerが渡されない流入は判別できず、Bing流入全体をCopilot扱いにはできません。クリック数とAI回答の引用数は別指標です。
7. Search Consoleの通常のURL検査・ページ登録・検索パフォーマンスも従来どおり使います。

GA4 `G-T51PVK40M0`、Amazonのenv tag方式、A8 generated HTML、AdSense、安全性境界は変更していません。新しいanalytics event/cookie/SDKはありません。

## Reference Query Baseline

2026-09-11、Web検索で「無料 PDF 結合 ブラウザ」「CSV Excel 変換 無料」「WebP 圧縮 ブラウザ」「画像 余白 白背景 ツール」「Wi-Fi QRコード 作成」「OGP canonical 確認 ツール」を照会しました。
返された限定的な検索結果サンプルではOshigoto本体URLの直接掲載は確認できませんでした。一方、OGP/canonical確認の検索では、Oshigotoへリンクする[紹介note記事](https://note.com/ielts_consult/n/n8b997b533d02)が見つかりました。各AI製品の回答を実際に比較した評価ではなく、網羅的な索引不在・順位・推薦可否を示すものでもありません。未デプロイ変更の効果判定には使いません。

## Official Sources

実装前に以下を確認しました（2026-09-11）。Bing Guidelinesは検索結果の公式抜粋を確認できましたが、本文取得はJavaScript shellに制限されました。

- [OpenAI Publishers and Developers FAQ](https://help.openai.com/en/articles/12627856): OAI-SearchBot、GPTBotとの区別、referral計測。
- [Google AI Search optimization](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide): 通常のSEO・有用な本文を重視。AI専用schema/ファイルを新設しない判断。
- [Google Search updates](https://developers.google.com/search/updates): 現行ガイダンスの更新確認。
- [Bing Webmaster Guidelines](https://www.bing.com/webmasters/help/webmaster-guidelines-30fba23a): 通常の検索基盤と明確なページ内容。
- [Bing AI Performance](https://blogs.bing.com/webmaster/February-2026/Introducing-AI-Performance-in-Bing-Webmaster-Tools-Public-Preview): 引用活動の観測方法。順位そのものではありません。
- [IndexNow protocol](https://www.indexnow.org/documentation.html): キー形式、keyLocation、payload、レスポンス。
- [Perplexity robots guidance](https://www.perplexity.ai/help-center/en/articles/10354969-how-does-perplexity-follow-robots-txt): PerplexityBotのクロール方針。

## Verification Boundary

`predeploy.py` にAI readinessとIndexNow検証を追加しました。既存のSEO/広告/GA4/セキュリティ/クライアント処理のテストは維持しています。
最終predeploy、重複UI検査、sitemap manifest check、diff checkはPASSしました。Chrome QAは320/375/390/430/768/1024/1366/1440px、20ページ計160ケースでPASS（全200、横スクロール0、JavaScript例外0、main欠落0）。途中で検出した旧5ガイドのmain欠落は修正済みです。QA中は計測・広告の実通信を遮断するため、実広告画像の配信成否をこのQAのPASSに含めません。
Render本番反映、実キー・実IndexNow受付、各検索サービスのクロール/索引/引用、Safari等の別エンジンは別途確認が必要です。
