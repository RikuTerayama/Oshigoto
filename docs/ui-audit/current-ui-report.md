# UI監査レポート - RT Tools

> **目的**: このレポートは、GeminiにUI改善案を出させるための現状把握資料です。
> すべてのページの構造・コンポーネント・スタイル・アニメーション・アクセシビリティ・パフォーマンスを分解して記述しています。

## 0. 目的と前提

### 目的
GeminiにUI改善案を出させるための現状把握レポートです。このレポートをGeminiに貼り付けることで、具体的な改善提案と実装手順を得ることができます。

### 技術スタック
- **フレームワーク**: Flask (Python)
- **テンプレートエンジン**: Jinja2
- **ルーティング方式**: Flaskの@app.route()デコレータ
- **スタイリング**: インラインスタイル + <style>タグ（Tailwind CSS未使用）
- **JavaScript**: バニラJS（static/js/配下）
- **UIライブラリ**: なし（カスタム実装）
- **アニメーション**: CSS transition/transform（Framer Motion等は未使用）

### 主要ライブラリ
- **クライアント側**: pdf-lib, pdfjs-dist, jszip, @imgly/background-removal
- **サーバー側**: Flask, Playwright (Jobcan AutoFill用)

---

## 1. サイトマップ（ページ一覧）

### 全ルート一覧

| URLパス | 実体ファイル | 重要度 | 役割 |
|---------|------------|--------|------|
| / | `landing.html` | 🔴 High | ランディングページ（製品ハブ） |
| /autofill | `autofill.html` | 🔴 High | Jobcan自動入力ツール（旧ホームページ） |
| /privacy | `privacy.html` | 🔴 High | プライバシーポリシーページ |
| /terms | `terms.html` | 🔴 High | 利用規約ページ |
| /guide/getting-started | `guide_getting_started.html` | 🔴 High | はじめての使い方ガイド |
| /guide/excel-format | `guide_excel_format.html` | 🔴 High | Excelファイルの作成方法ガイド |
| /guide/troubleshooting | `guide_troubleshooting.html` | 🔴 High | トラブルシューティングガイド |
| /guide/complete | `guide/complete-guide.html` | 🔴 High | 完全ガイド |
| /guide/comprehensive-guide | `guide/comprehensive-guide.html` | 🔴 High | Jobcan勤怠管理を効率化する総合ガイド |
| /tools/image-batch | `tools/image-batch.html` | 🔴 High | 画像一括変換ツール（準備中） |
| /tools/pdf | `tools/pdf.html` | 🔴 High | PDFユーティリティ（準備中） |
| /tools/image-cleanup | `tools/image-cleanup.html` | 🔴 High | 画像ユーティリティ（準備中） |
| /tools/minutes | `tools/minutes.html` | 🔴 High | 議事録整形ツール（準備中） |
| /tools/seo | `tools/seo.html` | 🔴 High | Web/SEOユーティリティ（準備中） |
| /tools | `tools/index.html` | 🔴 High | ツール一覧ページ |
| /contact | `contact.html` | 🟡 Medium | お問い合わせページ |
| /faq | `faq.html` | 🟡 Medium | よくある質問（FAQ） |
| /glossary | `glossary.html` | 🟡 Medium | 用語集 |
| /about | `about.html` | 🟡 Medium | サイトについて |
| /best-practices | `best-practices.html` | 🟡 Medium | ベストプラクティス |
| /sitemap.html | `sitemap.html` | 🟡 Medium | HTMLサイトマップ |
| /case-study/contact-center | `case-study-contact-center.html` | 🟢 Low | 導入事例：コンタクトセンター |
| /blog | `blog/index.html` | 🟢 Low | ブログ一覧 |
| /blog/implementation-checklist | `blog/implementation-checklist.html` | 🟢 Low | ブログ記事：導入チェックリスト |
| /blog/automation-roadmap | `blog/automation-roadmap.html` | 🟢 Low | ブログ記事：90日ロードマップ |
| /blog/workstyle-reform-automation | `blog/workstyle-reform-automation.html` | 🟢 Low | ブログ記事：働き方改革と自動化 |
| /blog/excel-attendance-limits | `blog/excel-attendance-limits.html` | 🟢 Low | ブログ記事：Excel管理の限界と自動化ツール |
| /blog/playwright-security | `blog/playwright-security.html` | 🟢 Low | ブログ記事：Playwrightによるブラウザ自動化のセキュリティ |
| /blog/month-end-closing-hell-and-automation | `blog/month-end-closing-hell-and-automation.html` | 🟢 Low | ブログ記事：月末締めが地獄になる理由と自動化 |
| /blog/excel-format-mistakes-and-design | `blog/excel-format-mistakes-and-design.html` | 🟢 Low | ブログ記事：Excelフォーマットのミス10選 |
| /blog/convince-it-and-hr-for-automation | `blog/convince-it-and-hr-for-automation.html` | 🟢 Low | ブログ記事：情シス・人事を説得する5ステップ |
| /blog/playwright-jobcan-challenges-and-solutions | `blog/playwright-jobcan-challenges-and-solutions.html` | 🟢 Low | ブログ記事：Playwrightでハマったポイント |
| /blog/jobcan-auto-input-tools-overview | `blog/jobcan-auto-input-tools-overview.html` | 🟢 Low | ブログ記事：Jobcan自動入力ツールの全体像と選び方 |
| /blog/reduce-manual-work-checklist | `blog/reduce-manual-work-checklist.html` | 🟢 Low | ブログ記事：勤怠管理の手入力を減らすための実務チェックリスト |
| /blog/jobcan-month-end-tips | `blog/jobcan-month-end-tips.html` | 🟢 Low | ブログ記事：Jobcan月末締めをラクにするための7つの実践テクニック |
| /blog/jobcan-auto-input-dos-and-donts | `blog/jobcan-auto-input-dos-and-donts.html` | 🟢 Low | ブログ記事：Jobcan自動入力のやり方と、やってはいけないNG自動化 |
| /blog/month-end-closing-checklist | `blog/month-end-closing-checklist.html` | 🟢 Low | ブログ記事：月末の勤怠締め地獄を減らすための現実的なチェックリスト |
| /case-study/consulting-firm | `case-study-consulting-firm.html` | 🟢 Low | 導入事例：コンサルティングファーム |
| /case-study/remote-startup | `case-study-remote-startup.html` | 🟢 Low | 導入事例：小規模スタートアップ |

