# 無効トラフィック対策監査レポート（分析のみ・コード変更禁止）

**目的**: AdSense 承認後の事故（無効トラ・ボット・連打・クリック誘導疑義）を最小差分で防ぐため、現状のレート制限・ログ・広告UI・緊急遮断を事実ベースで棚卸しし、次ターン実装バックログを作成する。  
**対象**: Flask app.py / templates / static / Render 運用想定。重点: /tools/*, /api/*, /status/*, /, /autofill, /contact。  
**証跡**: すべて file:line で根拠を明示。推測は「推測」とラベル付け。

---

## A. 守るべきURLマップ（事実）

**ルート一覧の根拠**: `grep "@app.route" app.py` による列挙（app.py 802行〜2038行）。

| URL | 役割 | 想定負荷 | Bot価値 | 優先度 | 備考 |
|-----|------|----------|---------|--------|------|
| / | LP | 高 | 高 | P1 | app.py:802 |
| /autofill | AutoFillページ | 高 | 高 | P1 | app.py:912 |
| /tools | ツール一覧 | 中 | 中 | P1 | app.py:1260 |
| /tools/pdf | PDFツール | 中 | 中 | P1 | app.py:1025 |
| /tools/image-batch | 画像一括 | 中 | 中 | P1 | app.py:1018 |
| /tools/image-cleanup | 画像クリーンアップ | 中 | 中 | P1 | app.py:1139 |
| /tools/seo | SEOツール | 中 | 中 | P1 | app.py:1158 |
| /tools/csv | CSV/Excelツール | 中 | 中 | P1 | app.py:1165 |
| /tools/minutes | リダイレクト→/tools | 低 | 低 | P2 | app.py:1146 |
| /guide | ガイド一覧 | 中 | 中 | P2 | app.py:944 |
| /guide/* | 各ガイド | 中 | 低 | P2 | app.py:955〜1013 |
| /contact | お問い合わせ | 中 | 中 | P1 | app.py:939 |
| /privacy | プライバシー | 低 | 低 | P2 | app.py:929 |
| /terms | 利用規約 | 低 | 低 | P2 | app.py:934 |
| /faq | FAQ | 低 | 低 | P2 | app.py:1273 |
| /upload | POST アップロード | 高 | 高 | P1 | app.py:1609（サーバ処理） |
| /status/<job_id> | ポーリング | 高 | 中 | P1 | app.py:1826 |
| /cancel/<job_id> | POST キャンセル | 中 | 低 | P2 | app.py:1788 |
| /api/pdf/unlock | POST（tool-runner等） | 中 | 中 | P1 | app.py:1043 |
| /api/pdf/lock | POST（tool-runner等） | 中 | 中 | P1 | app.py:1089 |
| /api/minutes/format | POST | 低 | 低 | P2 | app.py:1152 |
| /api/seo/crawl-urls | POST クロール | 中 | 高 | P1 | app.py:1208（レート制限あり） |
| /download-template | GET ダウンロード | 中 | 中 | P2 | app.py:1559 |
| /download-previous-template | GET ダウンロード | 中 | 中 | P2 | app.py:1584 |
| /sessions | 管理用 | 低 | 低 | P2 | app.py:1932 |
| /cleanup-sessions | 管理用 | 低 | 低 | P2 | app.py:1959 |
| /healthz, /livez, /readyz | ヘルス | 高(回数) | 低 | P2 | app.py:1389,1400,1405 |
| /health, /ready, /ping | ヘルス | 中 | 低 | P2 | app.py:1443,1464,1438 |
| /health/memory | GET メモリ | 低 | 低 | P2 | app.py:1478 |
| /ads.txt | 広告用 | 低 | 低 | P2 | app.py:2014 |
| /robots.txt | クローラー用 | 中 | 高 | P2 | app.py:2020 |
| /sitemap.xml | サイトマップ | 中 | 中 | P2 | app.py:2038 |
| /static/* | 静的 | 高 | 低 | P2 | Flask デフォルト（ルート未定義） |

**変換・処理系の区別（事実）**  
- **ブラウザ内のみ**: PDF/画像/CSV/SEO の大半は tool-runner.js または各ページの JS で完結。サーバへは **/api/pdf/unlock**, **/api/pdf/lock**（app.py:1043,1089）、**/api/minutes/format**（1152）、**/api/seo/crawl-urls**（1208）のみ送信。  
- **サーバ内**: **/upload**（1609）で Playwright 実行、**/status/<job_id>**（1826）でポーリング、**/cancel/<job_id>**（1788）でキャンセル。

