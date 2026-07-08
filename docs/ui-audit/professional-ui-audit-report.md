# UI監査レポート - プロフェッショナル化とスクロールリビール導入

> **目的**: 現状UIを客観的に棚卸しし、モダンで洗練された（プロフェッショナルな）方向に改善するための材料となる「UI監査レポート」を作成。スクロールリビール演出の導入方針と実装計画を含む。

**対象サイト**: https://jobcan-automation.onrender.com/  
**技術スタック**: Flask + Jinja2、インラインスタイル、バニラJS  
**作成日**: 2026-02-03

---

## 0. エグゼクティブサマリー

### 現状の総評
現状のUIは「機能性は高いが、視覚的なプロフェッショナリズムに欠ける」状態です。主な要因は、**絵文字アイコンの多用**、**過剰な装飾効果（グラデーション、影、角丸）**、**インラインスタイルによる一貫性の欠如**、**情報階層の視覚的弱さ**です。B2B向け業務効率化ツールとして、より「監査に耐える堅さ」と「信頼感」を醸し出す必要があります。

### 最重要の改善テーマTop3
1. **アイコン体系の刷新**: 絵文字（🏠🕒🛠️📚等）を線形アイコン（Lucide/Heroicons）に置換し、統一された視覚言語を確立
2. **タイポグラフィと余白の体系化**: 見出し階層の明確化、行間・字間の最適化、セクション間隔の統一
3. **カラーパレットの簡素化**: グラデーション背景を控えめにし、ニュートラルベース + アクセント1色（#4A9EFF）の構成に統一

### スクロールリビール導入の狙いと注意点
**狙い**: 長文コンテンツ（ガイド、FAQ、ブログ）での読み進め体験を向上させ、情報の階層を視覚的に補助する。  
**注意点**: 
- フォーム入力領域（autofill.htmlのアップロード/実行ボタン）には適用しない
- 控えめなモーション（opacity + translateY、duration 300-400ms）に統一
- `prefers-reduced-motion`対応必須（アクセシビリティ）

---

## 1. 現状UIの棚卸し（ページ別）

### 1.1 トップページ（/ - landing.html）

**ファーストビュー所感**:
- ヒーローセクション（h1: 3em、padding: 80px）は存在感があるが、CTAボタンの視覚的優先度が低い
- 製品カードグリッドは整然としているが、hover時の`translateY(-5px)`が過剰

**気になる点**:
- 絵文字アイコンがナビゲーションに使用されている（🏠🕒🛠️📚）
- グラデーション背景が多用されている（`linear-gradient(135deg, #121212 0%, #1A1A1A 50%, #0F0F0F 100%)`）
- 角丸が大きい（border-radius: 16px, 12px）
- ボタンのhover効果が派手（`transform: translateY(-2px)` + `box-shadow: 0 8px 25px`）

**良い点**:
- コンテナの最大幅（1200px）が適切
- グリッドレイアウト（`grid-template-columns: repeat(auto-fit, minmax(320px, 1fr))`）がレスポンシブ
- カラーパレット（ダークテーマ + #4A9EFF）は一貫している

**幼く見える要因**:
- **アイコン**: 絵文字（🏠🕒🛠️📚）がカジュアルすぎる（`templates/includes/header.html:10-13`）
- **配色**: グラデーション背景が多層的で「ゲーミング感」がある
- **余白**: セクション間隔（80px）は適切だが、要素間のgap（30px）が不規則
- **文字**: 見出しの`letter-spacing: 0.08em`が広すぎて「装飾的」に見える
- **影**: `box-shadow: 0 15px 40px rgba(0, 0, 0, 0.4)`が過剰

**スクロールリビール候補**:
- ✅ ヒーロー直下の製品カードグリッド（`.products-grid`）: 各カードを順次表示
- ✅ ユースケースセクション（`.use-cases`）: セクション単位で表示
- ❌ ヒーローセクション自体: ファーストビューなので不要

---

### 1.2 主要機能ページ（/autofill - autofill.html）

**ファーストビュー所感**:
- ヘッダー画像（`JobcanAutofill.png`）が背景に使用され、オーバーレイ（`rgba(0, 0, 0, 0.3)`）で読みやすさは確保
- フォーム入力領域（email, password, file）は整然としているが、ラベルの視覚的階層が弱い