### 重要度別分類

**High (🔴)**: LP、AutoFill、Tools、Guide、Legalページ
**Medium (🟡)**: FAQ、About、Contact、Best Practices
**Low (🟢)**: Blog記事、Case Study

---

## 2. 共通UI/デザインシステムの現状

### Layout構造

- **Header**: `templates/includes/header.html`
  - 固定ナビゲーション（sticky, top: 0）
  - ロゴ + ナビゲーションリンク（Home, AutoFill, Tools, Guide）
  - アクティブ状態のハイライト（#4A9EFF）
  - モバイル対応（@media max-width: 768px）

- **Footer**: `templates/includes/footer.html`
  - 3カラムグリッド（ガイド、リソース、法的情報）
  - データ保持方針の表示
  - バージョン表示
  - レスポンシブグリッド（auto-fit, minmax(200px, 1fr)）

- **Container**: 各ページで共通の `.container` クラス
  - max-width: 1200px
  - margin: 0 auto
  - padding: 40px 20px

### Typography/Color/Spacing

**Typography**:
- フォント: 'Noto Sans JP', 'Helvetica Neue', 'Segoe UI', sans-serif
- letter-spacing: 0.05em（統一）
- line-height: 1.6（統一）

**Color Palette** (使用頻度の高い色):
- `#121212`
- `#1A1A1A`
- `#0F0F0F`
- `#FFFFFF`
- `#1E1E1E`
- `#2A2A2A`
- `rgba(0, 0, 0, 0.5)`
- `rgba(255, 255, 255, 0.2)`
- `#4A9EFF`
- `rgba(255, 255, 255, 0.9)`

