#!/usr/bin/env node
/**
 * UI監査レポート生成スクリプト
 * Flaskアプリケーションの全ページを解析し、Gemini向けのUI監査レポートを生成
 */

import * as fs from 'fs';
import * as path from 'path';

interface Route {
  path: string;
  template: string;
  description: string;
  importance: 'High' | 'Medium' | 'Low';
}

interface PageAnalysis {
  path: string;
  file: string;
  purpose: string;
  components: string[];
  structure: string;
  styles: {
    inline: number;
    styleTag: boolean;
    classes: string[];
  };
  animations: string[];
  improvements: string[];
  risk: 'Low' | 'Med' | 'High';
}

// app.pyからルートを抽出
function extractRoutes(): Route[] {
  const appPyPath = path.join(process.cwd(), 'app.py');
  const content = fs.readFileSync(appPyPath, 'utf-8');
  
  const routes: Route[] = [];
  const routeRegex = /@app\.route\(['"]([^'"]+)['"]\)\s*\n\s*def\s+(\w+)\([^)]*\):\s*\n\s*"""(.*?)"""/gs;
  
  let match;
  while ((match = routeRegex.exec(content)) !== null) {
    const routePath = match[1];
    const funcName = match[2];
    const description = match[3].trim();
    
    // render_templateを探す
    const funcContent = content.substring(match.index);
    const templateMatch = funcContent.match(/render_template\(['"]([^'"]+)['"]/);
    const template = templateMatch ? templateMatch[1] : '';
    
    // 重要度を判定
    let importance: 'High' | 'Medium' | 'Low' = 'Medium';
    if (routePath === '/' || routePath === '/autofill' || routePath.startsWith('/tools') || 
        routePath.startsWith('/guide') || routePath === '/privacy' || routePath === '/terms') {
      importance = 'High';
    } else if (routePath.startsWith('/blog') || routePath.startsWith('/case-study')) {
      importance = 'Low';
    }
    
    routes.push({
      path: routePath,
      template,
      description,
      importance
    });
  }
  
  return routes;
}

// HTMLファイルを解析
function analyzeHtmlFile(filePath: string): PageAnalysis | null {
  if (!fs.existsSync(filePath)) {
    return null;
  }
  
  const content = fs.readFileSync(filePath, 'utf-8');
  
  // 目的を抽出（page_title, page_descriptionから）
  const titleMatch = content.match(/page_title\s*=\s*['"]([^'"]+)['"]/);
  const descMatch = content.match(/page_description\s*=\s*['"]([^'"]+)['"]/);
  const purpose = descMatch ? descMatch[1] : (titleMatch ? titleMatch[1] : '');
  
  // コンポーネントを抽出（include, extends）
  const includes = content.match(/{%\s*include\s+['"]([^'"]+)['"]\s*%}/g) || [];
  const components = includes.map(inc => {
    const match = inc.match(/['"]([^'"]+)['"]/);
    return match ? match[1] : '';
  }).filter(Boolean);
  
  // 構造を簡易抽出（主要なセクション）
  const sections: string[] = [];
  if (content.includes('hero') || content.includes('Hero')) sections.push('Hero');
  if (content.includes('container')) sections.push('Container');
  if (content.includes('panel') || content.includes('tool-section')) sections.push('Panel');
  if (content.includes('grid') || content.includes('products-grid') || content.includes('main-layout')) sections.push('Grid');
  if (content.includes('form') || content.includes('input') || content.includes('textarea') || content.includes('select')) sections.push('Form');
  if (content.includes('button') || content.includes('action-button') || content.includes('submit-btn')) sections.push('Button');
  if (content.includes('output') || content.includes('preview') || content.includes('download-panel') || content.includes('progress-panel')) sections.push('Output');
  if (content.includes('file-dropzone') || content.includes('file-list')) sections.push('FileInput');
  if (content.includes('option-panel') || content.includes('option-group')) sections.push('Options');
  
  // スタイル解析
  const inlineStyleCount = (content.match(/style\s*=/g) || []).length;
  const hasStyleTag = content.includes('<style>');
  const classMatches = content.match(/class\s*=\s*['"]([^'"]+)['"]/g) || [];
  const classes = classMatches.map(m => {
    const match = m.match(/['"]([^'"]+)['"]/);
    return match ? match[1] : '';
  }).filter(Boolean);
  
  // アニメーション検出
  const animations: string[] = [];
  if (content.includes('transition')) animations.push('CSS transition');
  if (content.includes('transform')) animations.push('CSS transform');
  if (content.includes('animation')) animations.push('CSS animation');
  if (content.includes('hover')) animations.push('Hover effects');
  
  // 改善余地（簡易判定）
  const improvements: string[] = [];
  if (inlineStyleCount > 20) improvements.push('インラインスタイルが多数（CSS分離推奨）');
  if (!content.includes('aria-label') && (content.includes('button') || content.includes('input'))) improvements.push('アクセシビリティ: aria-label不足');
  if (!content.includes('alt=') && content.includes('<img')) improvements.push('アクセシビリティ: alt属性不足');
  if (!hasStyleTag && inlineStyleCount > 0) improvements.push('スタイル: <style>タグへの統合推奨');
  if (content.includes('onclick=') || content.includes('onchange=') || content.includes('oninput=')) improvements.push('イベントハンドラ: インラインイベント（分離推奨）');
  if (content.includes('alert(') || content.includes('confirm(')) improvements.push('UX: alert/confirmの使用（モーダル推奨）');
  if (!content.includes('loading') && (content.includes('submit') || content.includes('button'))) improvements.push('UX: ローディング状態の表示不足');
  if (!content.includes('error') && content.includes('form')) improvements.push('UX: エラー状態の表示不足');
  
  // リスク判定
  let risk: 'Low' | 'Med' | 'High' = 'Low';
  if (filePath.includes('autofill') || filePath.includes('landing')) {
    risk = 'High';
  } else if (filePath.includes('tools/')) {
    risk = 'Med';
  }
  
  return {
    path: '',
    file: path.relative(process.cwd(), filePath),
    purpose,
    components,
    structure: sections.join(' → '),
    styles: {
      inline: inlineStyleCount,
      styleTag: hasStyleTag,
      classes: [...new Set(classes)].slice(0, 10) // 重複除去、上位10個
    },
    animations,
    improvements,
    risk
  };
}