**気になる点**:
- 見出しに絵文字が使用されている（`h1::before { content: '🕒'; }` - `templates/index.html:117-126`）
- フォーム入力の`border-radius: 12px`が大きい
- ボタンの`::before`疑似要素による「光るアニメーション」が過剰（`templates/autofill.html:328-337`）
- エラーメッセージ/ログ表示に絵文字が多用されている（✅❌⚠️🎉等）

**良い点**:
- フォームのフォーカス状態（`box-shadow: 0 0 0 3px var(--primary-blue-transparent)`）が明確
- 入力フィールドのパディング（18px 20px）が適切
- プログレスパネル（`templates/includes/progress_panel.html`）の構造は整然

**幼く見える要因**:
- **アイコン**: 見出しの絵文字（🕒）が装飾的（`templates/index.html:117-126`）
- **配色**: グラデーション背景（`linear-gradient(145deg, #1E1E1E 0%, #2A2A2A 100%)`）が多用
- **余白**: フォームグループ間（`margin-bottom: 30px`）は適切だが、ラベルと入力の間（12px）が狭い
- **文字**: `text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3)`がラベルに使用され、過剰
- **影**: コンテナの`box-shadow: 0 25px 50px rgba(0, 0, 0, 0.5)`が過剰
- **角丸**: コンテナの`border-radius: 20px`が大きい

**スクロールリビール候補**:
- ❌ フォーム入力領域: 即時操作が必要なため適用しない
- ✅ ヘッダー直下の説明テキスト: 軽くフェードイン
- ❌ プログレスパネル/ログ表示: 動的更新されるため適用しない

---

### 1.3 設定/ヘルプ/FAQ（/faq - faq.html）

**ファーストビュー所感**:
- FAQアイテム（`.faq-item`）は`border-left: 4px solid #4A9EFF`で視覚的に区別されているが、質問と回答の階層が弱い

**気になる点**:
- 見出しに絵文字が使用されている（`<h1>❓ よくある質問（FAQ）</h1>` - `templates/faq.html:99`）
- FAQアイテムの背景（`rgba(255, 255, 255, 0.03)`）が薄すぎて区別が弱い
- カテゴリラベル（`.category`）の`text-transform: uppercase` + `letter-spacing: 0.1em`が過剰

**良い点**:
- コンテナの最大幅（1000px）が読みやすさを確保
- 質問と回答の構造（`.faq-question`, `.faq-answer`）が明確
- リンクのホバー状態（`text-decoration: underline`）が適切

**幼く見える要因**:
- **アイコン**: 見出しの絵文字（❓）がカジュアル
- **配色**: 背景の透明度（0.03）が薄すぎて「浮いていない」
- **余白**: FAQアイテム間（`margin-bottom: 35px`）は適切
- **文字**: カテゴリラベルの`letter-spacing: 0.1em`が広すぎる

**スクロールリビール候補**:
- ✅ FAQアイテム（`.faq-item`）: 各アイテムを順次表示（stagger効果）
- ✅ カテゴリセクション（h2）: セクション単位で表示
- ✅ ナビゲーションリンク（`.nav-link`）: ページ下部の「戻る」リンク

---

### 1.4 ガイドページ（/guide/getting-started - guide_getting_started.html）

**ファーストビュー所感**:
- ページヘッダー（`templates/includes/page_header.html`）の構造は整然
- コンテンツの階層（h1 → h2 → h3）は明確だが、視覚的区別が弱い

**気になる点**:
- 見出しのフォントサイズが不統一（h1: 2.5em, h2: 1.8em, h3: 未定義）
- セクション間の余白が不規則
- コードブロック/リストのスタイリングが統一されていない

**良い点**:
- ページヘッダーの「戻る」リンクが機能している
- コンテンツの最大幅が適切

**幼く見える要因**:
- **余白**: セクション間隔が不規則
- **文字**: 見出し階層の視覚的区別が弱い（font-weight, color, sizeの統一性不足）