主な色:
- 背景: linear-gradient(135deg, #121212 0%, #1A1A1A 50%, #0F0F0F 100%)
- テキスト: #FFFFFF, rgba(255, 255, 255, 0.8-0.9)
- アクセント: #4A9EFF（プライマリカラー）
- 成功: #4CAF50
- 警告: #FF9800
- エラー: #F44336

**Spacing**:
- コンテナパディング: 40px 20px
- セクション間隔: 30-60px
- 要素間隔: 10-20px（gap, margin）

### コンポーネント設計方針

**共通コンポーネント** (`templates/includes/`):

- **author_bio.html**: author_bio
  - インラインスタイル: 7箇所
  - <style>タグ: なし
  - Jinja2使用: なし

- **download_panel.html**: download_panel
  - インラインスタイル: 8箇所
  - <style>タグ: なし
  - Jinja2使用: あり

- **file_dropzone.html**: file_dropzone
  - インラインスタイル: 6箇所
  - <style>タグ: なし
  - Jinja2使用: あり

- **footer.html**: footer
  - インラインスタイル: 24箇所
  - <style>タグ: なし
  - Jinja2使用: あり

- **header.html**: header
  - インラインスタイル: 6箇所
  - <style>タグ: あり
  - Jinja2使用: あり

- **head_meta.html**: head_meta
  - インラインスタイル: 0箇所
  - <style>タグ: なし
  - Jinja2使用: あり

- **option_panel.html**: option_panel
  - インラインスタイル: 7箇所
  - <style>タグ: なし
  - Jinja2使用: あり

- **page_header.html**: page_header
  - インラインスタイル: 5箇所
  - <style>タグ: なし
  - Jinja2使用: あり

- **product_card.html**: product_card
  - インラインスタイル: 6箇所
  - <style>タグ: なし
  - Jinja2使用: あり

- **progress_panel.html**: progress_panel
  - インラインスタイル: 10箇所
  - <style>タグ: あり
  - Jinja2使用: あり

- **structured_data.html**: structured_data
  - インラインスタイル: 0箇所
  - <style>タグ: なし
  - Jinja2使用: あり

- **tool_shell.html**: tool_shell
  - インラインスタイル: 9箇所
  - <style>タグ: なし
  - Jinja2使用: あり

**共通部品**:
- Button: `.action-button`, `.cta-button`（インラインスタイル）
- Card: `.product-card`, `.panel`, `.tool-section`（インラインスタイル）
- Form: インラインスタイル（統一されたクラスなし）
- Modal: なし（確認ダイアログはalert/confirm）
- Toast: `MinutesExport.showToast()`（JavaScript実装）
- Progress: `.progress-panel`（カスタム実装）

**よく使われるクラス** (上位10):
- `.option-group`: 60回
- `.faq-item`: 44回
- `.faq-question`: 44回
- `.faq-answer`: 44回
- `.category`: 38回
- `.action-button`: 29回
- `.container`: 23回
- `.term-item`: 22回
- `.term-name`: 22回
- `.term-reading`: 22回

---

## 3. ページ別UI監査

### /

- **Path**: `/`
- **File**: `templates\landing.html`
- **目的**: Jobcan自動入力、画像一括変換、PDFユーティリティ、議事録整形など、業務効率化に役立つツールを提供しています。
- **主要コンポーネント**:
  - `includes/head_meta.html`
  - `includes/header.html`
  - `includes/footer.html`
- **UI構造**: Hero → Container → Grid → Form → Button
- **スタイル**:
  - インラインスタイル: 0箇所
  - <style>タグ: あり
  - 主要クラス: container, hero, cta-button, section, products-grid
- **アニメーション**: CSS transition, CSS transform, Hover effects
- **改善余地**:
  - アクセシビリティ: aria-label不足
  - UX: ローディング状態の表示不足
  - UX: エラー状態の表示不足
- **変更リスク**: High - 主要機能ページのため慎重に

### /autofill

- **Path**: `/autofill`
- **File**: `templates\autofill.html`
- **目的**: Jobcanへの勤怠データをExcelから一括入力する自動化ツール。手作業の繰り返しを削減し、月次締め作業を大幅に効率化します。
- **主要コンポーネント**:
  - `includes/head_meta.html`
  - `includes/header.html`
  - `includes/footer.html`
- **UI構造**: Container → Grid → Form → Button
- **スタイル**:
  - インラインスタイル: 89箇所
  - <style>タグ: あり
  - 主要クラス: container, header, content, sr-only, form-group
- **アニメーション**: CSS transition, CSS transform, CSS animation, Hover effects
- **改善余地**:
  - インラインスタイルが多数（CSS分離推奨）
  - イベントハンドラ: インラインイベント（分離推奨）
  - UX: alert/confirmの使用（モーダル推奨）
- **変更リスク**: High - 主要機能ページのため慎重に

### /privacy

- **Path**: `/privacy`
- **File**: `templates\privacy.html`
- **目的**: プライバシーポリシーページ
- **主要コンポーネント**:
  - `includes/head_meta.html`
- **UI構造**: Container → Form
- **スタイル**:
  - インラインスタイル: 0箇所
  - <style>タグ: あり
  - 主要クラス: container, update-date, back-link
- **アニメーション**: CSS transition, CSS transform, Hover effects
- **改善余地**:
  - UX: エラー状態の表示不足
- **変更リスク**: Low - 低リスク

### /terms

- **Path**: `/terms`
- **File**: `templates\terms.html`
- **目的**: 利用規約ページ
- **主要コンポーネント**:
  - `includes/head_meta.html`
- **UI構造**: Container → Form
- **スタイル**:
  - インラインスタイル: 0箇所
  - <style>タグ: あり
  - 主要クラス: container, update-date, warning, back-link
- **アニメーション**: CSS transition, CSS transform, Hover effects
- **改善余地**:
  - UX: エラー状態の表示不足
- **変更リスク**: Low - 低リスク

### /guide/getting-started

- **Path**: `/guide/getting-started`
- **File**: `templates\guide_getting_started.html`
- **目的**: はじめての使い方ガイド
- **主要コンポーネント**:
  - `includes/head_meta.html`
- **UI構造**: Container → Form
- **スタイル**:
  - インラインスタイル: 3箇所
  - <style>タグ: あり
  - 主要クラス: container, info-box, step-box, tip-box, warning-box
- **アニメーション**: CSS transition, CSS transform, Hover effects
- **改善余地**:
  - UX: エラー状態の表示不足
- **変更リスク**: Low - 低リスク

### /guide/excel-format

- **Path**: `/guide/excel-format`
- **File**: `templates\guide_excel_format.html`
- **目的**: Excelファイルの作成方法ガイド
- **主要コンポーネント**:
  - `includes/head_meta.html`
- **UI構造**: Container → Form
- **スタイル**:
  - インラインスタイル: 91箇所
  - <style>タグ: あり
  - 主要クラス: container, example-table, info-box, good, warning-box
- **アニメーション**: CSS transition, CSS transform, Hover effects
- **改善余地**:
  - インラインスタイルが多数（CSS分離推奨）
  - UX: エラー状態の表示不足
- **変更リスク**: Low - 低リスク

### /guide/troubleshooting

- **Path**: `/guide/troubleshooting`
- **File**: `templates\guide_troubleshooting.html`
- **目的**: トラブルシューティングガイド
- **主要コンポーネント**:
  - `includes/head_meta.html`
- **UI構造**: Container → Form
- **スタイル**:
  - インラインスタイル: 12箇所
  - <style>タグ: あり
  - 主要クラス: container, error-box, solution-box, warning-box, tip-box
- **アニメーション**: CSS transition, CSS transform, Hover effects
- **改善余地**:
  - （特になし）
- **変更リスク**: Low - 低リスク

### /guide/complete

- **Path**: `/guide/complete`
- **File**: `templates\guide\complete-guide.html`
- **目的**: 完全ガイド
- **主要コンポーネント**:
  - `includes/head_meta.html`
- **UI構造**: Hero → Container → Grid → Form
- **スタイル**:
  - インラインスタイル: 7箇所
  - <style>タグ: あり
  - 主要クラス: container, hero-section, stats, stat-card, stat-number
- **アニメーション**: CSS transition, CSS transform, Hover effects
- **改善余地**:
  - アクセシビリティ: aria-label不足
  - UX: エラー状態の表示不足
- **変更リスク**: Low - 低リスク

### /guide/comprehensive-guide

- **Path**: `/guide/comprehensive-guide`
- **File**: `templates\guide\comprehensive-guide.html`
- **目的**: Jobcan勤怠管理を効率化する総合ガイド
- **主要コンポーネント**:
  - `includes/head_meta.html`
- **UI構造**: Container → Grid → Form
- **スタイル**:
  - インラインスタイル: 123箇所
  - <style>タグ: あり
  - 主要クラス: container, breadcrumb
- **アニメーション**: CSS transition, Hover effects
- **改善余地**:
  - インラインスタイルが多数（CSS分離推奨）
  - UX: エラー状態の表示不足
- **変更リスク**: Low - 低リスク

### /tools/image-batch

- **Path**: `/tools/image-batch`
- **File**: `templates\tools\image-batch.html`
- **目的**: png/jpg/webpの一括変換、複数サイズ同時出力、リサイズ、品質圧縮に対応。ブラウザ内で完結し、ファイルは保存されません。
- **主要コンポーネント**:
  - `includes/head_meta.html`
  - `includes/header.html`
  - `includes/footer.html`
- **UI構造**: Container → Panel → Form → Button → Output → FileInput → Options
- **スタイル**:
  - インラインスタイル: 17箇所
  - <style>タグ: あり
  - 主要クラス: container, page-header, tool-section, file-dropzone, file-list
- **アニメーション**: CSS transition, Hover effects
- **改善余地**:
  - アクセシビリティ: aria-label不足
  - イベントハンドラ: インラインイベント（分離推奨）
  - UX: alert/confirmの使用（モーダル推奨）
  - UX: ローディング状態の表示不足
- **変更リスク**: Low - 低リスク

### /tools/pdf

- **Path**: `/tools/pdf`
- **File**: `templates\tools\pdf.html`
- **目的**: PDFの結合・分割・抽出・PDF→画像・圧縮・画像→PDF・埋め込み画像抽出をブラウザ内で実行。ファイルはアップロードしません。
- **主要コンポーネント**:
  - `includes/head_meta.html`
  - `includes/header.html`
  - `includes/footer.html`
- **UI構造**: Container → Panel → Form → Button → Output → FileInput → Options
- **スタイル**:
  - インラインスタイル: 33箇所
  - <style>タグ: あり
  - 主要クラス: container, page-header, tool-section, file-dropzone, file-list
- **アニメーション**: CSS transition, Hover effects
- **改善余地**:
  - インラインスタイルが多数（CSS分離推奨）
  - アクセシビリティ: aria-label不足
  - イベントハンドラ: インラインイベント（分離推奨）
  - UX: alert/confirmの使用（モーダル推奨）
  - UX: ローディング状態の表示不足
- **変更リスク**: Low - 低リスク

### /tools/image-cleanup

- **Path**: `/tools/image-cleanup`
- **File**: `templates\tools\image-cleanup.html`
- **目的**: 透過→白背景、余白トリミング、縦横比統一、背景除去をブラウザ内で一括処理。ファイルはアップロードしません。
- **主要コンポーネント**:
  - `includes/head_meta.html`
  - `includes/header.html`
  - `includes/footer.html`
- **UI構造**: Container → Panel → Form → Button → Output → FileInput → Options
- **スタイル**:
  - インラインスタイル: 21箇所
  - <style>タグ: あり
  - 主要クラス: container, page-header, tool-section, file-dropzone, file-list
- **アニメーション**: CSS transition, Hover effects
- **改善余地**:
  - インラインスタイルが多数（CSS分離推奨）
  - アクセシビリティ: aria-label不足
  - イベントハンドラ: インラインイベント（分離推奨）
  - UX: alert/confirmの使用（モーダル推奨）
  - UX: ローディング状態の表示不足
- **変更リスク**: Low - 低リスク

### /tools/minutes

- **Path**: `/tools/minutes`
- **File**: `templates\tools\minutes.html`
- **目的**: 議事録ログを成果物テンプレへ整形。決定事項とToDo抽出、期限の正規化、CSVとJSON出力に対応。アップロード不要。
- **主要コンポーネント**:
  - `includes/head_meta.html`
  - `includes/header.html`
  - `includes/footer.html`
- **UI構造**: Container → Panel → Grid → Form → Button → Output → Options
- **スタイル**:
  - インラインスタイル: 20箇所
  - <style>タグ: あり
  - 主要クラス: container, page-header, main-layout, panel, option-group
- **アニメーション**: CSS transition, Hover effects
- **改善余地**:
  - アクセシビリティ: aria-label不足
  - イベントハンドラ: インラインイベント（分離推奨）
  - UX: alert/confirmの使用（モーダル推奨）
  - UX: ローディング状態の表示不足
- **変更リスク**: Low - 低リスク

### /tools/seo

- **Path**: `/tools/seo`
- **File**: `templates\tools\seo.html`
- **目的**: OGP画像生成、PageSpeed改善チェックリスト、メタタグ検査、sitemap.xml/robots.txt生成をブラウザ内で実行。アップロード不要。
- **主要コンポーネント**:
  - `includes/head_meta.html`
  - `includes/header.html`
  - `includes/footer.html`
- **UI構造**: Container → Panel → Grid → Form → Button → Output → Options
- **スタイル**:
  - インラインスタイル: 28箇所
  - <style>タグ: あり
  - 主要クラス: container, page-header, main-layout, panel, mode-selector
- **アニメーション**: CSS transition, Hover effects
- **改善余地**:
  - インラインスタイルが多数（CSS分離推奨）
  - アクセシビリティ: aria-label不足
  - イベントハンドラ: インラインイベント（分離推奨）
  - UX: alert/confirmの使用（モーダル推奨）
  - UX: ローディング状態の表示不足
- **変更リスク**: Low - 低リスク

### /tools

- **Path**: `/tools`
- **File**: `templates\tools\index.html`
- **目的**: Jobcan自動入力、画像一括変換、PDFユーティリティ、議事録整形、Web/SEOユーティリティなど、業務効率化に役立つツールを提供しています。
- **主要コンポーネント**:
  - `includes/head_meta.html`
  - `includes/header.html`
  - `includes/footer.html`
- **UI構造**: Container → Grid → Form → Button
- **スタイル**:
  - インラインスタイル: 9箇所
  - <style>タグ: あり
  - 主要クラス: container, page-header, products-grid, product-card, icon
- **アニメーション**: CSS transition, CSS transform, Hover effects
- **改善余地**:
  - アクセシビリティ: aria-label不足
  - UX: ローディング状態の表示不足
  - UX: エラー状態の表示不足
- **変更リスク**: Low - 低リスク

### その他のページ（要約）

- **/contact**: `contact.html` - お問い合わせページ
- **/faq**: `faq.html` - よくある質問（FAQ）
- **/glossary**: `glossary.html` - 用語集
- **/about**: `about.html` - サイトについて
- **/best-practices**: `best-practices.html` - ベストプラクティス
- **/sitemap.html**: `sitemap.html` - HTMLサイトマップ
- **/case-study/contact-center**: `case-study-contact-center.html` - 導入事例：コンタクトセンター
- **/blog**: `blog/index.html` - ブログ一覧
- **/blog/implementation-checklist**: `blog/implementation-checklist.html` - ブログ記事：導入チェックリスト
- **/blog/automation-roadmap**: `blog/automation-roadmap.html` - ブログ記事：90日ロードマップ
- （他 14 ページ）

---

## 4. 横断課題まとめ（改善余地の共通パターン）

### ナビ/導線の一貫性
- ✅ ヘッダーとフッターは統一されている
- ⚠️ 各ページのCTA配置が統一されていない
- ⚠️ パンくずリストがない

### CTA配置、Hero、コピー
- ✅ LPにはHeroセクションがある
- ⚠️ ツールページのCTAが統一されていない
- ⚠️ エンプティステートのガイドが不足

### フォームUX（validation、helper text）
- ⚠️ バリデーションメッセージがalert()で表示（UX改善余地）
- ⚠️ ヘルパーテキストが不足している箇所がある
- ⚠️ エラー状態の視覚的フィードバックが弱い

### 結果表示（一覧、フィルタ、空状態）
- ✅ ツールページにはProgressPanelとDownloadPanelがある
- ⚠️ 空状態のガイドが不足
- ⚠️ エラー状態の表示が統一されていない

### Loading/Progress/Cancel
- ✅ ToolRunnerで進捗表示がある
- ⚠️ ローディングスケルトンがない
- ⚠️ Cancel後の状態表示が弱い

### モバイル対応（レスポンシブ）
- ✅ ヘッダーにモバイル対応あり
- ⚠️ 一部ページでモバイル最適化が不足
- ⚠️ タッチ操作の最適化が不足

### アクセシビリティ（label/aria/contrast）
- ⚠️ aria-labelが不足している箇所が多い
- ⚠️ フォーカス管理が不十分
- ⚠️ キーボード操作の最適化が不足
- ✅ コントラスト比は概ね良好（ダークテーマ）

### パフォーマンス（画像、LCP/CLS、bundle）
- ⚠️ 画像の遅延読み込みがない
- ⚠️ JavaScriptのバンドル最適化が未実施
- ⚠️ フォントの最適化が未実施

### アニメーション指針（控えめ・速い・一貫）
- ✅ transition: all 0.3s が統一されている
- ⚠️ アニメーションの一貫性が不足
- ⚠️ マイクロインタラクションが少ない

---

## 5. "モダンで洗練" のターゲット定義（Gemini向けに言語化）

### デザイン目標
- **Minimal & Calm**: 余計な装飾を排除し、機能に集中
- **Developer-friendly**: 技術者向けツールとして、情報密度を適切に保つ
- **Premium**: 高品質なUIで信頼感を醸成
- **Dark-first**: ダークテーマを基本とし、目に優しい

### 参考サイトのタイプ
- **Vercel**: ミニマルで洗練されたデザイン、適切な余白
- **Linear**: スムーズなアニメーション、一貫したデザインシステム
- **Stripe**: 明確な階層構造、優れたタイポグラフィ
- **GitHub**: 機能性重視、情報密度の適切な管理

### アニメーションの方向性
- **Micro-interactions**: ボタンホバー、フォーカス、クリックフィードバック
- **Page transition**: ページ遷移時のスムーズなトランジション（将来的に）
- **Loading skeleton**: ローディング中のスケルトンスクリーン
- **Progress feedback**: 処理中の明確な進捗表示
- **Error states**: エラー時の適切なアニメーション

### コンポーネント方針
- **shadcn/ui + Tailwind CSS**: 統一されたデザインシステムの導入を検討
- **Token化**: カラー、スペーシング、タイポグラフィをトークン化
- **Dark mode対応**: 現在のダークテーマを維持しつつ、システム設定対応も検討
- **再利用性**: 共通コンポーネントの徹底的な再利用

---

## 6. 実装方針案（Geminiが提案しやすい粒度）

### Phase 1: デザインシステム整備（tokens、共通コンポーネント）
**完了条件**:
- Tailwind CSSの導入と設定
- デザイントークン（カラー、スペーシング、タイポグラフィ）の定義
- 共通コンポーネント（Button, Card, Form, Modal等）の実装
- 既存ページへの段階的適用

### Phase 2: ナビ/LP改善
**完了条件**:
- ヘッダー/フッターのデザイン刷新
- LPのHeroセクション改善
- CTA配置の最適化
- モバイル対応の強化

### Phase 3: 各ツールUI刷新（入力→処理→結果）
**完了条件**:
- ツールページの統一レイアウト
- フォームUXの改善（バリデーション、ヘルパーテキスト）
- 結果表示の改善（空状態、エラー状態）
- 進捗表示の改善（スケルトン、アニメーション）

### Phase 4: アニメーション/アクセシビリティ/パフォーマンス仕上げ
**完了条件**:
- マイクロインタラクションの追加
- アクセシビリティの改善（aria-label, キーボード操作）
- パフォーマンス最適化（画像遅延読み込み、JSバンドル）
- 最終的なUI/UXテスト

---

## 7. Geminiに投げるプロンプト案（3種類）

### A) 全体方針を設計させるプロンプト

```
以下のUI監査レポートを基に、RT ToolsのUI改善の全体方針を設計してください。

【ここにレポートを貼る】

要件:
1. 現状の課題を整理し、優先順位をつける
2. デザインシステムの導入方針を提案する（shadcn/ui + Tailwind CSS推奨）
3. 4つのPhaseの詳細な実装計画を作成する
4. 各Phaseの完了条件と成果物を明確にする
5. リスクと対策を記載する

出力形式: Markdown
```

### B) ページ単位で改修案と実装手順を出させるプロンプト

```
以下のUI監査レポートを基に、特定ページの改修案と実装手順を提案してください。

【ここにレポートを貼る】

対象ページ: /tools/image-batch（画像一括変換ツール）

要件:
1. 現状のUI構造を分析する
2. 改善案を具体的に提示する（Before/After）
3. 実装手順をステップバイステップで記載する
4. 必要なコンポーネントとスタイルを具体的に記載する
5. 既存機能を壊さないための注意点を記載する

出力形式: Markdown + コード例
```

### C) shadcn + Tailwind + Framer Motion前提で、具体的コンポーネントコードを書かせるプロンプト

```
以下のUI監査レポートを基に、shadcn/ui + Tailwind CSS + Framer Motionを使用して、
RT Toolsの共通コンポーネントを実装してください。

【ここにレポートを貼る】

要件:
1. Button, Card, Form, Modal, Toast, Progress コンポーネントを実装
2. ダークテーマに対応
3. アクセシビリティを考慮（aria-label, キーボード操作）
4. マイクロインタラクションを追加（Framer Motion）
5. TypeScript + Reactで実装（Next.js想定だが、コンポーネント単体で動作するように）

出力形式: TypeScript/TSXコード + 使用例
```

---

## 8. 実装指向プロンプト（Flask/Jinja2環境向け）

以下のプロンプトは、Flask + Jinja2環境で直接実装を進めるための具体的な指示文です。
各プロンプトは独立して使用でき、段階的にUI改善を進めることができます。

### D) デザインシステム構築プロンプト

```
添付の「UI監査レポート」に基づき、RT ToolsのUIをVercelやLinearのような「Minimal & Premium Dark」なスタイルへ刷新するための土台を作ってください。

【基本方針】

1. Tailwind CSSの導入
   - CDNではなく、プロジェクトに導入可能な最小構成を提案し、tailwind.config.jsを作成してください
   - カラーパレットはレポートの値をベースに、深みのあるグレー（#0F0F0F, #1A1A1A）と鮮やかなアクセントブルー（#4A9EFF）を定義すること

2. タイポグラフィ
   - Noto Sans JPをベースに、letter-spacing: -0.02em（モダンな印象）と適切なline-heightをグローバルに適用してください

3. 共通コンポーネントの抽象化
   - インラインスタイルを排除し、Jinja2の各テンプレートで再利用可能な「Button」「Card」「Input」「Panel」のTailwindクラスの組み合わせ（またはJinjaマクロ）を定義してください

4. Glassmorphismの採用
   - ヘッダーやカードには、背景をわずかに透過させ、backdrop-filter: blur(10px) と 境界線（border: 1px solid rgba(255,255,255,0.1)）を組み合わせた高級感のあるデザインを適用してください

まず、static/css/main.css（新規作成）と tailwind.config.js の構成案を出してください。

【ここにレポートを貼る】
```

### E) 主要ページ（Landing/Autofill）の劇的刷新プロンプト

```
@landing.html と @autofill.html を修正し、監査レポートで指摘されている「UXの不足」と「デザインの不透明感」を解消してください。

【具体的指示】

1. Heroセクション
   - タイトル（H1）には bg-clip-text を使ったグラデーションを適用し、サブテキストとのコントラストを明確に

2. Bento Gridレイアウト
   - 各ツールへの導線を、一律のリストではなく、重要度に応じたサイズの異なる「Bento Grid」スタイルで再構築してください

3. Autofillフォームのモダン化
   - インラインスタイルを全てTailwindに置換
   - フォーム要素（Dropzone）は点線ではなく、微細なアニメーションを伴うソリッドな境界線に変更
   - alert() で表示されているバリデーションを、トースト通知（Lucideアイコン付き）をシミュレートしたHTML/CSS構造に変更する準備をしてください

4. インタラクション
   - 全ての button と card に、ホバー時の transform: translateY(-2px) と box-shadow（発光を感じさせるブルーの影）を追加してください

ロジック（Jinja2の変数やFlaskのルート）は一切壊さず、見た目とクラス構成のみを美しく書き換えてください。

【ここにレポートを貼る】
```

### F) マイクロインタラクションとUXの仕上げプロンプト

```
プロジェクト全体の「触り心地」を向上させるため、JavaScriptとCSSを用いたマイクロインタラクションを追加してください。

【実装内容】

1. Loading Skeleton
   - progress_panel.html に、処理待ち時間を退屈させないための、流れるようなシマーエフェクト（骨格スクリーン）を実装してください

2. 入力フィードバック
   - テキスト入力やファイル選択時、成功/失敗を枠線の色の変化（ring-2 ring-blue-500等）と、わずかな「バウンスアニメーション」で表現してください

3. Smooth Scroll & Transitions
   - ページ内遷移や要素の表示・非表示を transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1) で制御し、高級な操作感にしてください

4. アクセシビリティ
   - 監査レポートの指摘通り、全てのボタンと入力フォームに適切な aria-label を動的に（または静的に）付与し、フォーカス状態の視認性を高めてください

既存の static/js/ 配下のロジックと衝突しないよう、独立した ui-effects.js を作成して統合してください。

【ここにレポートを貼る】
```

---

## 9. プロンプト使用ガイド

### 推奨実装順序

1. **Phase 1: デザインシステム構築（プロンプトD）**
   - Tailwind CSSの導入と設定
   - 共通コンポーネントの抽象化
   - デザイントークンの定義
   - 完了後、既存ページへの段階的適用を開始

2. **Phase 2: 主要ページ刷新（プロンプトE）**
   - Landing PageとAutoFillページの刷新
   - インラインスタイルの完全排除
   - モダンなレイアウトへの移行
   - 完了後、他のツールページへの適用を検討

3. **Phase 3: UX仕上げ（プロンプトF）**
   - マイクロインタラクションの追加
   - アクセシビリティの改善
   - パフォーマンス最適化
   - 最終的なUI/UXテスト

### プロンプトの使い方

1. このレポート全文をコピー
2. 使用したいプロンプト（D/E/F）を選択
3. プロンプト内の「【ここにレポートを貼る】」部分に、レポート全文を貼り付け
4. Gemini（またはCursor）に送信
5. 生成されたコードをレビューし、段階的に適用

### 注意事項

- **既存機能の保護**: ロジック（Jinja2変数、Flaskルート、JavaScript処理）は一切変更しない
- **段階的適用**: 一度に全ページを変更せず、1ページずつ検証しながら進める
- **バックアップ**: 変更前に必ずGitコミットを作成
- **テスト**: 各Phase完了後に、主要機能が正常に動作することを確認

---

**レポート生成日時**: 2026/2/3 13:42:29
**生成ツール**: generate-ui-audit.ts
**最終更新**: 実装指向プロンプト追加（2026/2/3）