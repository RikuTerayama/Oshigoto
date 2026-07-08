# Google AdSense「有用性の低いコンテンツ」不承認 サイト品質監査レポート

**作成日**: 2026-02-24  
**対象サイト**: https://jobcan-automation.onrender.com/  
**目的**: 次回申請で承認される確率を最大化するため、現状の課題を特定し、最小差分で直すための課題リストを作成する

---

## エグゼクティブサマリー

### AdSense 不承認の主要因候補 Top5

| 順位 | 候補 | 確度 | 根拠 |
|------|------|------|------|
| 1 | プライバシーポリシーと実装の矛盾（広告配信・データ処理の記載） | **高** | 第8項「今後配信を行う予定」と記載されている一方、`ADSENSE_ENABLED=true` で AdSense スクリプトが読み込まれている。第4項「原則ローカル処理」と Jobcan AutoFill のサーバー処理が矛盾 |
| 2 | 問い合わせ導線のリンク切れ（GitHub Issues プレースホルダー） | **高** | プレースホルダー URL のままでは 404。実リポジトリは `RikuTerayama/jobcan_automation` |
| 3 | サイトテーマの散らかり（多ジャンルツール混在） | **中** | 勤怠管理・画像変換・PDF・SEO・CSV と性質の異なるツールが混在し、サイトの主目的が曖昧に見える可能性 |
| 4 | ツール型ページの初期表示価値の薄さ | **中** | ツールページは「使い方・制約・FAQ」を HTML に含めており改善済み。ただし一部ツールは入力UIが主で、クリックしないと価値が見えにくい設計 |
| 5 | プライバシーポリシーの AdSense 必須開示の不足・曖昧さ | **中** | Cookie・オプトアウト・第三者ベンダーへの言及はあるが、「配信予定」という未来形で現状と乖離。EEA/UK 向け CMP の言及なし（仮説） |

### 最小差分で効く改善パッケージ（P0 3点セット）

1. **プライバシーポリシー修正**: 第8項を「本サイトでは Google AdSense による広告配信を行っています」に変更し、第4項で Jobcan AutoFill のサーバー処理（一時アップロード→処理後削除）を明記
2. **GitHub リンク修正**: プレースホルダー URL を実リポジトリ URL（`RikuTerayama/jobcan_automation`）に置換
3. **aboutads.info を HTTPS に**: `http://www.aboutads.info/choices/` → `https://optout.aboutads.info/` に変更（推奨）

### 再申請前に最低限通すべきゲート

- [ ] プライバシーポリシーが実装（広告配信・データ処理）と矛盾していない
- [ ] 問い合わせページ内の全リンクが有効（404 なし）
- [ ] 主要ページ（/, /autofill, /tools, /privacy, /contact, /about）が Googlebot UA で本文取得可能
- [ ] プライバシーポリシーに AdSense 用 Cookie・オプトアウト・第三者ベンダーへの言及が現状に即して記載されている

---

## サイト棚卸し（クローラ視点）

### ルーティング一覧（app.py から抽出）

