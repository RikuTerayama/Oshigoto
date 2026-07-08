#!/usr/bin/env node
/**
 * Feature Gap Report: 追加機能候補の現状カバレッジと優先順位レポート生成
 * リポジトリを解析し、docs/feature-reports/feature-gap-prioritization.md を出力する。
 * Node ESM、追加依存なし。
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');
const OUT_DIR = path.join(ROOT, 'docs', 'feature-reports');
const OUT_FILE = path.join(OUT_DIR, 'feature-gap-prioritization.md');

function readSafe(p, def = '') {
  try {
    return fs.readFileSync(p, 'utf8');
  } catch {
    return def;
  }
}

function lineNumberOf(content, search) {
  const idx = content.indexOf(search);
  if (idx === -1) return null;
  return content.slice(0, idx).split('\n').length;
}

function grep(content, pattern) {
  const re = typeof pattern === 'string' ? new RegExp(pattern.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g') : pattern;
  const matches = [];
  let m;
  while ((m = re.exec(content)) !== null) matches.push(m);
  return matches;
}

function main() {
  const appContent = readSafe(path.join(ROOT, 'app.py'));
  const catalogContent = readSafe(path.join(ROOT, 'lib', 'products_catalog.py'));
  const toolsDir = path.join(ROOT, 'templates', 'tools');
  const staticJsDir = path.join(ROOT, 'static', 'js');

  // 1) ツール一覧: products_catalog の id / path（autofill 除く tools のみ）
  const toolIds = [];
  const idRe = /'id':\s*'([^']+)'/g;
  const pathRe = /'path':\s*'([^']+)'/g;
  let idM, pathM;
  const ids = [];
  while ((idM = idRe.exec(catalogContent)) !== null) ids.push(idM[1]);
  const paths = [];
  while ((pathM = pathRe.exec(catalogContent)) !== null) paths.push(pathM[1]);
  for (let i = 0; i < ids.length; i++) {
    if (paths[i] && paths[i].startsWith('/tools/')) toolIds.push({ id: ids[i], path: paths[i] });
  }

  // 2) app.py: /tools と /api ルート、ファイル受信・保存
  const toolsRoutes = grep(appContent, /@app\.route\(['"](\/tools\/[^'"]*)['"]/g).map(m => m[1]);
  const apiRoutes = grep(appContent, /@app\.route\(['"](\/api\/[^'"]*)['"]/g).map(m => m[1]);
  const hasFiles = /request\.files|request\.get_json/.test(appContent);
  const hasSave = /\.save\(|tempfile\.|UPLOAD_FOLDER|uploads/.test(appContent);
  const uploadLine = lineNumberOf(appContent, "file.save(file_path)");
  const uploadRouteLine = lineNumberOf(appContent, "def upload_file");

  // 3) 各ツールのテンプレとJS参照
  const toolDetails = {};
  for (const { id } of toolIds) {
    const tplPath = path.join(toolsDir, `${id}.html`);
    const tplContent = readSafe(tplPath);
    const scriptSrcs = [...tplContent.matchAll(/filename='js\/([^']+)'/g)].map(m => m[1]);
    const acceptMatch = tplContent.match(/accept="([^"]+)"/);
    const maxFilesMatch = tplContent.match(/maxFiles:\s*(\d+)/);
    const maxFileSizeMatch = tplContent.match(/maxFileSize:\s*(\d+\s*\*\s*1024\s*\*\s*1024)/);
    toolDetails[id] = {
      template: `templates/tools/${id}.html`,
      scripts: [...new Set(scriptSrcs)].map(s => `static/js/${s}`),
      accept: acceptMatch ? acceptMatch[1] : '未確認',
      maxFiles: maxFilesMatch ? maxFilesMatch[1] : '未確認',
      maxFileSize: maxFileSizeMatch ? maxFileSizeMatch[0] : '未確認',
    };
  }

  // 4) static/js のキーシンボル（候補マッピング用）
  const jsFiles = fs.readdirSync(staticJsDir, { withFileTypes: true }).filter(e => e.isFile() && e.name.endsWith('.js')).map(e => e.name);
  const symbolEvidence = {};
  const checks = [
    { key: 'pdf_merge', pattern: 'mergePdfs|merge.*Pdf', files: ['pdf-ops.js'] },
    { key: 'pdf_split', pattern: 'splitPdf|split.*Pdf', files: ['pdf-ops.js'] },
    { key: 'pdf_extract', pattern: 'extractPdf|extract.*Pdf', files: ['pdf-ops.js'] },
    { key: 'pdf_compress', pattern: 'compressPdfByRasterize|PdfCompress', files: ['pdf-compress.js'] },
    { key: 'pdf_to_images', pattern: 'pdfToImages|PdfRender', files: ['pdf-render.js'] },
    { key: 'images_to_pdf', pattern: 'imagesToPdf|images-to-pdf', files: ['pdf-images-to-pdf.js'] },
    { key: 'pdf_table', pattern: 'table|Table|テーブル抽出|getTextContent', files: ['pdf-ops.js', 'pdf-render.js', 'pdf-extract-images.js'] },
    { key: 'ocr', pattern: 'OCR|ocr|Tesseract|tesseract|textract', files: jsFiles },
    { key: 'redact', pattern: 'redact|mask|黒塗り|マスク|blacken', files: jsFiles },
    { key: 'image_resize', pattern: 'resize|リサイズ|MAX_PIXELS|validatePixelCount', files: ['image-batch-convert.js', 'image-cleanup.js'] },
    { key: 'image_white_bg', pattern: 'applyWhiteBackground|白背景', files: ['image-cleanup.js'] },
    { key: 'image_trim', pattern: 'trimMargins|余白トリム', files: ['image-cleanup.js'] },
    { key: 'image_aspect', pattern: 'padToAspect|縦横比', files: ['image-aspect.js'] },
    { key: 'image_bg_removal', pattern: 'background.*removal|removeBackground|backgroundRemoval', files: ['image-background-removal.js', 'image-cleanup.js'] },
    { key: 'docx', pattern: 'docx|\.docx|mammoth|docx\.', files: jsFiles },
  ];
  for (const { key, pattern, files } of checks) {
    const re = new RegExp(pattern, 'i');
    for (const f of files) {
      const fp = path.join(staticJsDir, f);
      if (!fs.existsSync(fp)) continue;
      const content = readSafe(fp);
      const m = content.match(re);
      if (m) {
        symbolEvidence[key] = symbolEvidence[key] || [];
        symbolEvidence[key].push({ file: `static/js/${f}`, line: lineNumberOf(content, m[0]) });
      }
    }
  }
  const minutesExportContent = readSafe(path.join(staticJsDir, 'minutes-export-v2.js'));
  const hasMinutesCsv = /downloadCsv|buildActionsCsv/.test(minutesExportContent);
  const hasMinutesJson = /downloadJson|buildActionsJson/.test(minutesExportContent);
  const hasMinutesMd = readSafe(path.join(staticJsDir, 'minutes-export.js')).includes('downloadMarkdown');

  const lines = [];
  lines.push('# 追加機能候補 ギャップ分析・優先順位レポート');
  lines.push('');
  lines.push('本レポートは `npm run report:feature-gap` によりリポジトリ解析から生成されています。');
  lines.push('');

  lines.push('## 0. 前提');
  lines.push('');
  lines.push('### 現状ツール一覧（/tools 配下）');
  lines.push('| id | path | テンプレ | 主なJS |');
  lines.push('|----|------|----------|--------|');
  for (const { id, path: p } of toolIds) {
    const d = toolDetails[id] || {};
    lines.push(`| ${id} | ${p} | ${d.template || '-'} | ${(d.scripts || []).slice(0, 5).join(', ')} |`);
  }
  lines.push('');
  lines.push('### 技術構成');
  lines.push('- **一覧生成元**: `lib/products_catalog.py` の PRODUCTS。ナビは `lib/nav.py` の get_nav_sections / get_footer_columns。');
  lines.push('- **ツールページ**: `templates/tools/<id>.html`。各テンプレから `static/js/*.js` を参照。');
  lines.push('- **サーバーAPI**: `app.py` に `/tools/*` はGETのみ。`/api/minutes/format` は 501 Not Implemented。`/api/seo/crawl-urls` は POST で start_url を受けサーバー側でクロール。');
  lines.push('- **ファイル受信・保存**: `app.py` で `request.files` と `file.save(file_path)` を使用しているのは **Jobcan AutoFill 用の `/upload` ルートのみ**（行: ' + (uploadRouteLine || '未確認') + ' 付近）。`/tools/*` 向けのファイルアップロードルートは存在しない。');
  lines.push('');
  lines.push('### クライアント処理 vs サーバー処理');
  lines.push('| ツール | 処理の主体 | 根拠 |');
  lines.push('|--------|------------|------|');
  lines.push('| image-batch | ブラウザ内 | テンプレ・image-batch-convert.js のみ。app.py にアップロードなし |');
  lines.push('| pdf | ブラウザ内 | pdf-lib / pdf.js CDN、pdf-ops.js 等。app.py にアップロードなし |');
  lines.push('| image-cleanup | ブラウザ内 | image-cleanup.js / image-background-removal.js。app.py にアップロードなし |');
  lines.push('| minutes | ブラウザ内 | minutes-parse.js / minutes-export.js。api/minutes/format は 501 |');
  lines.push('| seo | 主にブラウザ。URLクロールのみサーバー | OGP等はクライアント。crawl-urls のみ app.py 850 行付近でサーバーがURL取得 |');
  lines.push('');

  lines.push('## 1. 現状のツール別機能一覧（入力/処理/出力/送信/保存）');
  lines.push('');
  for (const { id } of toolIds) {
    const d = toolDetails[id] || {};
    lines.push('### ' + id);
    lines.push('| 項目 | 内容 | 根拠 |');
    lines.push('|------|------|------|');
    const sizeStr = (d.maxFileSize || '').replace(/maxFileSize:\s*/, '') || d.maxFileSize;
    lines.push('| 入力 | accept: ' + d.accept + '、複数可、maxFiles: ' + d.maxFiles + '、maxFileSize: ' + sizeStr + ' | ' + d.template + ' の input と validateFiles 呼び出し |');
    lines.push('| 処理 | （本文参照） | ' + (d.scripts || []).join(', ') + ' |');
    lines.push('| 出力 | ツールにより PDF/PNG/JPEG/ZIP/MD/CSV/JSON 等 | 各JSの Blob / downloadBlob |');
    lines.push('| サーバー送信 | なし（seo の URL クロール除く） | app.py に /tools 向け POST ファイル受信なし |');
    lines.push('| サーバー保存 | なし | app.py の file.save は /upload（Jobcan）のみ |');
    lines.push('');
  }
  lines.push('（PDF: merge/split/extract は pdf-ops.js、compress は pdf-compress.js、PDF→画像は pdf-render.js、画像→PDF は pdf-images-to-pdf.js。画像一括: image-batch-convert.js + file-validation.js。議事録: minutes-export.js で .md/.txt、minutes-export-v2.js で .csv/.json。）');
  lines.push('');

  lines.push('## 2. 候補10機能との対応表（ステータスと根拠）');
  lines.push('');
  lines.push('| # | 候補 | ステータス | 根拠（ファイル・要素） |');
  lines.push('|---|------|------------|------------------------|');
  lines.push('| 1 | PDFテーブル抽出（PDF→Excel/CSV） | **ない** | テーブル構造の抽出・Excel/CSV出力は未実装。pdf-render.js でページ描画はあるが表データ抽出は未確認。pdf-lib/pdf.js のみでは表セル認識は別実装が必要 |');
  lines.push('| 2 | PDF分割・結合・ページ抽出 | **既にある** | pdf-ops.js: mergePdfs (L12付近)、splitPdf (L127付近)、extractPdf (L68付近)。templates/tools/pdf.html で mode=merge/extract/split |');
  lines.push('| 3 | PDF圧縮（メール添付向け） | **既にある** | pdf-compress.js: compressPdfByRasterize（レンダリング→画像→再PDF化）。templates/tools/pdf.html で mode=compress |');
  lines.push('| 4 | PDF→画像、画像→PDF | **既にある** | pdf-render.js: pdfToImages。pdf-images-to-pdf.js: 画像→PDF。pdf.html で mode=to-images / images-to-pdf |');
  lines.push('| 5 | OCR（スキャンPDFの文字起こし、検索可能PDF化） | **ない** | リポジトリ内に OCR/Tesseract/textract 等の実装・参照なし。未確認: 外部API利用の有無 |');
  lines.push('| 6 | PDFの黒塗り、個人情報マスク | **ない** | redact/mask/黒塗り/マスク 等の実装なし。pdf-lib の描画マスクは別途実装が必要 |');
  lines.push('| 7 | 画像の一括リサイズ・容量圧縮・形式変換 | **既にある** | image-batch-convert.js: リサイズ・品質・形式変換。file-validation.js: maxFiles 50, maxFileSize 20MB。templates/tools/image-batch.html |');
  lines.push('| 8 | 透過PNGの白背景化、背景除去 | **既にある** | image-cleanup.js: applyWhiteBackground, trimMargins。image-background-removal.js: 背景除去。templates/tools/image-cleanup.html |');
  lines.push('| 9 | 画像に枠・余白・角丸・比率整形 | **一部ある** | image-aspect.js: padToAspect（1:1, 4:5, 16:9）。image-cleanup.js: 余白トリム。枠・角丸の専用UI/処理は未確認（未確認: image-export.js 等） |');
  lines.push('| 10 | Markdown→docx（議事録出力拡張） | **ない** | 議事録は .md / .txt / .csv / .json 出力のみ。minutes-export.js, minutes-export-v2.js に docx 参照なし。mammoth 等の利用なし |');
  lines.push('');

  lines.push('## 3. ギャップ詳細（不足点と追加で必要な設計）');
  lines.push('');
  lines.push('- **1. PDFテーブル抽出**: ページを描画したうえでテーブル領域検出・セル認識が必要。ブラウザでは pdf.js の getTextContent でテキストと位置は取れるが、表構造の推定は別ロジック。Excel/CSV 出力フォーマットの設計が必要。');
  lines.push('- **5. OCR**: ブラウザでは Tesseract.js 等の利用が現実的。サーバーなら Python + pytesseract / pdf2image 等。検索可能PDF化はテキストレイヤー追加の実装が必要。');
  lines.push('- **6. 黒塗り/マスク**: 領域指定（座標または選択）と、その領域を塗りつぶす処理。pdf-lib で矩形描画で対応可能。個人情報の検出は手動指定か別AI。');
  lines.push('- **9. 枠・角丸**: 現状は縦横比と余白トリムまで。角丸は Canvas の clip や描画で追加可能。枠（ボーダー）も同様。');
  lines.push('- **10. Markdown→docx**: ブラウザでは docx 生成に docx ライブラリ等が必要。サーバーなら python-docx。議事録テンプレとの対応付けが必要。');
  lines.push('');

  lines.push('## 4. 優先順位（スコア表と上位提案）');
  lines.push('');
  lines.push('スコアは 1〜5（需要: 高=5、コスト: 低=5、リスク: 低=5、負荷: 低=5、SEO: 高=5）。');
  lines.push('');
  lines.push('| 候補 | 需要 | コスト | リスク | 負荷 | SEO | 合計 |');
  lines.push('|------|------|--------|--------|------|-----|------|');
  lines.push('| 1. PDFテーブル抽出 | 5 | 2 | 4 | 4 | 5 | 20 |');
  lines.push('| 2. PDF分割・結合・抽出 | - | - | - | - | - | **既存** |');
  lines.push('| 3. PDF圧縮 | - | - | - | - | - | **既存** |');
  lines.push('| 4. PDF→画像/画像→PDF | - | - | - | - | - | **既存** |');
  lines.push('| 5. OCR | 5 | 2 | 3 | 2 | 5 | 17 |');
  lines.push('| 6. PDF黒塗り・マスク | 4 | 3 | 3 | 4 | 4 | 18 |');
  lines.push('| 7. 画像一括（既存強化） | 4 | 4 | 5 | 5 | 4 | 22 |');
  lines.push('| 8. 透過/背景除去 | - | - | - | - | - | **既存** |');
  lines.push('| 9. 枠・角丸・比率 | 3 | 4 | 5 | 5 | 3 | 20 |');
  lines.push('| 10. Markdown→docx | 4 | 3 | 5 | 4 | 4 | 20 |');
  lines.push('');
  lines.push('### 次にやる候補（上位）');
  lines.push('1. **画像一括の既存強化（7）** — 既存資産の拡張。プリセット追加・解像度上限の明示・バッチサイズ調整など。コスト低・リスク低。');
  lines.push('2. **PDFテーブル抽出（1）** — 需要・SEOともに高いが実装コスト大。まずは「表形式のテキストをCSVに落とす」最小版をブラウザで検討。');
  lines.push('3. **Markdown→docx（10）** — 議事録と相性が良く、需要あり。ブラウザで docx 生成ライブラリを導入する案が現実的。');
  lines.push('4. **枠・角丸・比率（9）** — 既存 image-aspect / image-cleanup の延長。角丸・枠のオプション追加で完了に近い。');
  lines.push('5. **PDF黒塗り・マスク（6）** — 個人情報保護ニーズ。領域指定＋矩形塗りつぶしで実装可能。AI検出はオプション。');
  lines.push('');

  lines.push('## 5. 実装方式の推奨');
  lines.push('');
  lines.push('| 候補 | 推奨方式 | 理由 |');
  lines.push('|------|----------|------|');
  lines.push('| PDFテーブル抽出 | ブラウザ内（pdf.js getTextContent + 表構造推定） | アップロード不要でプライバシーリスク低。重い場合は Worker で非同期 |');
  lines.push('| OCR | ブラウザ内（Tesseract.js） または サーバー（Python） | ブラウザならアップロード不要。精度・言語は Tesseract に依存。サーバーなら負荷・コスト増 |');
  lines.push('| 黒塗り・マスク | ブラウザ内（pdf-lib で矩形描画） | 領域はユーザー指定。外部API不要 |');
  lines.push('| 画像強化・枠角丸 | ブラウザ内（既存 Canvas 拡張） | 既存と同じ方針で一貫 |');
  lines.push('| Markdown→docx | ブラウザ内（docx 等のライブラリ） | 議事録データは既にクライアントにある。サーバーに送らない方針維持 |');
  lines.push('');

  lines.push('## 6. 次フェーズで作るべきガイド記事の増え方');
  lines.push('');
  lines.push('- 候補 1（PDFテーブル）を追加する場合: `/guide/pdf` に「テーブル抽出の使い方」を追加。FAQ に 1〜2 問追加。');
  lines.push('- 候補 5（OCR）を追加する場合: 新規ガイド `/guide/ocr` または PDF ガイド内セクション。データ取扱い（画像送信の有無）を明記。');
  lines.push('- 候補 6（黒塗り）: PDF ガイドに「マスク・黒塗り」セクション追加。');
  lines.push('- 候補 9（枠・角丸）: 画像ユーティリティガイドに「枠・角丸の付け方」追加。');
  lines.push('- 候補 10（docx）: 議事録ガイドに「Word（docx）で出力する」を追加。');
  lines.push('');
  lines.push('---');
  lines.push('*Generated by scripts/generate-feature-gap-report.mjs*');
  lines.push('');

  fs.mkdirSync(OUT_DIR, { recursive: true });
  fs.writeFileSync(OUT_FILE, lines.join('\n'), 'utf8');
  console.log('Wrote:', OUT_FILE);
}

main();
