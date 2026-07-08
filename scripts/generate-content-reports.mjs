#!/usr/bin/env node
/**
 * Content Reports Generator for AdSense-ready articles.
 * Parses Flask app and products_catalog, emits Markdown to docs/content-reports/.
 * Node built-in only (fs, path). No extra dependencies.
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
const __dirname = path.dirname(fileURLToPath(import.meta.url));

const ROOT = path.resolve(__dirname, '..');
const CATALOG_PATH = path.join(ROOT, 'lib', 'products_catalog.py');
const APP_PATH = path.join(ROOT, 'app.py');
const TEMPLATES_DIR = path.join(ROOT, 'templates');
const OUT_DIR = path.join(ROOT, 'docs', 'content-reports');

// ----- Parse lib/products_catalog.py (PRODUCTS array) -----
function parseProductsCatalog(content) {
  const products = [];
  // Split by product block boundary: "},\n    {" (with possible whitespace)
  const blocks = content.split(/\}\s*,\s*\{/);
  for (const block of blocks) {
    const id = block.match(/'id':\s*'([^']+)'/)?.[1];
    const name = block.match(/'name':\s*'([^']*(?:\\'[^']*)*)'/)?.[1]?.replace(/\\'/g, "'");
    const desc = block.match(/'description':\s*'([^']*(?:\\'[^']*)*)'/)?.[1]?.replace(/\\'/g, "'");
    const pathMatch = block.match(/'path':\s*'([^']+)'/)?.[1];
    if (id && name) {
      products.push({
        id,
        name,
        description: desc || '',
        path: pathMatch || (id === 'autofill' ? '/autofill' : `/tools/${id}`),
      });
    }
  }
  return products;
}

// ----- Parse app.py for route list (optional) -----
function parseRoutes(content) {
  const routes = [];
  const re = /@app\.route\(['"]([^'"]+)['"]/g;
  let m;
  while ((m = re.exec(content)) !== null) routes.push(m[1]);
  return routes;
}

// ----- Extract hints from template HTML -----
function extractTemplateHints(htmlPath) {
  if (!fs.existsSync(htmlPath)) return {};
  const content = fs.readFileSync(htmlPath, 'utf8');
  const hints = {};
  const h1 = content.match(/<h1[^>]*>([^<]+)</)?.[1]?.trim();
  if (h1) hints.h1 = h1;
  const title = content.match(/page_title\s*=\s*'([^']+)'/)?.[1] || content.match(/<title[^>]*>([^<]+)</)?.[1];
  if (title) hints.title = title;
  const desc = content.match(/page_description\s*=\s*'([^']+)'/)?.[1] || content.match(/meta name="description" content="([^"]+)"/)?.[1];
  if (desc) hints.description = desc;
  const infoTexts = [...content.matchAll(/info-text[^>]*>([^<]+)</g)].map((x) => x[1].trim());
  if (infoTexts.length) hints.infoTexts = infoTexts;
  return hints;
}

// ----- Section helpers -----
function section(title, level = 2) {
  const h = '#'.repeat(level);
  return `\n${h} ${title}\n\n`;
}

function ul(items) {
  return items.map((i) => `- ${i}`).join('\n') + '\n\n';
}

// ----- Per-service report (template) -----
function buildServiceReport(product, routes, templateHints) {
  const { id, name, description, path } = product;
  const slug = path.replace(/^\//, '').replace(/\//g, '-') || id;
  let md = section(`${name} コンテンツレポート`, 1);
  md += `- **URL**: \`${path}\`\n`;
  md += `- **ID**: ${id}\n`;
  md += `- **生成元**: lib/products_catalog + templates\n\n`;

  md += section('1. サービス概要（1分で分かる）', 2);
  md += `- **何ができるか**: ${description}\n`;
  md += `- **誰のどんな課題を解決するか**: TODO（業務シーンに合わせて記載）\n`;
  md += `- **競合代替との差分**: TODO（Excel手作業・他ツールとの比較）\n\n`;

  md += section('2. 想定ユーザーと利用シーン', 2);
  md += `- 仕事のユースケース: TODO（EC、社内申請、資料添付、勤怠締め等から選択・追記）\n`;
  md += `- 失敗しがちなポイントと、なぜこのツールが役立つか: TODO\n\n`;

  md += section('3. できること（機能一覧）', 2);
  md += ul([
    description,
    '（詳細は画面・製品カタログの capabilities を参照。TODO: 粒度揃えて列挙）',
  ]);
  md += `v1/v2 の差分: TODO（該当する場合のみ）\n\n`;

  md += section('4. 使い方（手順）', 2);
  md += `- 入力 → 設定 → 実行 → 結果 → ダウンロード の流れで記載\n`;
  md += `- 空状態・失敗時・キャンセル・リセット: TODO\n\n`;

  md += section('5. 入出力仕様', 2);
  md += `- 入力フォーマット・対応拡張子・上限: TODO（テンプレート・静的JSから抽出推奨）\n`;
  md += `- 出力形式: TODO（zip, md, csv, json 等）\n\n`;

  md += section('6. 制約と注意事項（重要）', 2);
  md += `- ブラウザ制約（CORS、メモリ、処理時間等）: TODO\n`;
  md += `- 期待値の調整: TODO\n`;
  md += `- 失敗したときの対処: TODO\n\n`;

  md += section('7. データの取り扱い（AdSenseと信頼性のために必須）', 2);
  md += `- ローカル処理か・アップロード有無: 本ツールは原則ブラウザ内完結（要確認）\n`;
  md += `- 保存の有無・ログの取り扱い: TODO\n\n`;

  md += section('8. よくある質問（FAQ）', 2);
  md += `- 最低8問。実装・運用に即した質問を作成すること。\n`;
  md += `- 例: うまくいかない、遅い、出力が崩れる、対応形式、推奨設定、セキュリティ等\n`;
  md += `- TODO: ここにFAQを8件以上記載\n\n`;

  md += section('9. スクリーンショット計画（撮影指示）', 2);
  md += `- どの画面を撮れば記事が強くなるか: TODO\n`;
  md += `- ファイル名案: 例 \`${id}-01-input.png\`, \`${id}-02-result.png\`\n`;
  md += `- 画像のキャプション案: TODO\n\n`;

  md += section('10. SEO素材（記事化のための素材）', 2);
  md += `- 記事タイトル案（最低5案）: TODO\n`;
  md += `- 想定スラッグ案: 例 \`/guide/${id}\`, \`/tools/${id}\`\n`;
  md += `- メタディスクリプション案: 120〜160文字程度\n`;
  md += `- 見出し構成案（h2/h3の骨子）: TODO\n`;
  md += `- 内部リンク案: このサービス → 他サービス/LP/FAQ/法務 への導線: TODO\n`;
  md += `- 構造化データ候補: FAQPage 想定（実装は別タスク）\n\n`;

  md += section('11. 実装上の根拠（リポジトリ参照）', 2);
  md += `- 該当ページ: \`${path}\` → app.py のルート定義\n`;
  md += `- テンプレート: \`templates/autofill.html\` または \`templates/tools/${id}.html\`\n`;
  md += `- 主要コンポーネント/関数: app.py, static/js/*.js（該当ツール用）\n`;
  md += `- 設定値・上限・プリセット: lib/products_catalog.py または 各HTML/JS 内\n`;
  md += `- エラー表示・注意文: テンプレート内 .info-text, alert 等\n\n`;

  if (templateHints.h1) md += `<!-- 抽出: h1 = ${templateHints.h1} -->\n`;
  if (templateHints.infoTexts?.length) md += `<!-- 抽出: info-text 等 = ${templateHints.infoTexts.slice(0, 3).join(' | ')} -->\n`;

  return md;
}

// ----- 00_master_overview.md -----
function buildMasterOverview(products, routes) {
  let md = section('コンテンツレポート マスター概要', 1);
  md += section('サービス一覧', 2);
  md += `| 名称 | URL | 目的 | 想定記事本数 | 優先度 |\n|------|-----|------|-------------|--------|\n`;
  products.forEach((p, i) => {
    md += `| ${p.name} | ${p.path} | ${p.description.slice(0, 40)}... | 1 | 高 |\n`;
  });
  md += '\n';
  md += section('サイト全体の情報設計', 2);
  md += `- LP（/）→ ツール一覧（/tools）→ 各サービス（/tools/xxx, /autofill）→ ガイド（/guide/xxx）・FAQ（/faq）・法務（/privacy, /terms）の導線\n`;
  md += `- 想定: 1サービス1記事 + ガイドページ + 比較・導入記事\n\n`;
  md += section('AdSense観点の弱点仮説', 2);
  md += ul([
    '薄いページになりやすい: ツール単体ページは「使い方」のみで終わると文字数不足',
    '改善: 各ツールに「よくある質問」「制約」「データ取り扱い」を明示',
    '共通: プライバシー・利用規約・お問い合わせの導線を全ページで統一',
  ]);
  md += section('記事量産のためのテンプレ（本レポート構成）', 2);
  md += ul([
    '1. サービス概要（1分で分かる）',
    '2. 想定ユーザーと利用シーン',
    '3. できること（機能一覧）',
    '4. 使い方（手順）',
    '5. 入出力仕様',
    '6. 制約と注意事項',
    '7. データの取り扱い',
    '8. よくある質問（FAQ）',
    '9. スクリーンショット計画',
    '10. SEO素材',
    '11. 実装上の根拠',
  ]);
  return md;
}

// ----- 99_adsense_readiness_checklist.md -----
function buildAdSenseChecklist() {
  let md = section('AdSense 承認準備チェックリスト', 1);
  md += section('必須ページの有無チェック', 2);
  md += `- [ ] プライバシーポリシー（/privacy）\n`;
  md += `- [ ] 利用規約（/terms）\n`;
  md += `- [ ] お問い合わせ（/contact）\n`;
  md += `- [ ] サイト/運営者情報（About: /about）\n\n`;
  md += section('コンテンツ品質チェック', 2);
  md += `- [ ] 薄いページを避ける（1ページあたり十分な文字数・見出し）\n`;
  md += `- [ ] 重複コンテンツを避ける\n`;
  md += `- [ ] 広告過多・誘導のみにならない\n\n`;
  md += section('ナビと内部リンクの整合', 2);
  md += `- [ ] 全ページからプライバシー・利用規約・お問い合わせへ到達可能\n`;
  md += `- [ ] ツール一覧 ↔ 各ツール ↔ ガイド の双方向リンク\n\n`;
  md += section('画像・引用・著作権の注意', 2);
  md += `- [ ] 画像の利用許諾・出典明記\n`;
  md += `- [ ] 引用の範囲と出典\n\n`;
  md += section('1記事あたりの最低情報量の目安', 2);
  md += `- 見出し数: 目安 5〜10（h2/h3）\n`;
  md += `- FAQ数: 最低 8 問\n`;
  md += `- 画像: 1〜3 枚（スクショ・図解）\n`;
  return md;
}

// ----- Main -----
function main() {
  if (!fs.existsSync(CATALOG_PATH)) {
    console.error('lib/products_catalog.py not found');
    process.exit(1);
  }
  const catalogContent = fs.readFileSync(CATALOG_PATH, 'utf8');
  const products = parseProductsCatalog(catalogContent);

  let appContent = '';
  if (fs.existsSync(APP_PATH)) appContent = fs.readFileSync(APP_PATH, 'utf8');
  const routes = parseRoutes(appContent);

  if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, { recursive: true });

  // 00
  fs.writeFileSync(
    path.join(OUT_DIR, '00_master_overview.md'),
    buildMasterOverview(products, routes),
    'utf8'
  );
  console.log('Wrote 00_master_overview.md');

  // 01_<id>.md
  for (const product of products) {
    const templatePath =
      product.id === 'autofill'
        ? path.join(TEMPLATES_DIR, 'autofill.html')
        : path.join(TEMPLATES_DIR, 'tools', `${product.id}.html`);
    const hints = extractTemplateHints(templatePath);
    const report = buildServiceReport(product, routes, hints);
    const outPath = path.join(OUT_DIR, `01_${product.id}.md`);
    fs.writeFileSync(outPath, report, 'utf8');
    console.log(`Wrote 01_${product.id}.md`);
  }

  // 99
  fs.writeFileSync(
    path.join(OUT_DIR, '99_adsense_readiness_checklist.md'),
    buildAdSenseChecklist(),
    'utf8'
  );
  console.log('Wrote 99_adsense_readiness_checklist.md');

  console.log('Done. Output dir:', OUT_DIR);
}

main();