| パス | ページ種別 | テンプレート |
|------|-----------|--------------|
| `/` | LP | landing.html |
| `/autofill` | ツール（メイン） | autofill.html |
| `/tools` | ツール一覧 | tools/index.html |
| `/tools/image-batch` | ツール | tools/image-batch.html |
| `/tools/pdf` | ツール | tools/pdf.html |
| `/tools/image-cleanup` | ツール | tools/image-cleanup.html |
| `/tools/seo` | ツール | tools/seo.html |
| `/tools/csv` | ツール | tools/csv.html |
| `/guide` | ガイド一覧 | guide/index.html |
| `/guide/autofill` | ガイド | guide/autofill.html |
| `/guide/getting-started` | ガイド | guide/getting-started.html |
| `/guide/excel-format` | ガイド | guide/excel-format.html |
| `/guide/troubleshooting` | ガイド | guide/troubleshooting.html |
| `/guide/complete` | ガイド | guide/complete-guide.html |
| `/guide/comprehensive-guide` | ガイド | guide/comprehensive-guide.html |
| `/guide/image-batch` | ガイド | guide/image-batch.html |
| `/guide/pdf` | ガイド | guide/pdf.html |
| `/guide/image-cleanup` | ガイド | guide/image-cleanup.html |
| `/guide/seo` | ガイド | guide/seo.html |
| `/guide/csv` | ガイド | guide/csv.html |
| `/about` | 規約・運営者 | about.html |
| `/faq` | ガイド | faq.html |
| `/glossary` | ガイド | glossary.html |
| `/best-practices` | ガイド | best-practices.html |
| `/privacy` | 規約 | privacy.html |
| `/terms` | 規約 | terms.html |
| `/contact` | 規約・問い合わせ | contact.html |
| `/blog` | 記事一覧 | blog/index.html |
| `/blog/*` (14記事) | 記事 | blog/*.html |
| `/case-study/contact-center` | 事例 | case-study-contact-center.html |
| `/case-study/consulting-firm` | 事例 | case-study-consulting-firm.html |
| `/case-study/remote-startup` | 事例 | case-study-remote-startup.html |
| `/sitemap.html` | その他 | sitemap.html |

**リダイレクト**: `/guide/minutes` → 301 `/guide`, `/tools/minutes` → 301 `/tools`  
**noindex**: `/status/*`, `/api/*`, `/download-template`, `/download-previous-template`, `/sessions`, `/cleanup-sessions`

### 主要 URL の棚卸し（重要度順）

| URL | ページ種別 | 初期表示の本文量 | クリック前提の薄さ | 重複度 | インデックス制御 | 404/リンク切れ |
|-----|------------|------------------|-------------------|--------|------------------|----------------|
| `/` | LP | 十分（製品一覧・説明・導線） | 低 | 低 | 妥当 | なし |
| `/autofill` | ツール | 十分（使用方法・FAQ・注意・関連ツール） | 中（入力しないと価値なし） | 低 | 妥当 | なし |
| `/tools` | ツール一覧 | 十分（各ツールカード・説明） | 低 | 低 | 妥当 | なし |
| `/tools/image-batch` | ツール | 十分（使い方・FAQ・制約・関連ツール） | 中 | 低 | 妥当 | なし |
| `/tools/pdf` | ツール | 同型 | 中 | 中（ツール共通構造） | 妥当 | なし |
| `/tools/image-cleanup` | ツール | 同型 | 中 | 中 | 妥当 | なし |
| `/tools/seo` | ツール | 同型 | 中 | 中 | 妥当 | なし |
| `/tools/csv` | ツール | 同型 | 中 | 中 | 妥当 | なし |
| `/privacy` | 規約 | 十分 | 低 | 低 | 妥当 | なし |
| `/terms` | 規約 | 十分 | 低 | 低 | 妥当 | なし |
| `/contact` | 問い合わせ | 十分（FAQ・導線） | 低 | 低 | 妥当 | **GitHub リンク 404** |
| `/about` | 運営者 | 十分 | 低 | 低 | 妥当 | **GitHub リンク 404** |
| `/guide/*` | ガイド | 各ページで十分 | 低 | 中（構造は似るが内容は個別） | 妥当 | なし |
| `/blog/*` | 記事 | 各記事で十分 | 低 | 中（14記事、構造は似るが内容は個別） | 妥当 | なし |
| `/case-study/*` | 事例 | 十分（企業プロフィール・課題・効果） | 低 | 高（3件とも同型構造） | 妥当 | なし |

### ドメイン棚卸し

- **本番**: `https://jobcan-automation.onrender.com`（render.yaml, app.py, head_meta.html 等でハードコード）
- **他ドメイン**: リポジトリ内に別ドメインの管理なし

---

## 低品質判定につながる論点マップ

### A. コンテンツ価値（独自性・網羅性・専門性・再訪性）

| 観点 | 現状 | 評価 |
|------|------|------|
| 記事・ガイドの付加価値 | 具体例・手順・比較・FAQ を含む。ブログ14本、ガイド10本以上 | 良好 |
| ツールページの説明 | 使い方・制約・FAQ・想定用途を HTML に含む（image-batch 等で確認） | 良好 |
| 同型ページの量産 | ツール5種・ガイド10種・ブログ14本・事例3件。各ツールは product 変数で差別化。事例3件は構造が非常に類似 | 中リスク（事例） |
| テンプレ量産感 | ツールは tool_shell を拡張するが、各ページで独自ブロックを上書き。ブログ・ガイドは個別テンプレ | 低リスク |

### B. サイト一貫性（テーマの散らかり）

| 観点 | 現状 | 評価 |
|------|------|------|
| 1ドメイン内のプロダクト混在 | Jobcan 勤怠 + 画像変換 + PDF + SEO + CSV。主目的は「業務効率化ツール集」だが、勤怠特化と汎用ツールが混在 | 中リスク |
| ナビ・カテゴリ設計 | ヘッダー・フッターで一貫。ツール一覧・ガイド一覧で整理 | 良好 |

### C. 信頼性（運営者情報・透明性・誤解の回避）

| 観点 | 現状 | 評価 |
|------|------|------|
| 運営者情報 | about.html で OPERATOR_NAME, OPERATOR_EMAIL, OPERATOR_LOCATION を表示（環境変数未設定時は空） | 要確認 |
| 問い合わせ導線 | Google Form iframe + 別タブリンク。OPERATOR_EMAIL 未設定時はフォームが主導線 | 機能するが GitHub リンク 404 |
| 規約・免責 | privacy.html, terms.html あり | 良好 |
| 第三者サービス認証入力 | /autofill で Jobcan のメール・パスワード入力。「非公式」「会社の公式ツールではありません」と明記。セキュリティ説明あり | 良好 |
| 商標・名称 | 「Jobcan」は商標の可能性。非公式である旨は明記 | 良好 |
| プライバシーと実装の整合 | **矛盾あり**（後述） | 要修正 |

### D. 技術的に評価されない（クローラが中身を見られない）

| 観点 | 現状 | 評価 |
|------|------|------|
| SSR/SSG/CSR | Flask サーバーサイドレンダリング。全ページ初期 HTML にコンテンツ含む | 良好 |
| JavaScript 依存 | ツールは JS で動作するが、説明文・使い方・FAQ は HTML に含まれる | 良好 |
| Googlebot UA | 本監査で通常 UA で fetch した結果、主要テキストは取得できた。Googlebot 専用ブロックなし | 要検証（後述） |
| meta/title/canonical | head_meta.html で page_title, description, canonical, og:url を設定。各ページで block で上書き | 良好 |
| 構造化データ | Organization, WebSite, SoftwareApplication, BreadcrumbList 等 | 良好 |

### E. ポリシー必須ページの充足（AdSense 申請の見栄え）

| 観点 | 現状 | 評価 |
|------|------|------|
| プライバシー（広告・Cookie・第三者） | 第8項に AdSense 言及あり。ただし「今後配信を行う予定」と未来形。Cookie・オプトアウト・aboutads.info へのリンクあり | **要修正** |
| 問い合わせの実体 | Google Form が動作。OPERATOR_EMAIL は環境変数次第 | 良好 |
| 利用規約と実装の矛盾 | プライバシー第4項「原則ローカル処理」と Jobcan AutoFill のサーバー処理が矛盾 | **要修正** |

---

## 証拠付きの指摘リスト（課題チケット化）

### 課題 1: プライバシーポリシー第8項「広告配信予定」と実装の矛盾

- **重要度**: P0
- **該当 URL**: https://jobcan-automation.onrender.com/privacy
- **なぜ問題か**: AdSense 審査時に「広告を配信しているのに、ポリシーでは配信予定と記載」と不整合に見える。信頼性を損なう。
- **再現手順**: 1. /privacy を開く 2. 第8項を確認「今後 Google AdSense による広告配信を行う予定です」 3. head_meta.html で ADSENSE_ENABLED 時は AdSense スクリプトが読み込まれることを確認 4. render.yaml で ADSENSE_ENABLED=true を確認
- **原因箇所**: `templates/privacy.html` 132–135行目
- **最小差分の改善案**: 「本サイトでは、Google AdSense による広告配信を行っています。審査通過後、広告が表示されます。」のように現状に即した表現に変更。または、既に配信している場合は「本サイトでは Google AdSense による広告配信を行っています。」に統一。
- **改善後の確認方法**: /privacy の第8項が実装と一致していることを目視確認

---

### 課題 2: プライバシーポリシー第4項「原則ローカル処理」と Jobcan AutoFill のサーバー処理の矛盾

- **重要度**: P0
- **該当 URL**: https://jobcan-automation.onrender.com/privacy
- **なぜ問題か**: Jobcan AutoFill は /upload で Excel をサーバーに送信し、Playwright がサーバー上で実行される。プライバシーでは「原則ローカル処理」「各種ツールはブラウザ内で処理」とあるが、AutoFill はサーバー処理。誤解を招き、信頼性を損なう。
- **再現手順**: 1. /privacy 第4項を確認 2. app.py の /upload ルート（1683行付近）で request.files を受け取り process_jobcan_automation を呼ぶ処理を確認
- **原因箇所**: `templates/privacy.html` 103–109行目
- **最小差分の改善案**: 第4項で「Jobcan AutoFill は、勤怠データ入力のため、Excel ファイルをサーバーに一時的にアップロードします。処理完了後、ファイルは即座に削除され、サーバーに保存されません。ログイン情報は処理中のみメモリに保持されます。」のように、サーバー処理であることを明記しつつ、保存しない旨を明確化。
- **改善後の確認方法**: プライバシーを読み、実装と矛盾がないことを確認

---

### 課題 3: GitHub リンクのプレースホルダー（404）

- **重要度**: P0
- **該当 URL**: 
  - https://jobcan-automation.onrender.com/contact（GitHub Issues リンク）
  - https://jobcan-automation.onrender.com/about（GitHub リポジトリリンク）
- **なぜ問題か**: プレースホルダー URL は存在しない。問い合わせ・運営者情報の導線がリンク切れだと、信頼性・透明性が損なわれる。
- **再現手順**: 1. /contact を開く 2. 「GitHub Issues」リンクをクリック 3. 404 または存在しないリポジトリに遷移することを確認。同様に /about の GitHub リンクを確認
- **原因箇所**: 
  - `templates/contact.html` 160行目: GitHub Issues のプレースホルダー URL
  - `templates/contact.html` 221行目: README のプレースホルダー URL
  - `templates/about.html` 384行目, 411行目: GitHub リポジトリのプレースホルダー URL
- **最小差分の改善案**: プレースホルダー URL を実リポジトリ `RikuTerayama/jobcan_automation`（アンダースコア）に置換。Issues は `https://github.com/RikuTerayama/jobcan_automation/issues`、README は `https://github.com/RikuTerayama/jobcan_automation/blob/main/README.md`。
- **改善後の確認方法**: 各リンクをクリックし、有効な GitHub ページに遷移することを確認

---

### 課題 4: aboutads.info が HTTP

- **重要度**: P1
- **該当 URL**: https://jobcan-automation.onrender.com/privacy（第8項内リンク）
- **なぜ問題か**: `http://www.aboutads.info/choices/` は HTTPS 推奨。混在コンテンツやセキュリティ観点で不利になる可能性。
- **再現手順**: /privacy の第8項内リンクを確認
- **原因箇所**: `templates/privacy.html` 134行目
- **最小差分の改善案**: `https://optout.aboutads.info/` または `https://www.aboutads.info/choices/` に変更
- **改善後の確認方法**: リンクをクリックし、HTTPS で正しく遷移することを確認

---

### 課題 5: 事例ページの同型構造（3件）

- **重要度**: P2
- **該当 URL**: /case-study/contact-center, /case-study/consulting-firm, /case-study/remote-startup
- **なぜ問題か**: 3件とも「企業プロフィール→課題→導入プロセス→効果」の同一構造。内容は異なるが、テンプレ量産感を与える可能性がある。
- **再現手順**: 3つの事例ページを開き、見出し構造・セクション構成が類似していることを確認
- **原因箇所**: `templates/case-study-*.html` 各ファイル
- **最小差分の改善案**: 各事例に「失敗談」「工夫した点」「業種別の注意点」など、差別化できるセクションを追加。または現状のまま様子見（P2）。
- **改善後の確認方法**: 各事例の独自性が増していることを確認

---

### 課題 6: ツール一覧の「Local」バッジと Jobcan AutoFill の実態の矛盾

- **重要度**: P1
- **該当 URL**: https://jobcan-automation.onrender.com/tools
- **なぜ問題か**: `status == 'available'` の全ツールに「Local」バッジが表示される（templates/tools/index.html 248行目）。Jobcan AutoFill はサーバーにファイルをアップロードするため「Local」は誤解を招く。プライバシー・信頼性の観点で矛盾。
- **再現手順**: /tools を開き、Jobcan AutoFill のカードに「Local」と表示されることを確認
- **原因箇所**: `templates/tools/index.html` 248行目。`product.status == 'available'` で一律「Local」を表示
- **最小差分の改善案**: Jobcan AutoFill（product.id == 'autofill'）の場合は「Local」を表示しない、または「サーバー処理（一時保持・即削除）」等の正確な表現に変更。他ツールは「ブラウザ内処理」等に統一しても可。
- **改善後の確認方法**: /tools で Jobcan AutoFill に誤解を招く表記がなくなっていることを確認

---

## 検証手順（手元で即できるチェック）

### 1. Googlebot UA で主要ページの本文取得確認

```powershell
# PowerShell
$headers = @{
    "User-Agent" = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
}
$urls = @(
    "https://jobcan-automation.onrender.com/",
    "https://jobcan-automation.onrender.com/autofill",
    "https://jobcan-automation.onrender.com/tools",
    "https://jobcan-automation.onrender.com/privacy",
    "https://jobcan-automation.onrender.com/contact"
)
foreach ($url in $urls) {
    $response = Invoke-WebRequest -Uri $url -Headers $headers -UseBasicParsing
    $body = $response.Content
    $textLength = ($body -replace '<[^>]+>','').Length
    Write-Host "$url : テキスト長 $textLength 文字, Status $($response.StatusCode)"
}
```

**期待**: 各 URL で 200 が返り、テキスト長が数百文字以上あること。Googlebot 専用ブロックで空になっていないこと。

### 2. JavaScript 無効相当で本文が空にならないか

- ブラウザの開発者ツールで JavaScript を無効化
- /, /autofill, /tools/image-batch, /privacy を開く
- 説明文・見出し・リンクが表示されることを確認

**期待**: Flask は SSR のため、JS 無効でも主要コンテンツは表示される。

### 3. サイト内リンク切れチェック・ステータスコード一覧

```powershell
# 簡易版: 主要リンクの存在確認
$links = @(
    "https://jobcan-automation.onrender.com/",
    "https://jobcan-automation.onrender.com/privacy",
    "https://jobcan-automation.onrender.com/terms",
    "https://jobcan-automation.onrender.com/contact",
    "https://github.com/placeholder-repo/jobcan-automation/issues",
    "https://github.com/RikuTerayama/jobcan_automation"
)
foreach ($link in $links) {
    try {
        $r = Invoke-WebRequest -Uri $link -UseBasicParsing -TimeoutSec 10
        Write-Host "$link : $($r.StatusCode)"
    } catch {
        Write-Host "$link : ERROR $($_.Exception.Message)"
    }
}
```

**期待**: プレースホルダーのリンクは 404。RikuTerayama のリンクは 200。

### 4. 重要ページの title / description / canonical 棚卸し

```powershell
$urls = @("/", "/autofill", "/tools", "/privacy", "/contact", "/about")
foreach ($path in $urls) {
    $url = "https://jobcan-automation.onrender.com" + $path
    $r = Invoke-WebRequest -Uri $url -UseBasicParsing
    if ($r.Content -match '<title>([^<]+)</title>') { $title = $matches[1] } else { $title = "N/A" }
    if ($r.Content -match 'meta name="description" content="([^"]*)"') { $desc = $matches[1].Substring(0, [Math]::Min(60, $matches[1].Length)) } else { $desc = "N/A" }
    if ($r.Content -match 'link rel="canonical" href="([^"]+)"') { $can = $matches[1] } else { $can = "N/A" }
    Write-Host "--- $path ---"
    Write-Host "title: $title"
    Write-Host "description: $desc..."
    Write-Host "canonical: $can"
}
```

---

## P0 だけ潰したら再申請できる最短ルート（案）

1. **プライバシーポリシー修正**（課題 1, 2）
   - 第8項: 「今後配信を行う予定」→「本サイトでは Google AdSense による広告配信を行っています」（または現状に即した表現）
   - 第4項: Jobcan AutoFill のサーバー一時処理を明記し、「原則ローカル処理」との整合を取る

2. **GitHub リンク修正**（課題 3）
   - contact.html, about.html のプレースホルダー URL を実リポジトリに置換

3. **aboutads.info を HTTPS に**（課題 4、推奨）
   - privacy.html のリンクを HTTPS に変更

4. **再申請前の最終確認**
   - 上記検証手順 1〜4 を実行
   - プライバシー・問い合わせ・about を目視で確認
   - 必要に応じて OPERATOR_EMAIL を設定し、問い合わせ導線を強化

---

## 補足：初期仮説の検証結果

| 仮説 | 検証結果 | 確度 |
|------|----------|------|
| ツール型ページは初期 HTML が薄く低品質判定リスク | ツールページ（image-batch 等）は使い方・FAQ・制約を HTML に含む。薄くない | 低（リスクは軽減済み） |
| 多ジャンルツール混在で主目的が曖昧 | 勤怠・画像・PDF・SEO・CSV が混在。ナビは一貫しているが、テーマの広がりはある | 中 |
| 第三者認証入力 UI の誤解リスク | 非公式・セキュリティ説明あり。フィッシング誤認リスクは低い | 低 |
| プライバシーの AdSense 必須開示不足 | Cookie・オプトアウト・第三者言及はあるが、「配信予定」と実装が矛盾 | 高 |

---

*本レポートは分析のみ行い、コード改修・リファクタ・文言修正・設定変更は一切行っていません。*
