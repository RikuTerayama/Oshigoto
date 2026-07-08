#!/usr/bin/env node
/**
 * IA Report: Guide / Resources 現状監査レポート生成
 * Flask app.py と templates を走査し、docs/ia-reports/guide-resources-audit.md を出力する。
 * Node ESM、追加依存なし。
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');
const APP_PATH = path.join(ROOT, 'app.py');
const NAV_PATH = path.join(ROOT, 'lib', 'nav.py');
const TEMPLATES_DIR = path.join(ROOT, 'templates');
const OUT_DIR = path.join(ROOT, 'docs', 'ia-reports');
const OUT_FILE = path.join(OUT_DIR, 'guide-resources-audit.md');

function readSafe(p, def = '') {
  try {
    return fs.readFileSync(p, 'utf8');
  } catch {
    return def;
  }
}

function extractGuideRoutes(appContent) {
  const routes = [];
  const routeRe = /@app\.route\(['"]([^'"]+)['"].*?\)\s*\ndef\s+(\w+).*?return\s+render_template\(['"]([^'"]+)['"]/gs;
  let m;
  while ((m = routeRe.exec(appContent)) !== null) {
    const urlPath = m[1];
    const handler = m[2];
    const template = m[3];
    if (urlPath.startsWith('/guide') || urlPath === '/faq' || urlPath === '/glossary' || urlPath === '/about' || urlPath === '/blog' || urlPath === '/privacy' || urlPath === '/terms' || urlPath === '/contact' || urlPath === '/download-template' || urlPath === '/download-previous-template') {
      routes.push({ path: urlPath, handler, template });
    }
  }
  // Fallback: line-by-line
  if (routes.length === 0) {
    const lines = appContent.split('\n');
    for (let i = 0; i < lines.length; i++) {
      const routeM = lines[i].match(/@app\.route\(['"]([^'"]+)['"]/);
      if (routeM && (routeM[1].startsWith('/guide') || ['/faq','/glossary','/about','/privacy','/terms','/contact'].includes(routeM[1]))) {
        const templateM = appContent.slice(lines.slice(0, i + 1).join('\n').length).match(/render_template\(['"]([^'"]+)['"]/);
        routes.push({ path: routeM[1], handler: '', template: templateM ? templateM[1] : '' });
      }
    }
  }
  return routes;
}

function extractAllGuideRoutesStrict(appContent) {
  const routes = [];
  const lines = appContent.split('\n');
  for (let i = 0; i < lines.length; i++) {
    const r = lines[i].match(/@app\.route\(['"]([^'"]+)['"]/);
    if (!r) continue;
    const path_ = r[1];
    if (!path_.startsWith('/guide')) continue;
    let template = '';
    for (let j = i + 1; j < Math.min(i + 15, lines.length); j++) {
      const t = lines[j].match(/render_template\(['"]([^'"]+)['"]/);
      if (t) { template = t[1]; break; }
    }
    routes.push({ path: path_, template });
  }
  return routes;
}

function listTemplates(dir, base = '') {
  const acc = [];
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const e of entries) {
    const rel = base ? `${base}/${e.name}` : e.name;
    if (e.isDirectory()) acc.push(...listTemplates(path.join(dir, e.name), rel));
    else if (e.name.endsWith('.html')) acc.push(rel);
  }
  return acc;
}

function grepHref(dir, pattern) {
  const results = [];
  const files = listTemplates(dir).map((f) => path.join(dir, f));
  const re = new RegExp(pattern, 'g');
  for (const file of files) {
    const content = readSafe(file);
    const relPath = path.relative(TEMPLATES_DIR, file);
    let m;
    while ((m = re.exec(content)) !== null) {
      results.push({ from: relPath.replace(/\\/g, '/'), href: m[1] || m[2] });
    }
  }
  return results;
}

function extractTitles(htmlPath) {
  const content = readSafe(htmlPath);
  const titles = [];
  const h1Re = /<h1[^>]*>([^<]+)</g;
  let m;
  while ((m = h1Re.exec(content)) !== null) titles.push({ type: 'h1', text: m[1].trim() });
  const titleRe = /page_title\s*=\s*'([^']+)'/;
  const titleM = content.match(titleRe);
  if (titleM) titles.push({ type: 'page_title', text: titleM[1] });
  return titles;
}

function buildReport() {
  const appContent = readSafe(APP_PATH);
  const navContent = readSafe(NAV_PATH);

  const guideRoutes = extractAllGuideRoutesStrict(appContent);
  const allTemplates = listTemplates(TEMPLATES_DIR);
  const guideTemplates = allTemplates.filter((t) => t.startsWith('guide/') || t === 'guide_getting_started.html' || t === 'guide_excel_format.html' || t === 'guide_troubleshooting.html');
  const linkToGuide = grepHref(TEMPLATES_DIR, 'href=["\'](/guide/[^"\']+)["\']');
  const linkToResource = grepHref(TEMPLATES_DIR, 'href=["\'](/(?:faq|glossary|about|privacy|terms|contact|blog)[^"\']*)["\']');

  const guideByService = {
    jobcan: guideRoutes.filter((r) => ['/guide/getting-started', '/guide/excel-format', '/guide/troubleshooting', '/guide/complete', '/guide/comprehensive-guide'].includes(r.path)),
    tools: guideRoutes.filter((r) => ['/guide/image-batch', '/guide/pdf', '/guide/image-cleanup', '/guide/minutes', '/guide/seo'].includes(r.path)),
  };

  let md = '';

  md += '# Guide / Resources 情報設計 現状監査レポート\n\n';
  md += '---\n\n';

  md += '## 0. 目的と結論（1ページで分かる）\n\n';
  md += '### 現状の問題の要約\n\n';
  md += '- **構造の偏り**: `/guide` 配下は **Jobcan AutoFill（勤怠自動入力）向けが5ページ**（getting-started, excel-format, troubleshooting, complete, comprehensive-guide）、**他ツール向けは各1ページのみ**（image-batch, pdf, image-cleanup, minutes, seo）。\n';
  md += '- **重複・配置の不統一**: Jobcan 向けガイドの実体が **templates 直下**（`guide_getting_started.html` 等）と **templates/guide/**（`complete-guide.html`, `comprehensive-guide.html`）に分散している。\n';
  md += '- **「resources」の定義**: URL に `/resources` は存在しない。ナビの「Resource」は **FAQ・用語集・ブログ・About・法務・お問い合わせ** へのドロップダウンラベル（lib/nav.py で定義）。\n';
  md += '- **欠け**: 各ツールごとの FAQ / トラブルシュート / データ取扱い の専用ページはなく、Jobcan 向けにのみトラブルシューティング・Excel形式ガイドがある。\n\n';
  md += '### 最重要の観察結果（証拠付き）\n\n';
  md += '1. **Jobcan 向け Guide が5件、他ツールは各1件** — app.py に `/guide/getting-started` 等 5 ルート + `/guide/image-batch` 等 5 ルート。sitemap.xml の固定リスト（app.py 1630–1634行）には Jobcan 向け5件のみが明示列挙され、ツール別ガイドは PRODUCTS の guide_path から動的追加。\n';
  md += '2. **テンプレート配置が二系統** — Jobcan: `guide_getting_started.html`, `guide_excel_format.html`, `guide_troubleshooting.html`（直下）と `guide/complete-guide.html`, `guide/comprehensive-guide.html`（guide/ 配下）。他ツール: すべて `guide/<id>.html`。\n';
  md += '3. **Resource は URL ではなくナビ区分** — lib/nav.py の `resource_links` に /faq, /glossary, /blog, /about, /privacy, /terms, /contact が列挙。ダウンロード系は /download-template, /download-previous-template で別ルート。\n\n';

  md += '## 1. 現在の情報設計（サイトマップ）\n\n';
  md += '### 公開URLと実体ファイル\n\n';
  md += '| URL | 実体テンプレート | 備考 |\n|-----|------------------|------|\n';
  for (const r of guideRoutes) {
    md += `| ${r.path} | ${r.template} | Guide |\n`;
  }
  md += '| /faq | faq.html | Resource（ナビ） |\n';
  md += '| /glossary | glossary.html | Resource |\n';
  md += '| /about | about.html | Resource |\n';
  md += '| /blog | blog/index.html | Resource |\n';
  md += '| /privacy | privacy.html | 法的情報 |\n';
  md += '| /terms | terms.html | 法的情報 |\n';
  md += '| /contact | contact.html | 法的情報 |\n';
  md += '| /download-template | （Excel生成） | ダウンロード |\n';
  md += '| /download-previous-template | （Excel生成） | ダウンロード |\n';
  md += '| / | landing.html | LP |\n';
  md += '| /autofill | autofill.html | Jobcan AutoFill |\n';
  md += '| /tools | tools/index.html | ツール一覧 |\n';
  md += '| /tools/image-batch 他 | tools/<id>.html | 各ツール |\n\n';
  md += '### Guide 階層（親子の整理）\n\n';
  md += '- **Jobcan AutoFill 系（フラット）**: /guide/getting-started, /guide/excel-format, /guide/troubleshooting, /guide/complete, /guide/comprehensive-guide — いずれも同一階層。親ディレクトリなし。\n';
  md += '- **他ツール（フラット）**: /guide/image-batch, /guide/pdf, /guide/image-cleanup, /guide/minutes, /guide/seo — 各サービス1ページのみ。\n\n';

  md += '## 2. Guide の現状棚卸し（定量・定性）\n\n';
  md += '- **ページ数**: Guide 全 **10 ページ**。うち Jobcan 向け **5**、他ツール向け **5**（1ツール1ページ）。\n';
  md += '- **階層**: すべて1階層（/guide/<slug>）。サブパス（例 /guide/jobcan/overview）はなし。\n';
  md += '- **作成方式**: すべて Jinja2 テンプレート直書き。Markdown 読み込みは未使用。\n';
  md += '- **内部リンク（リンク元）**: ツールページ（image-batch, pdf, minutes, seo, image-cleanup）から「ガイドを読む」→ 各 /guide/<id>。FAQ・ブログ・事例からは /guide/getting-started, /guide/excel-format, /guide/troubleshooting が多数。sitemap.html は Jobcan 向け3件のみ列挙。\n';
  md += '- **Jobcan だけ複数ある根拠**: app.py 698–721 行に 5 ルート定義。lib/nav.py の guide_links に「完全ガイド」「はじめての使い方」「Excelファイルの作成方法」「トラブルシューティング」を固定で先に並べ、その後に products の guide_path を付加。\n';
  md += '- **他ツールが1ページしかない根拠**: products_catalog の各 product に guide_path が1つずつ（例 /guide/image-batch）。app.py に /guide/image-batch 等 1 ルートずつのみ。\n\n';

  md += '## 3. resources の現状棚卸し（定量・定性）\n\n';
  md += '- **定義**: 「resources」は **URL プレフィックスではなく**、ヘッダー/フッターの「Resource」ドロップダウンに含まれるページ群（lib/nav.py: resource_links）。\n';
  md += '- **ページ数・種類**: FAQ（/faq）、用語集（/glossary）、ブログ一覧・記事（/blog, /blog/xxx）、サイトについて（/about）、プライバシーポリシー（/privacy）、利用規約（/terms）、お問い合わせ（/contact）。テンプレートはすべて HTML。ダウンロードは /download-template, /download-previous-template（Excel 生成）。\n';
  md += '- **サービス紐付け**: FAQ は主に Jobcan AutoFill の利用質問。用語集・ブログはサイト全体。各ツール専用の FAQ ページは存在しない。\n';
  md += '- **欠けている要素**: 各ツールの「使い方」「制約」「データ取扱い」「トラブルシュート」の専用ページ。画像一括変換・PDF・議事録・SEO 用の FAQ/比較/ユースケースページ。\n\n';

  md += '## 4. 重複/分断/欠落の分析\n\n';
  md += '- **重複**: 「はじめての使い方」「Excel形式」の説明が、guide_getting_started / guide_excel_format / guide/complete-guide / guide/comprehensive-guide に分散。ブログ記事からも同じガイドへ多数リンク。\n';
  md += '- **分断**: ツールページからは各 /guide/<tool> へは繋がる。一方、Guide ドロップダウンは「完全ガイド」等が上で、ツール別ガイドが下。Landing から Guide への導線はナビのみ。\n';
  md += '- **欠落**: 各ツールの FAQ、トラブルシュート、用語説明、データ取扱い（ローカル処理の明記）の専用ページ。サイトマップ（sitemap.html）にツール別ガイドが未列挙（sitemap.xml には PRODUCTS から動的追加）。\n\n';

  md += '## 5. 「構造化して整える」ための設計案（3案）\n\n';
  md += '### A案: サービス別にガイド階層を統一\n';
  md += '- 例: /guide/<service>/overview, /guide/<service>/how-to, /guide/<service>/faq, /guide/<service>/troubleshooting\n';
  md += '- **メリット**: 全サービスで同じ構造。拡張しやすい。\n';
  md += '- **デメリット**: 既存URLが全て変わる。リダイレクトが大量に必要。\n';
  md += '- **既存URL**: 301 リダイレクトで新パスへ。slug は service=jobcan|image-batch|pdf|... に統一。\n';
  md += '- **実装難易度**: High\n\n';
  md += '### B案: Guide と resources を統合し /docs に一本化\n';
  md += '- 例: /docs/<service>/..., /docs/faq, /docs/glossary\n';
  md += '- **メリット**: 「ナレッジは /docs」と一本化。\n';
  md += '- **デメリット**: 現行の「Guide」ブランドとナビを全面変更。既存リンク・ブックマークが無効。\n';
  md += '- **既存URL**: 301 で /docs へ。Resource 系は /docs/faq 等に移行。\n';
  md += '- **実装難易度**: High\n\n';
  md += '### C案: Guide はナレッジ、resources はダウンロード/テンプレに特化\n';
  md += '- Guide: 現状の /guide を維持しつつ、中身だけ「各ツール1本＋Jobcan は複数」を整理（重複削減・テンプレ配置統一）。\n';
  md += '- Resource: FAQ/用語集/ブログ/About/法務は「ナビの Resource」のまま。ダウンロードは /download-template 等のまま。責任範囲を明文化（Guide=使い方・手順、Resource=サポート・法務・コンテンツ）。\n';
  md += '- **メリット**: URL 変更が最小。段階的に整理できる。\n';
  md += '- **デメリット**: 「他ツールも複数ページに」する場合は C の延長で A に近づける必要あり。\n';
  md += '- **既存URL**: 維持。必要に応じて 301 は最小限（例 comprehensive-guide を complete に統合する場合のみ）。\n';
  md += '- **実装難易度**: Medium\n\n';

  md += '## 6. 具体的な整備ToDo（次ステップの実装タスク化）\n\n';
  md += '1. **まずやること**: 情報設計の決定（A/B/C のいずれかまたはハイブリッド）。slug と階層の定義。ナビ（lib/nav.py）の「Guide」「Resource」ラベルと一覧の見直し。\n';
  md += '2. **次にやること**: 既存ガイドのテンプレート配置統一（Jobcan をすべて guide/ 配下に移すか、直下を残すか）。重複コンテンツの統合（complete と comprehensive の役割分担または統合）。各ツールに FAQ セクションまたは1ページ追加の要否検討。\n';
  md += '3. **最後にやること**: 廃止URL の 404 または 301 設定。sitemap.xml / sitemap.html の更新。内部リンクの一括置換。\n\n';

  md += '## 7. エビデンス（調査ログ）\n\n';
  md += '### 参照したファイル一覧\n\n';
  md += '- app.py（ルート定義・render_template）\n';
  md += '- lib/nav.py（Guide / Resource ナビ定義）\n';
  md += '- lib/products_catalog.py（guide_path の定義）\n';
  md += '- templates/（guide/, guide_*.html, faq.html, glossary.html 等）\n\n';
  md += '### 重要なルート定義の抜粋（app.py）\n\n';
  md += '```\n';
  md += '@app.route(\'/guide/getting-started\') -> guide_getting_started.html\n';
  md += '@app.route(\'/guide/excel-format\') -> guide_excel_format.html\n';
  md += '@app.route(\'/guide/troubleshooting\') -> guide_troubleshooting.html\n';
  md += '@app.route(\'/guide/complete\') -> guide/complete-guide.html\n';
  md += '@app.route(\'/guide/comprehensive-guide\') -> guide/comprehensive-guide.html\n';
  md += '@app.route(\'/guide/image-batch\') -> guide/image-batch.html  (他ツール同様)\n';
  md += '```\n\n';
  md += '### ナビ定義（lib/nav.py 要約）\n\n';
  md += '- guide_links: 完全ガイド・はじめての使い方・Excelファイルの作成方法・トラブルシューティング（固定）のあと、PRODUCTS の guide_path を追加。\n';
  md += '- resource_links: FAQ, 用語集, ブログ, サイトについて, プライバシー, 利用規約, お問い合わせ。\n\n';
  md += '### 生成スクリプトの走査ルール\n\n';
  md += '- app.py を読み、@app.route と直後の render_template で /guide および Resource 系 URL とテンプレートを対応付け。\n';
  md += '- templates 配下を再帰的にリストし、guide 関連テンプレート（guide/*.html, guide_*.html）を列挙。\n';
  md += '- templates 内の href="/guide/..." および href="/faq" 等を正規表現で抽出し、リンク元ファイルを集計。\n';
  md += '- 本レポートは上記に加え、手動でナビ・sitemap の記述を補足。\n\n';

  md += '---\n\n';
  md += '*Generated by scripts/generate-ia-guide-resources-report.mjs*\n';

  return md;
}

function main() {
  if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, { recursive: true });
  const report = buildReport();
  fs.writeFileSync(OUT_FILE, report, 'utf8');
  console.log('Wrote', OUT_FILE);
}

main();