**X-Robots-Tag: noindex を付けているパス（事実）**  
- **根拠**: app.py:393〜405。`add_noindex_for_dynamic` が after_request で実行。  
- **対象**:  
  - `path.startswith('/status/')` → 全 status ページ（app.py:401）  
  - `path.startswith('/api/')` → 全 API（app.py:401）  
  - `path in _NOINDEX_PATHS` → `/download-template`, `/download-previous-template`, `/sessions`, `/cleanup-sessions`（app.py:394,402）。  
- **error.html**: templates/error.html:6 に `<meta name="robots" content="noindex, nofollow">`（HTML 側）。

---

## B. 現状の防御（レート制限/UA/IP/Referer）有無（事実）

**依存関係（事実）**  
- requirements.txt: Flask, openpyxl, playwright, jpholiday, psutil, gunicorn, requests, beautifulsoup4, pypdf のみ。  
- **Flask-Limiter / slowapi / redis / werkzeug のレート制限ミドルウェアは未使用**（requirements.txt に存在しない）。  
- **reverse proxy 用の ProxyFix 等の設定は app.py に存在しない**（grep "ProxyFix|Forwarded" で 0 件。X-Forwarded-For 参照は後述の 1 箇所のみ）。

**レート制限**  
- **唯一のレート制限**: `/api/seo/crawl-urls` のみ。  
  - **根拠**: app.py:1212〜1223。`_crawl_rate_by_ip` で IP ごとに前回実行時刻を保持し、`_CRAWL_RATE_SEC` 未満で再リクエストすると 429 と Retry-After を返す。  
  - **使用 IP**: `_get_client_ip_for_crawl()`（app.py:1193〜1205）。`request.access_route` と `X-Forwarded-For` を優先し、なければ `request.remote_addr`。  