// 共通コンポーネントを解析
function analyzeCommonComponents(): any {
  const includesDir = path.join(process.cwd(), 'templates', 'includes');
  const components: any = {};
  
  if (!fs.existsSync(includesDir)) {
    return components;
  }
  
  const files = fs.readdirSync(includesDir);
  for (const file of files) {
    if (file.endsWith('.html')) {
      const filePath = path.join(includesDir, file);
      const content = fs.readFileSync(filePath, 'utf-8');
      
      components[file] = {
        inlineStyles: (content.match(/style\s*=/g) || []).length,
        hasStyleTag: content.includes('<style>'),
        usesJinja: content.includes('{%') || content.includes('{{'),
        purpose: file.replace('.html', '')
      };
    }
  }
  
  return components;
}

// スタイルパターンを分析
function analyzeStylePatterns(): any {
  const templatesDir = path.join(process.cwd(), 'templates');
  const patterns: any = {
    colors: new Set<string>(),
    fonts: new Set<string>(),
    spacing: new Set<string>(),
    commonClasses: new Map<string, number>()
  };
  
  function scanDirectory(dir: string) {
    const files = fs.readdirSync(dir);
    for (const file of files) {
      const filePath = path.join(dir, file);
      const stat = fs.statSync(filePath);
      
      if (stat.isDirectory()) {
        scanDirectory(filePath);
      } else if (file.endsWith('.html')) {
        const content = fs.readFileSync(filePath, 'utf-8');
        
        // カラー抽出
        const colorMatches = content.match(/#[0-9A-Fa-f]{6}|rgba?\([^)]+\)/g) || [];
        colorMatches.forEach(c => patterns.colors.add(c));
        
        // フォント抽出
        const fontMatches = content.match(/font-family:\s*([^;]+)/g) || [];
        fontMatches.forEach(f => {
          const match = f.match(/font-family:\s*(.+)/);
          if (match) patterns.fonts.add(match[1].trim());
        });
        
        // クラス使用頻度
        const classMatches = content.match(/class\s*=\s*['"]([^'"]+)['"]/g) || [];
        classMatches.forEach(m => {
          const match = m.match(/['"]([^'"]+)['"]/);
          if (match) {
            const classes = match[1].split(/\s+/);
            classes.forEach(c => {
              patterns.commonClasses.set(c, (patterns.commonClasses.get(c) || 0) + 1);
            });
          }
        });
      }
    }
  }
  
  scanDirectory(templatesDir);
  
  const entries = Array.from(patterns.commonClasses.entries()) as [string, number][];
  
  return {
    colors: Array.from(patterns.colors).slice(0, 20),
    fonts: Array.from(patterns.fonts),
    commonClasses: entries
      .sort((a, b) => b[1] - a[1])
      .slice(0, 20)
      .map(([name, count]) => ({ name, count }))
  };
}

// レポート生成
function generateReport(): string {
  const routes = extractRoutes();
  const commonComponents = analyzeCommonComponents();
  const stylePatterns = analyzeStylePatterns();
  
  let report = `# UI監査レポート - RT Tools

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
`;

  // 重要度順にソート
  const sortedRoutes = routes.sort((a, b) => {
    const order = { High: 0, Medium: 1, Low: 2 };
    return order[a.importance] - order[b.importance];
  });
  
  for (const route of sortedRoutes) {
    if (route.template) {
      const importanceBadge = route.importance === 'High' ? '🔴 High' : 
                             route.importance === 'Medium' ? '🟡 Medium' : '🟢 Low';
      report += `| ${route.path} | \`${route.template}\` | ${importanceBadge} | ${route.description} |\n`;
    }
  }
  
  report += `\n### 重要度別分類\n\n`;
  report += `**High (🔴)**: LP、AutoFill、Tools、Guide、Legalページ\n`;
  report += `**Medium (🟡)**: FAQ、About、Contact、Best Practices\n`;
  report += `**Low (🟢)**: Blog記事、Case Study\n\n`;
  
  report += `---\n\n## 2. 共通UI/デザインシステムの現状\n\n`;
  
  report += `### Layout構造\n\n`;
  report += `- **Header**: \`templates/includes/header.html\`\n`;
  report += `  - 固定ナビゲーション（sticky, top: 0）\n`;
  report += `  - ロゴ + ナビゲーションリンク（Home, AutoFill, Tools, Guide）\n`;
  report += `  - アクティブ状態のハイライト（#4A9EFF）\n`;
  report += `  - モバイル対応（@media max-width: 768px）\n\n`;
  
  report += `- **Footer**: \`templates/includes/footer.html\`\n`;
  report += `  - 3カラムグリッド（ガイド、リソース、法的情報）\n`;
  report += `  - データ保持方針の表示\n`;
  report += `  - バージョン表示\n`;
  report += `  - レスポンシブグリッド（auto-fit, minmax(200px, 1fr)）\n\n`;
  
  report += `- **Container**: 各ページで共通の \`.container\` クラス\n`;
  report += `  - max-width: 1200px\n`;
  report += `  - margin: 0 auto\n`;
  report += `  - padding: 40px 20px\n\n`;
  
  report += `### Typography/Color/Spacing\n\n`;
  report += `**Typography**:\n`;
  report += `- フォント: 'Noto Sans JP', 'Helvetica Neue', 'Segoe UI', sans-serif\n`;
  report += `- letter-spacing: 0.05em（統一）\n`;
  report += `- line-height: 1.6（統一）\n\n`;
  
  report += `**Color Palette** (使用頻度の高い色):\n`;
  for (const color of stylePatterns.colors.slice(0, 10)) {
    report += `- \`${color}\`\n`;
  }
  report += `\n主な色:\n`;
  report += `- 背景: linear-gradient(135deg, #121212 0%, #1A1A1A 50%, #0F0F0F 100%)\n`;
  report += `- テキスト: #FFFFFF, rgba(255, 255, 255, 0.8-0.9)\n`;
  report += `- アクセント: #4A9EFF（プライマリカラー）\n`;
  report += `- 成功: #4CAF50\n`;
  report += `- 警告: #FF9800\n`;
  report += `- エラー: #F44336\n\n`;
  
  report += `**Spacing**:\n`;
  report += `- コンテナパディング: 40px 20px\n`;
  report += `- セクション間隔: 30-60px\n`;
  report += `- 要素間隔: 10-20px（gap, margin）\n\n`;
  
  report += `### コンポーネント設計方針\n\n`;
  report += `**共通コンポーネント** (\`templates/includes/\`):\n\n`;
  for (const [file, info] of Object.entries(commonComponents)) {
    report += `- **${file}**: ${(info as any).purpose}\n`;
    report += `  - インラインスタイル: ${(info as any).inlineStyles}箇所\n`;
    report += `  - <style>タグ: ${(info as any).hasStyleTag ? 'あり' : 'なし'}\n`;
    report += `  - Jinja2使用: ${(info as any).usesJinja ? 'あり' : 'なし'}\n\n`;
  }
  
  report += `**共通部品**:\n`;
  report += `- Button: \`.action-button\`, \`.cta-button\`（インラインスタイル）\n`;
  report += `- Card: \`.product-card\`, \`.panel\`, \`.tool-section\`（インラインスタイル）\n`;
  report += `- Form: インラインスタイル（統一されたクラスなし）\n`;
  report += `- Modal: なし（確認ダイアログはalert/confirm）\n`;
  report += `- Toast: \`MinutesExport.showToast()\`（JavaScript実装）\n`;
  report += `- Progress: \`.progress-panel\`（カスタム実装）\n\n`;
  
  report += `**よく使われるクラス** (上位10):\n`;
  for (const cls of stylePatterns.commonClasses.slice(0, 10)) {
    report += `- \`.${(cls as any).name}\`: ${(cls as any).count}回\n`;
  }
  
  report += `\n---\n\n## 3. ページ別UI監査\n\n`;
  
  // 重要度Highのページを詳細に、その他は要約
  const highPriorityRoutes = sortedRoutes.filter(r => r.importance === 'High' && r.template);
  
  for (const route of highPriorityRoutes) {
    const templatePath = path.join(process.cwd(), 'templates', route.template);
    const analysis = analyzeHtmlFile(templatePath);
    
    if (analysis) {
      report += `### ${route.path}\n\n`;
      report += `- **Path**: \`${route.path}\`\n`;
      report += `- **File**: \`${analysis.file}\`\n`;
      report += `- **目的**: ${analysis.purpose || route.description}\n`;
      report += `- **主要コンポーネント**:\n`;
      for (const comp of analysis.components) {
        report += `  - \`${comp}\`\n`;
      }
      report += `- **UI構造**: ${analysis.structure || '未検出'}\n`;
      report += `- **スタイル**:\n`;
      report += `  - インラインスタイル: ${analysis.styles.inline}箇所\n`;
      report += `  - <style>タグ: ${analysis.styles.styleTag ? 'あり' : 'なし'}\n`;
      report += `  - 主要クラス: ${analysis.styles.classes.slice(0, 5).join(', ') || 'なし'}\n`;
      report += `- **アニメーション**: ${analysis.animations.join(', ') || 'なし'}\n`;
      report += `- **改善余地**:\n`;
      for (const imp of analysis.improvements) {
        report += `  - ${imp}\n`;
      }
      if (analysis.improvements.length === 0) {
        report += `  - （特になし）\n`;
      }
      report += `- **変更リスク**: ${analysis.risk} - ${analysis.risk === 'High' ? '主要機能ページのため慎重に' : analysis.risk === 'Med' ? '中程度の影響' : '低リスク'}\n\n`;
    }
  }
  
  // その他のページは要約
  const otherRoutes = sortedRoutes.filter(r => r.importance !== 'High' && r.template);
  if (otherRoutes.length > 0) {
    report += `### その他のページ（要約）\n\n`;
    for (const route of otherRoutes.slice(0, 10)) { // 最初の10件のみ
      report += `- **${route.path}**: \`${route.template}\` - ${route.description}\n`;
    }
    if (otherRoutes.length > 10) {
      report += `- （他 ${otherRoutes.length - 10} ページ）\n`;
    }
    report += `\n`;
  }
  
  report += `---\n\n## 4. 横断課題まとめ（改善余地の共通パターン）\n\n`;
  
  report += `### ナビ/導線の一貫性\n`;
  report += `- ✅ ヘッダーとフッターは統一されている\n`;
  report += `- ⚠️ 各ページのCTA配置が統一されていない\n`;
  report += `- ⚠️ パンくずリストがない\n\n`;
  
  report += `### CTA配置、Hero、コピー\n`;
  report += `- ✅ LPにはHeroセクションがある\n`;
  report += `- ⚠️ ツールページのCTAが統一されていない\n`;
  report += `- ⚠️ エンプティステートのガイドが不足\n\n`;
  
  report += `### フォームUX（validation、helper text）\n`;
  report += `- ⚠️ バリデーションメッセージがalert()で表示（UX改善余地）\n`;
  report += `- ⚠️ ヘルパーテキストが不足している箇所がある\n`;
  report += `- ⚠️ エラー状態の視覚的フィードバックが弱い\n\n`;
  
  report += `### 結果表示（一覧、フィルタ、空状態）\n`;
  report += `- ✅ ツールページにはProgressPanelとDownloadPanelがある\n`;
  report += `- ⚠️ 空状態のガイドが不足\n`;
  report += `- ⚠️ エラー状態の表示が統一されていない\n\n`;
  
  report += `### Loading/Progress/Cancel\n`;
  report += `- ✅ ToolRunnerで進捗表示がある\n`;
  report += `- ⚠️ ローディングスケルトンがない\n`;
  report += `- ⚠️ Cancel後の状態表示が弱い\n\n`;
  
  report += `### モバイル対応（レスポンシブ）\n`;
  report += `- ✅ ヘッダーにモバイル対応あり\n`;
  report += `- ⚠️ 一部ページでモバイル最適化が不足\n`;
  report += `- ⚠️ タッチ操作の最適化が不足\n\n`;
  
  report += `### アクセシビリティ（label/aria/contrast）\n`;
  report += `- ⚠️ aria-labelが不足している箇所が多い\n`;
  report += `- ⚠️ フォーカス管理が不十分\n`;
  report += `- ⚠️ キーボード操作の最適化が不足\n`;
  report += `- ✅ コントラスト比は概ね良好（ダークテーマ）\n\n`;
  
  report += `### パフォーマンス（画像、LCP/CLS、bundle）\n`;
  report += `- ⚠️ 画像の遅延読み込みがない\n`;
  report += `- ⚠️ JavaScriptのバンドル最適化が未実施\n`;
  report += `- ⚠️ フォントの最適化が未実施\n\n`;
  
  report += `### アニメーション指針（控えめ・速い・一貫）\n`;
  report += `- ✅ transition: all 0.3s が統一されている\n`;
  report += `- ⚠️ アニメーションの一貫性が不足\n`;
  report += `- ⚠️ マイクロインタラクションが少ない\n\n`;
  
  report += `---\n\n## 5. "モダンで洗練" のターゲット定義（Gemini向けに言語化）\n\n`;
  
  report += `### デザイン目標\n`;
  report += `- **Minimal & Calm**: 余計な装飾を排除し、機能に集中\n`;
  report += `- **Developer-friendly**: 技術者向けツールとして、情報密度を適切に保つ\n`;
  report += `- **Premium**: 高品質なUIで信頼感を醸成\n`;
  report += `- **Dark-first**: ダークテーマを基本とし、目に優しい\n\n`;
  
  report += `### 参考サイトのタイプ\n`;
  report += `- **Vercel**: ミニマルで洗練されたデザイン、適切な余白\n`;
  report += `- **Linear**: スムーズなアニメーション、一貫したデザインシステム\n`;
  report += `- **Stripe**: 明確な階層構造、優れたタイポグラフィ\n`;
  report += `- **GitHub**: 機能性重視、情報密度の適切な管理\n\n`;
  
  report += `### アニメーションの方向性\n`;
  report += `- **Micro-interactions**: ボタンホバー、フォーカス、クリックフィードバック\n`;
  report += `- **Page transition**: ページ遷移時のスムーズなトランジション（将来的に）\n`;
  report += `- **Loading skeleton**: ローディング中のスケルトンスクリーン\n`;
  report += `- **Progress feedback**: 処理中の明確な進捗表示\n`;
  report += `- **Error states**: エラー時の適切なアニメーション\n\n`;
  
  report += `### コンポーネント方針\n`;
  report += `- **shadcn/ui + Tailwind CSS**: 統一されたデザインシステムの導入を検討\n`;
  report += `- **Token化**: カラー、スペーシング、タイポグラフィをトークン化\n`;
  report += `- **Dark mode対応**: 現在のダークテーマを維持しつつ、システム設定対応も検討\n`;
  report += `- **再利用性**: 共通コンポーネントの徹底的な再利用\n\n`;
  
  report += `---\n\n## 6. 実装方針案（Geminiが提案しやすい粒度）\n\n`;
  
  report += `### Phase 1: デザインシステム整備（tokens、共通コンポーネント）\n`;
  report += `**完了条件**:\n`;
  report += `- Tailwind CSSの導入と設定\n`;
  report += `- デザイントークン（カラー、スペーシング、タイポグラフィ）の定義\n`;
  report += `- 共通コンポーネント（Button, Card, Form, Modal等）の実装\n`;
  report += `- 既存ページへの段階的適用\n\n`;
  
  report += `### Phase 2: ナビ/LP改善\n`;
  report += `**完了条件**:\n`;
  report += `- ヘッダー/フッターのデザイン刷新\n`;
  report += `- LPのHeroセクション改善\n`;
  report += `- CTA配置の最適化\n`;
  report += `- モバイル対応の強化\n\n`;
  
  report += `### Phase 3: 各ツールUI刷新（入力→処理→結果）\n`;
  report += `**完了条件**:\n`;
  report += `- ツールページの統一レイアウト\n`;
  report += `- フォームUXの改善（バリデーション、ヘルパーテキスト）\n`;
  report += `- 結果表示の改善（空状態、エラー状態）\n`;
  report += `- 進捗表示の改善（スケルトン、アニメーション）\n\n`;
  
  report += `### Phase 4: アニメーション/アクセシビリティ/パフォーマンス仕上げ\n`;
  report += `**完了条件**:\n`;
  report += `- マイクロインタラクションの追加\n`;
  report += `- アクセシビリティの改善（aria-label, キーボード操作）\n`;
  report += `- パフォーマンス最適化（画像遅延読み込み、JSバンドル）\n`;
  report += `- 最終的なUI/UXテスト\n\n`;
  
  report += `---\n\n## 7. Geminiに投げるプロンプト案（3種類）\n\n`;
  
  report += `### A) 全体方針を設計させるプロンプト\n\n`;
  report += `\`\`\`\n`;
  report += `以下のUI監査レポートを基に、RT ToolsのUI改善の全体方針を設計してください。\n\n`;
  report += `【ここにレポートを貼る】\n\n`;
  report += `要件:\n`;
  report += `1. 現状の課題を整理し、優先順位をつける\n`;
  report += `2. デザインシステムの導入方針を提案する（shadcn/ui + Tailwind CSS推奨）\n`;
  report += `3. 4つのPhaseの詳細な実装計画を作成する\n`;
  report += `4. 各Phaseの完了条件と成果物を明確にする\n`;
  report += `5. リスクと対策を記載する\n\n`;
  report += `出力形式: Markdown\n`;
  report += `\`\`\`\n\n`;
  
  report += `### B) ページ単位で改修案と実装手順を出させるプロンプト\n\n`;
  report += `\`\`\`\n`;
  report += `以下のUI監査レポートを基に、特定ページの改修案と実装手順を提案してください。\n\n`;
  report += `【ここにレポートを貼る】\n\n`;
  report += `対象ページ: /tools/image-batch（画像一括変換ツール）\n\n`;
  report += `要件:\n`;
  report += `1. 現状のUI構造を分析する\n`;
  report += `2. 改善案を具体的に提示する（Before/After）\n`;
  report += `3. 実装手順をステップバイステップで記載する\n`;
  report += `4. 必要なコンポーネントとスタイルを具体的に記載する\n`;
  report += `5. 既存機能を壊さないための注意点を記載する\n\n`;
  report += `出力形式: Markdown + コード例\n`;
  report += `\`\`\`\n\n`;
  
  report += `### C) shadcn + Tailwind + Framer Motion前提で、具体的コンポーネントコードを書かせるプロンプト\n\n`;
  report += `\`\`\`\n`;
  report += `以下のUI監査レポートを基に、shadcn/ui + Tailwind CSS + Framer Motionを使用して、\n`;
  report += `RT Toolsの共通コンポーネントを実装してください。\n\n`;
  report += `【ここにレポートを貼る】\n\n`;
  report += `要件:\n`;
  report += `1. Button, Card, Form, Modal, Toast, Progress コンポーネントを実装\n`;
  report += `2. ダークテーマに対応\n`;
  report += `3. アクセシビリティを考慮（aria-label, キーボード操作）\n`;
  report += `4. マイクロインタラクションを追加（Framer Motion）\n`;
  report += `5. TypeScript + Reactで実装（Next.js想定だが、コンポーネント単体で動作するように）\n\n`;
  report += `出力形式: TypeScript/TSXコード + 使用例\n`;
  report += `\`\`\`\n\n`;
  
  report += `---\n\n`;
  report += `**レポート生成日時**: ${new Date().toLocaleString('ja-JP')}\n`;
  report += `**生成ツール**: generate-ui-audit.ts\n`;
  
  return report;
}

// メイン実行
function main() {
  console.log('UI監査レポートを生成中...');
  
  const report = generateReport();
  const outputDir = path.join(process.cwd(), 'docs', 'ui-audit');
  const outputPath = path.join(outputDir, 'current-ui-report.md');
  
  // ディレクトリが存在しない場合は作成
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }
  
  fs.writeFileSync(outputPath, report, 'utf-8');
  
  console.log(`✅ レポートを生成しました: ${outputPath}`);
  console.log(`📊 レポートサイズ: ${(report.length / 1024).toFixed(2)} KB`);
}

main();