**スクロールリビール候補**:
- ✅ セクション（h2）: 各セクションを順次表示
- ✅ リスト項目: 長いリストを順次表示（stagger効果）
- ✅ コードブロック: 軽くフェードイン

---

### 1.5 その他（/about, /contact, /terms等）

**共通の気になる点**:
- 見出しに絵文字が使用されている箇所が多い
- コンテナのスタイリングがページ間で微妙に異なる（一貫性の欠如）
- フッター（`templates/includes/footer.html`）の3カラムグリッドは整然

**スクロールリビール候補**:
- ✅ セクション単位での表示
- ❌ フォーム入力領域（contact.html）: 適用しない

---

## 2. 見た目が幼くなる主因（横断）

### 2.1 アイコンのスタイルがポップ
**根拠**: 
- ナビゲーション（`templates/includes/header.html:10-13`）: 絵文字（🏠🕒🛠️📚）がカジュアルすぎる
- 見出し（`templates/index.html:117-126`）: `h1::before { content: '🕒'; }`が装飾的
- FAQ見出し（`templates/faq.html:99`）: `<h1>❓ よくある質問（FAQ）</h1>`がカジュアル
- ログメッセージ: 絵文字（✅❌⚠️🎉）が多用されている

**影響範囲**: 全ページ（特にHeader、見出し、ログ表示）

---

### 2.2 丸み過多
**根拠**:
- コンテナ: `border-radius: 20px`（`templates/index.html:55`, `templates/autofill.html:55`）
- カード: `border-radius: 16px`（`templates/landing.html:92`, `templates/tools/index.html:69`）
- ボタン/入力: `border-radius: 12px`（`templates/autofill.html:282, 315`）
- FAQアイテム: `border-radius: 12px`（`templates/faq.html:45`）

**影響範囲**: 全ページ（特にコンテナ、カード、ボタン、入力フィールド）

---

### 2.3 色が多い（グラデーション多用）
**根拠**:
- 背景: `linear-gradient(135deg, #121212 0%, #1A1A1A 50%, #0F0F0F 100%)`（全ページ）
- コンテナ: `linear-gradient(145deg, #1E1E1E 0%, #2A2A2A 100%)`（全ページ）
- フッター: `linear-gradient(145deg, #1A1A1A 0%, #0F0F0F 100%)`（`templates/autofill.html:175`）

**影響範囲**: 全ページ（背景、コンテナ、フッター）

---

### 2.4 余白が不規則
**根拠**:
- セクション間隔: 30px, 40px, 60px, 80pxが混在（統一されていない）
- 要素間隔: gap: 15px, 20px, 30pxが混在
- フォームグループ間: `margin-bottom: 30px`は統一されているが、ラベルと入力の間（12px）が狭い

**影響範囲**: 全ページ（特にセクション間、グリッド、フォーム）

---

### 2.5 文字階層が弱い
**根拠**:
- 見出しのfont-weight: 600が統一されているが、font-sizeが不統一（h1: 2.5em-3.2em, h2: 1.8em-2em）
- `letter-spacing: 0.08em`が広すぎて「装飾的」に見える
- `text-shadow`が多用されている（`templates/index.html:110-112`, `templates/autofill.html:272`）

**影響範囲**: 全ページ（特に見出し、ラベル）

---

### 2.6 ボタンの主従が曖昧
**根拠**:
- プライマリボタン（`.submit-btn`）とセカンダリボタン（`.download-btn`）の視覚的区別が弱い（両方とも`background: transparent`）
- hover効果が過剰（`transform: translateY(-2px)` + `box-shadow: 0 8px 25px`）
- 「光るアニメーション」（`::before`疑似要素）が過剰

**影響範囲**: 全ページ（特にautofill.html、landing.html）

---

### 2.7 影が過剰
**根拠**:
- コンテナ: `box-shadow: 0 25px 50px rgba(0, 0, 0, 0.5)`（`templates/index.html:56-59`）
- カードhover: `box-shadow: 0 15px 40px rgba(0, 0, 0, 0.4)`（`templates/landing.html:103`）
- ボタンhover: `box-shadow: 0 8px 25px rgba(74, 158, 255, 0.3)`（`templates/landing.html:80`）

**影響範囲**: 全ページ（特にコンテナ、カード、ボタン）