- **その他エンドポイント**: **レート制限なし**（before_request / after_request / errorhandler に 429 や IP カウントのコードなし。upload, status, /, /tools/* 等に共通の limiter なし）。

**IP 取得方法**  
- **通常ログ（req_start）**: **request.remote_addr のみ**。app.py:132 `logger.info(f"req_start ... ip={request.remote_addr}")`。  
- **Render/プロキシ配下**: ProxyFix 未使用のため、**request.remote_addr はプロキシ（Render の前方）のアドレスになる可能性が高い**。実クライアント IP は X-Forwarded-For に含まれるが、現状アプリでは **crawl API のレート制限時のみ** _get_client_ip_for_crawl() で X-Forwarded-For を参照（app.py:1197）。  
- **結論（事実）**: アクセスログに出す IP は app.py:132 の `request.remote_addr`。クライアント IP を「プロキシ越しの実IP」として扱っているのは app.py:1193〜1205 の _get_client_ip_for_crawl() のみ。

**UA / Referer / Bot 判定**  
- **before_request / after_request に UA 判定・Referer 判定・bot 判定はない**（該当コードなし）。  
- **errorhandler 内**: 500/Exception 時に User-Agent をログに含めている（app.py:221, 284）。通常の req_start/req_end には **UA も Referer も含まれない**。

---

## C. 現状ログに何が残るか（足りない項目を列挙）（事実）

**アクセスログを出している箇所**  
- **Flask 標準の logging**（app.py:28〜33）。`logging.basicConfig` で format/datefmt 設定。`logger = logging.getLogger(__name__)`（34）。  
- **独自の req_start / req_end**: app.py:131〜132（before_request）、app.py:142〜152（after_request）。ヘルスチェック path（/healthz, /livez, /readyz）は除外。

**1 リクエストあたり取得している情報（事実）**  
- **req_start**: `rid`, `method`, `path`, `ip`（= request.remote_addr）。app.py:132。  
- **req_end**: `rid`, `method`, `path`, `status`, `ms`（duration_ms）。app.py:146〜148。  
- **5秒超のとき**: `SLOW_REQUEST rid=... path=... ms=...`。app.py:152。  
- **X-Request-ID**: g.request_id は before_request で付与（app.py:116）。after_request でレスポンスヘッダに `X-Request-ID` を付与（app.py:139）。**ログには rid として出力されている**（req_start/req_end の rid=...）。  
- **error 時**: 404/500/503/Exception で error_id, request_id(rid), path, method, user_agent, remote_addr 等がログに含まれる（app.py:197〜199, 213〜230, 242〜253, 276〜293）。

**足りない項目（事実）**  
- **User-Agent**: 通常の req_start/req_end には **出ていない**。  
- **Referer**: **どこにも出していない**。  
- **実クライアント IP（プロキシ越し）**: 通常ログは remote_addr のみで、X-Forwarded-For は crawl API 専用。  
- **リクエストボディサイズ / レスポンスサイズ**: 出していない。  
- **セッション/ジョブ単位の集約**: ログのみでは同一セッションの複数リクエストを束ねる設計はない（rid はリクエスト単位）。

**Render でのログ**: 標準出力に出す logger は Render のログに流れる想定。**どの logger に出すか**は現状 `logging.getLogger(__name__)` の INFO で統一されている（提案: 本番では同じ logger で構造化キーを増やす案は次ターン実装で検討。本分析では実装しない）。

---

## D. AdSense UI リスク箇所（事実）

**広告スクリプトの配置**  
- templates/includes/head_meta.html:61〜63。**AdSense 用 script（adsbygoogle.js）が全ページ共通で無条件に読み込まれている**。`{% if ADSENSE_ENABLED %}` のような分岐は **ない**（app.py の context_processor で ADSENSE_ENABLED は渡しているが、head_meta では未使用）。  
- **事実**: 広告スクリプトは GA_MEASUREMENT_ID と独立に、全テンプレで include される head_meta 経由で配信される。  
- **インコンテンツ広告ユニット（<ins class="adsbygoogle">）**: templates 内に **存在しない**（grep で 0 件）。オート広告のみの可能性が高い。

**「クリック誘導に見えるUI」の確認**  
- **/tools/***: 各ツールページに「実行」「ダウンロード」ボタンが存在。  
  - templates/tools/csv.html:91 「実行」ボタン（id="run-btn"）。同 58 行「クリックまたはドロップでファイルを選択」。  
  - templates/tools/seo.html: 多数の action-button（画像を生成、ダウンロード、検査する、等）。同 352 行 `<option value="adsense">AdSense承認</option>` は **OGP プリセットのラベル**であり、広告そのものではないが、「AdSense」文言がツール内に存在（誤認リスクは低いが記載）。  
- **landing.html**: 61〜71 行 `.cta-button` の CTA。  
- **autofill.html**: 800〜803 行「今月のテンプレートをダウンロード」「先月のテンプレートをダウンロード」ボタン。  
- **広告との近接**: 広告ユニットがテンプレに明示されていないため、**オート広告の挿入位置は Google 側**。「ダウンロード」「実行」等のボタンがオート広告の直近にレンダされ得るページは **/tools/*, /autofill, /** いずれも該当し得る。  
- **明確に怪しい配置**: コード上で「広告の直上/直下に CTA を意図的に配置」している箇所は **ない**。ただし **オート広告任せのため、実際の表示位置は本番で確認が必要**（推測: ツールページ・LP ではボタンと広告が近づく可能性はある）。

**「広告っぽく見える自作ボタン」等の grep 結果（事実）**  
- **ad / sponsor / おすすめ / クリック**:  
  - templates/contact.html:190 「クリック」→ 説明文「ボタンをクリックし」（誘導ではなく説明）。  
  - templates/tools/csv.html:58 「クリックまたはドロップでファイルを選択」（説明）。  
  - templates/tools/seo.html:352 「AdSense承認」→ プリセット名（広告ではない）。  
- **「スポンサー」「おすすめ」** の文言は templates 内に **なし**。  
- **結論**: 広告と誤認しうる文言の意図的使用はなし。「AdSense承認」は機能ラベルであり、コメントまたはラベル表記の整理で誤認をさらに下げる余地はある（次ターン候補）。

---

## E. 緊急遮断の現状（事実）

**広告停止**  
- **app.py**: context_processor で `ADSENSE_ENABLED` を渡している（app.py:335 成功時、357 例外時は False）。  
- **templates/includes/head_meta.html**: **adsbygoogle.js の読み込みは ADSENSE_ENABLED で分岐していない**（61〜63 行は無条件）。  
- **事実**: 環境変数で ADSENSE_ENABLED=false にしても、**現状では広告スクリプトは止まらない**。テンプレ側で `{% if ADSENSE_ENABLED %}` で script を囲めば止められるが、本分析では実装しない。

**機能停止・特定パス遮断**  
- **メンテナンスモード / 特定パス遮断**: **存在しない**（before_request でメンテナンス用 503 を返す処理なし、feature flag なし）。  
- **upload の実質的制限**: MAX_ACTIVE_SESSIONS / MAX_QUEUE_SIZE 超過時は 503 QUEUE_FULL（app.py:1692〜1696）。メモリガードでも 503（1644〜1650）。**「広告だけ止める」以外の緊急遮断（全機能 503 や /upload のみ 503）は env やフラグでは行えず、コード変更またはデプロイ停止に依存**。

**結論（事実）**  
- **緊急で「広告だけ止める」**: 現状 **できない**（ADSENSE_ENABLED はテンプレで未使用のため）。  
- **緊急で「全機能または特定パスを 503」**: **仕組みはない**。  
- **次ターンで最小差分で入れられる候補（実装はしない）**:  
  - head_meta.html で `{% if ADSENSE_ENABLED %}` で adsbygoogle スクリプトを囲む。  
  - 環境変数 MAINTENANCE_MODE=true 等で before_request の早い段階で 503 を返す。  
  - 特定パス（例 /upload）のみ 503 にする env（例 UPLOAD_DISABLED）を before_request で判定する。

---

## F. 次ターン実装バックログ TSV

**ファイル**: docs/invalid_traffic_backlog.tsv に同一内容を格納。

| 優先度 | 項目 | 現状 | 追加方針（最小差分案） | 変更箇所候補(file:line) | 受け入れ基準 |
|--------|------|------|------------------------|--------------------------|--------------|
| P1 | 広告の緊急停止 | ADSENSE_ENABLED は渡しているが script は無条件 | head_meta で adsbygoogle を ADSENSE_ENABLED で囲む | templates/includes/head_meta.html:61〜63 を {% if ADSENSE_ENABLED %} で囲む | 本番で ADSENSE_ENABLED=false にすると広告スクリプトが読み込まれない |
| P1 | アクセスログに UA/Referer | なし | req_start または after_request のログに UA と Referer を追加（長い場合は省略） | app.py:132 または 146〜148 | 1 リクエストあたり UA と Referer がログに残る |
| P1 | レート制限（/upload, /status） | なし | Flask-Limiter または slowapi で /upload, /status/* を IP あたり N 回/分に制限 | app.py（before_request 付近）、requirements.txt | 連打で 429 が返り、他ユーザーに影響が伝播しにくい |
| P1 | プロキシ越しの実 IP 統一 | 通常ログは remote_addr のみ。crawl のみ XFF 使用 | ProxyFix 導入または before_request で request の remote_addr を XFF 左端で上書きし、ログもその値を使う | app.py 起動直後または before_request、app.py:132 | Render 本番でログに実クライアント IP が残る |
| P2 | レート制限（/, /tools/*） | なし | 同一 IP の GET を N req/min に制限（ヘルスは除外） | app.py, requirements.txt | ボット連打で 429、正常ユーザーは影響小 |
| P2 | 緊急メンテナンスモード | なし | MAINTENANCE_MODE=true で全レスポンス 503 | app.py before_request の早い段階 | env で true にすると全パス 503 |
| P2 | /upload 単体遮断 | なし | UPLOAD_DISABLED=true で /upload のみ 503 | app.py /upload 直前または before_request | 事故時に upload だけ止められる |
| P2 | AdSense 誤認リスク | seo に「AdSense承認」ラベル | プリセット名を「AdSense承認用」等に変更またはコメントで意図明記 | templates/tools/seo.html:352 | 文言が広告と誤認されにくい |

---

## 補足（推測）

- **Render の X-Forwarded-For**: Render は通常、プロキシで X-Forwarded-For を付与する。ProxyFix 未使用のため、**現状アプリはその値を通常ログに使っていない**（推測）。  
- **オート広告の実際の表示位置**: コードでは制御していないため、**本番でツールページ・LP を開き、広告と CTA の距離を目視確認する必要がある**（推測）。

---

**以上、無効トラフィック対策監査の事実ベース棚卸しとする。コード変更は行っていない。**