---

## 3. コード/構造の根拠（重要）

### 3.1 触るべき主要ファイル一覧

**共通コンポーネント**:
- `templates/includes/header.html`: ナビゲーション（絵文字アイコン）
- `templates/includes/footer.html`: フッター
- `templates/includes/page_header.html`: ページヘッダー
- `templates/includes/progress_panel.html`: プログレスパネル

**主要ページ**:
- `templates/landing.html`: トップページ
- `templates/index.html`: 旧トップページ（autofill.htmlから参照）
- `templates/autofill.html`: 主要機能ページ（フォーム）
- `templates/faq.html`: FAQページ
- `templates/guide_getting_started.html`: ガイドページ
- `templates/tools/index.html`: ツール一覧

**スタイル定義**:
- 各HTMLファイル内の`<style>`タグ（インラインスタイルと混在）
- CSS変数: `:root { --primary-blue: #003366; ... }`（各ページで定義）

---

### 3.2 問題の発生源

**Header（`templates/includes/header.html`）**:
- 絵文字アイコン（🏠🕒🛠️📚）がナビゲーションに使用されている（10-13行目）
- インラインスタイルが多用されている（一貫性の欠如）

**Layout（各ページの`.container`）**:
- グラデーション背景が多用されている
- `border-radius: 20px`が大きい
- `box-shadow`が過剰

**Typography（見出し、ラベル）**:
- 見出しに絵文字が使用されている（`templates/index.html:117-126`）
- `letter-spacing: 0.08em`が広すぎる
- `text-shadow`が多用されている

**Button/Input（フォーム、CTA）**:
- ボタンの`border-radius: 12px`が大きい
- hover効果が過剰（`transform` + `box-shadow`）
- 「光るアニメーション」（`::before`疑似要素）が過剰

**Color tokens（CSS変数）**:
- 各ページで個別に定義されている（一貫性の欠如）
- グラデーションが多用されている

---

### 3.3 改善の方向性（まだ実装しない。変えるべき責務境界やコンポーネント設計方針）

**共通スタイルシートの導入**:
- `static/css/common.css`を作成し、CSS変数、タイポグラフィ、余白、カラーを一元管理
- 各ページの`<style>`タグを最小化し、共通スタイルを参照

**コンポーネント化の推進**:
- ボタン、カード、入力フィールドを共通コンポーネント化（Jinja2マクロまたはinclude）
- アイコンをSVG化（Lucide/Heroicons）し、共通コンポーネント化

**デザインシステムの確立**:
- タイポグラフィスケール（h1-h6, body, caption）を定義
- 余白スケール（4px, 8px, 12px, 16px, 24px, 32px, 48px, 64px）を定義
- カラーパレット（ベース、アクセント、状態色）を定義

---

## 4. 改善提案（優先度つき）

### P0（最優先、効果大・工数小）

#### 4.1 絵文字アイコンの置換
**ねらい**: ナビゲーションと見出しの視覚的プロフェッショナリズムを向上

**変更内容**:
- ナビゲーション（`templates/includes/header.html`）: 絵文字（🏠🕒🛠️📚）をSVGアイコン（Lucide/Heroicons）に置換
- 見出し（`templates/index.html:117-126`）: `h1::before { content: '🕒'; }`を削除し、SVGアイコンに置換
- FAQ見出し（`templates/faq.html:99`）: 絵文字（❓）を削除

**影響範囲**: Header、見出し（全ページ）

**実装難易度**: M（SVGアイコンの導入、Jinja2テンプレートの修正）

---

#### 4.2 角丸の縮小
**ねらい**: 過剰な装飾を削減し、プロフェッショナルな印象に

**変更内容**:
- コンテナ: `border-radius: 20px` → `8px`
- カード: `border-radius: 16px` → `6px`
- ボタン/入力: `border-radius: 12px` → `4px`

**影響範囲**: 全ページ（コンテナ、カード、ボタン、入力フィールド）

**実装難易度**: S（CSS値の変更のみ）

---

#### 4.3 影の縮小
**ねらい**: 過剰な装飾を削減し、プロフェッショナルな印象に

**変更内容**:
- コンテナ: `box-shadow: 0 25px 50px rgba(0, 0, 0, 0.5)` → `0 2px 8px rgba(0, 0, 0, 0.1)`
- カードhover: `box-shadow: 0 15px 40px rgba(0, 0, 0, 0.4)` → `0 4px 12px rgba(0, 0, 0, 0.15)`
- ボタンhover: `box-shadow: 0 8px 25px rgba(74, 158, 255, 0.3)` → `0 2px 8px rgba(74, 158, 255, 0.2)`

**影響範囲**: 全ページ（コンテナ、カード、ボタン）

**実装難易度**: S（CSS値の変更のみ）

---

### P1（効果大・工数中）

#### 4.4 タイポグラフィの体系化
**ねらい**: 見出し階層の明確化、読みやすさの向上

**変更内容**:
- 見出しサイズの統一: h1: 2.5em, h2: 2em, h3: 1.5em, h4: 1.25em
- `letter-spacing: 0.08em` → `0.02em`（見出し）、`0.05em` → `0.01em`（本文）
- `text-shadow`の削除（見出し、ラベル）

**影響範囲**: 全ページ（見出し、ラベル、本文）

**実装難易度**: M（CSS値の変更、各ページの確認）

---

#### 4.5 余白の統一
**ねらい**: レイアウトの整然さを向上

**変更内容**:
- セクション間隔: 48px（統一）
- 要素間隔: gap: 16px（統一）
- フォームグループ間: `margin-bottom: 24px`（統一）
- ラベルと入力の間: `margin-bottom: 8px`（統一）

**影響範囲**: 全ページ（セクション間、グリッド、フォーム）

**実装難易度**: M（CSS値の変更、各ページの確認）

---

#### 4.6 ボタンの主従の明確化
**ねらい**: CTAの視覚的優先度を向上

**変更内容**:
- プライマリボタン: `background: rgba(74, 158, 255, 0.2)` → `#4A9EFF`（背景色を実色に）
- セカンダリボタン: `background: transparent`（現状維持）
- hover効果の縮小: `transform: translateY(-2px)` → `translateY(-1px)`
- 「光るアニメーション」（`::before`疑似要素）の削除

**影響範囲**: 全ページ（特にautofill.html、landing.html）

**実装難易度**: M（CSS値の変更、各ページの確認）

---

#### 4.7 グラデーション背景の簡素化
**ねらい**: 過剰な装飾を削減し、プロフェッショナルな印象に

**変更内容**:
- 背景: `linear-gradient(135deg, #121212 0%, #1A1A1A 50%, #0F0F0F 100%)` → `#121212`（単色）
- コンテナ: `linear-gradient(145deg, #1E1E1E 0%, #2A2A2A 100%)` → `#1E1E1E`（単色）
- フッター: `linear-gradient(145deg, #1A1A1A 0%, #0F0F0F 100%)` → `#1A1A1A`（単色）

**影響範囲**: 全ページ（背景、コンテナ、フッター）

**実装難易度**: S（CSS値の変更のみ）

---

### P2（中長期）

#### 4.8 共通スタイルシートの導入
**ねらい**: 一貫性の向上、保守性の向上

**変更内容**:
- `static/css/common.css`を作成し、CSS変数、タイポグラフィ、余白、カラーを一元管理
- 各ページの`<style>`タグを最小化し、共通スタイルを参照

**影響範囲**: 全ページ

**実装難易度**: L（共通スタイルシートの作成、各ページの修正）

---

#### 4.9 コンポーネント化の推進
**ねらい**: 一貫性の向上、保守性の向上

**変更内容**:
- ボタン、カード、入力フィールドを共通コンポーネント化（Jinja2マクロまたはinclude）
- アイコンをSVG化（Lucide/Heroicons）し、共通コンポーネント化

**影響範囲**: 全ページ

**実装難易度**: L（共通コンポーネントの作成、各ページの修正）

---

## 5. スクロールリビール追加の設計案（今回の追加要件）

### 5.1 方針

**"控えめ・速い・一貫した"プロ向けモーション**:
- アニメーション: `opacity: 0 → 1` + `transform: translateY(20px) → translateY(0)`
- duration: 300-400ms（短め）
- easing: `cubic-bezier(0.4, 0, 0.2, 1)`（統一）
- stagger: 50-100ms（リスト項目、カードグリッド）

**乱用禁止**:
- フォーム入力領域（autofill.htmlのアップロード/実行ボタン）には適用しない
- プログレスパネル/ログ表示（動的更新される領域）には適用しない
- エラーメッセージ（即時表示が必要）には適用しない

**アクセシビリティ**:
- `prefers-reduced-motion`対応必須（`@media (prefers-reduced-motion: reduce)`でアニメーション無効化）

---

### 5.2 どこに入れるべきか（候補をページ別に列挙）

#### トップページ（landing.html）
- ✅ 製品カードグリッド（`.products-grid`）: 各カードを順次表示（stagger効果）
- ✅ ユースケースセクション（`.use-cases`）: セクション単位で表示
- ❌ ヒーローセクション: ファーストビューなので不要

#### 主要機能ページ（autofill.html）
- ✅ ヘッダー直下の説明テキスト: 軽くフェードイン
- ❌ フォーム入力領域: 即時操作が必要なため適用しない
- ❌ プログレスパネル/ログ表示: 動的更新されるため適用しない

#### FAQページ（faq.html）
- ✅ FAQアイテム（`.faq-item`）: 各アイテムを順次表示（stagger効果）
- ✅ カテゴリセクション（h2）: セクション単位で表示
- ✅ ナビゲーションリンク（`.nav-link`）: ページ下部の「戻る」リンク

#### ガイドページ（guide_getting_started.html等）
- ✅ セクション（h2）: 各セクションを順次表示
- ✅ リスト項目: 長いリストを順次表示（stagger効果）
- ✅ コードブロック: 軽くフェードイン

#### その他（about.html, contact.html等）
- ✅ セクション単位での表示
- ❌ フォーム入力領域（contact.html）: 適用しない

---

### 5.3 実装アプローチ比較

#### 1) Framer Motion + IntersectionObserver（推奨）
**メリット**:
- 豊富なアニメーション機能
- SSR対応（Flask + Jinja2でも利用可能）
- アクセシビリティ対応（`prefers-reduced-motion`）

**デメリット**:
- 依存関係の追加（package.jsonに追加が必要）
- バンドルサイズの増加

**適用可能性**: 低（React/Next.jsではないため、直接利用不可）

---

#### 2) 素のIntersectionObserverでclass付与（推奨）
**メリット**:
- 軽量（依存関係なし）
- バニラJSで実装可能
- アクセシビリティ対応（`prefers-reduced-motion`）

**デメリット**:
- アニメーション機能が限定的

**適用可能性**: 高（Flask + Jinja2 + バニラJSで実装可能）

---

#### 3) 既存ライブラリ（AOS等）が入っていれば継続
**現状**: 未使用（package.jsonに記載なし）

**適用可能性**: 低（新規導入が必要）

---

### 5.4 推奨案（素のIntersectionObserverでclass付与）

**理由**:
- 依存関係なし（軽量）
- SSR対応（Flask + Jinja2で問題なく動作）
- 保守性（バニラJSで実装可能）
- チーム運用（追加学習コストが低い）

**具体設計**:

**共通JavaScript（`static/js/scroll-reveal.js`）**:
```javascript
// IntersectionObserverを使用したスクロールリビール
(function() {
    // prefers-reduced-motion対応
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        return;
    }

    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('revealed');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // 初期化: data-reveal属性を持つ要素を監視
    document.addEventListener('DOMContentLoaded', () => {
        const elements = document.querySelectorAll('[data-reveal]');
        elements.forEach(el => observer.observe(el));
    });
})();
```

**共通CSS（`static/css/scroll-reveal.css`）**:
```css
/* スクロールリビール用スタイル */
[data-reveal] {
    opacity: 0;
    transform: translateY(20px);
    transition: opacity 0.4s cubic-bezier(0.4, 0, 0.2, 1),
                transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

[data-reveal].revealed {
    opacity: 1;
    transform: translateY(0);
}

/* stagger効果用（data-reveal-stagger属性） */
[data-reveal-stagger] > * {
    opacity: 0;
    transform: translateY(20px);
    transition: opacity 0.4s cubic-bezier(0.4, 0, 0.2, 1),
                transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

[data-reveal-stagger].revealed > *:nth-child(1) { transition-delay: 0ms; }
[data-reveal-stagger].revealed > *:nth-child(2) { transition-delay: 50ms; }
[data-reveal-stagger].revealed > *:nth-child(3) { transition-delay: 100ms; }
[data-reveal-stagger].revealed > *:nth-child(4) { transition-delay: 150ms; }
[data-reveal-stagger].revealed > *:nth-child(5) { transition-delay: 200ms; }
/* ... 必要に応じて追加 */

[data-reveal-stagger].revealed > * {
    opacity: 1;
    transform: translateY(0);
}

/* prefers-reduced-motion対応 */
@media (prefers-reduced-motion: reduce) {
    [data-reveal],
    [data-reveal-stagger] > * {
        opacity: 1;
        transform: none;
        transition: none;
    }
}
```

**使用例（Jinja2テンプレート）**:
```html
<!-- 単一要素 -->
<div data-reveal>
    <h2>セクションタイトル</h2>
    <p>コンテンツ</p>
</div>

<!-- リスト（stagger効果） -->
<ul data-reveal-stagger>
    <li>項目1</li>
    <li>項目2</li>
    <li>項目3</li>
</ul>

<!-- カードグリッド（stagger効果） -->
<div class="products-grid" data-reveal-stagger>
    <div class="product-card">カード1</div>
    <div class="product-card">カード2</div>
    <div class="product-card">カード3</div>
</div>
```

**追加/変更が必要なファイル**:
- `static/js/scroll-reveal.js`: 新規作成
- `static/css/scroll-reveal.css`: 新規作成
- `templates/includes/head_meta.html`: scroll-reveal.cssの読み込みを追加
- 各ページテンプレート: `data-reveal`属性の追加

---

## 6. "プロフェッショナルに見える"デザイン要件案（Geminiに渡すため）

### 6.1 タイポグラフィ要件

**見出し階層**:
- h1: 2.5em, font-weight: 600, letter-spacing: 0.02em, line-height: 1.2
- h2: 2em, font-weight: 600, letter-spacing: 0.02em, line-height: 1.3
- h3: 1.5em, font-weight: 600, letter-spacing: 0.01em, line-height: 1.4
- h4: 1.25em, font-weight: 600, letter-spacing: 0.01em, line-height: 1.4

**本文**:
- body: 1rem, font-weight: 400, letter-spacing: 0.01em, line-height: 1.6
- caption: 0.875rem, font-weight: 400, letter-spacing: 0.01em, line-height: 1.5

**数字の扱い**:
- 等幅フォント（`font-variant-numeric: tabular-nums`）を使用（データ表示時）

---

### 6.2 余白/グリッド要件

**max幅**:
- コンテナ: 1200px（デスクトップ）
- コンテンツ: 800px（読みやすさ重視）

**section spacing**:
- セクション間隔: 48px（統一）

**フォームの整列**:
- フォームグループ間: 24px
- ラベルと入力の間: 8px
- 入力フィールドのパディング: 12px 16px

---

### 6.3 カラー要件

**ベースはニュートラル + アクセント1色**:
- 背景: #121212（単色、グラデーションなし）
- コンテナ: #1E1E1E（単色、グラデーションなし）
- テキスト: #FFFFFF（主要）、rgba(255, 255, 255, 0.8)（セカンダリ）
- アクセント: #4A9EFF（プライマリカラー、1色のみ）

**状態色ルール**:
- 成功: #4CAF50
- 警告: #FF9800
- エラー: #F44336
- 無効: rgba(255, 255, 255, 0.3)

---

### 6.4 アイコン要件

**線形アイコン統一**:
- Lucide Icons または Heroicons（線形スタイル）
- サイズ: 20px（標準）、24px（見出し）、16px（小）
- 線幅: 1.5px（統一）
- 使用箇所: ナビゲーション、見出し、ボタン、ステータス表示

---

### 6.5 コンポーネント要件

**Card**:
- 角丸: 6px
- 影: `0 2px 8px rgba(0, 0, 0, 0.1)`（hover時: `0 4px 12px rgba(0, 0, 0, 0.15)`）
- ボーダー: `1px solid rgba(255, 255, 255, 0.1)`
- hover: `translateY(-2px)`（控えめ）

**Button**:
- 角丸: 4px
- プライマリ: `background: #4A9EFF`, `color: #FFFFFF`
- セカンダリ: `background: transparent`, `border: 1px solid rgba(255, 255, 255, 0.3)`
- hover: `translateY(-1px)`（控えめ）、影なし
- focus ring: `0 0 0 3px rgba(74, 158, 255, 0.3)`

**Input**:
- 角丸: 4px
- ボーダー: `1px solid rgba(255, 255, 255, 0.2)`
- パディング: 12px 16px
- focus: `border-color: #4A9EFF`, `box-shadow: 0 0 0 3px rgba(74, 158, 255, 0.2)`

---

### 6.6 モーション要件

**スクロールリビールの強さ**:
- `opacity: 0 → 1` + `translateY(20px) → translateY(0)`
- duration: 300-400ms
- easing: `cubic-bezier(0.4, 0, 0.2, 1)`

**staggerの有無**:
- リスト項目、カードグリッド: 50-100ms間隔

**禁止事項**:
- フォーム入力領域への適用
- 動的更新される領域（プログレスパネル、ログ表示）への適用
- エラーメッセージへの適用

---

### 6.7 参考にすべき雰囲気

**"B2B SaaSの管理画面"**:
- Stripe風の余白（広め、統一された間隔）
- Linear風のタイポグラフィ（読みやすさ重視、装飾的要素なし）
- Vercel風のカラーパレット（ニュートラルベース + アクセント1色）
- GitHub風のコンポーネント（角丸控えめ、影控えめ）

**"監査に耐える堅さ"**:
- 過剰な装飾なし（グラデーション、影、角丸を控えめに）
- 一貫性（同じ要素は同じスタイル）
- 情報階層の明確化（見出し、余白、カラーで区別）

---

## 7. 追加で必要な情報（あれば）

### 主要ターゲット
- **社内利用**: 企業内の勤怠管理担当者
- **外部配布**: 業務効率化ツールとしての提供

### ブランドカラー
- プライマリ: #4A9EFF（既存）
- 背景: #121212（ダークテーマ）

### 最重要CTA
- トップページ: 「Jobcan自動入力ツールを使う」（/autofillへのリンク）
- 主要機能ページ: 「ファイルをアップロード」（フォーム送信）

---

## 評価軸で採点（1〜5点）

| 評価軸 | 点数 | 根拠 |
|--------|------|------|
| タイポグラフィの品位 | 2/5 | 見出しの`letter-spacing: 0.08em`が広すぎ、`text-shadow`が多用されている |
| 余白/レイアウトの整然さ | 3/5 | セクション間隔が不統一（30px, 40px, 60px, 80pxが混在） |
| カラーの統一感 | 2/5 | グラデーション背景が多用され、カラーパレットが複雑 |
| アイコンの一貫性/適切さ | 1/5 | 絵文字アイコンが多用され、プロフェッショナル感に欠ける |
| 情報設計 | 3/5 | 見出し階層は明確だが、視覚的区別が弱い |
| UIの密度 | 3/5 | 読みやすさは確保されているが、情報階層が弱い |
| CTAの明確さ | 2/5 | プライマリボタンとセカンダリボタンの視覚的区別が弱い |
| スクロールリビールの相性 | 4/5 | 長文コンテンツ（ガイド、FAQ）での読み進め体験向上に有効 |

**総合評価**: 2.5/5（改善の余地が大きい）

---

## まとめ

現状のUIは機能性は高いが、視覚的なプロフェッショナリズムに欠けています。主な改善ポイントは、**絵文字アイコンの置換**、**角丸・影の縮小**、**タイポグラフィ・余白の体系化**、**カラーパレットの簡素化**です。スクロールリビール演出は、**素のIntersectionObserverでclass付与**する方式を推奨し、長文コンテンツでの読み進め体験を向上させます。

このレポートをGeminiに渡すことで、具体的なデザイン指示プロンプトを作成し、実装計画を立てることができます。
