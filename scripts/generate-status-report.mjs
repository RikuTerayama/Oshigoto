#!/usr/bin/env node
/**
 * ステータスレポートの簡易生成。
 * ルート一覧と製品IDを抽出し、フルレポートの場所を案内する。
 * フル監査は docs/status-reports/2026-02-06_product_ui_and_feature_audit.md を参照。
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, '..');

function extractRoutes(appPath) {
    const content = fs.readFileSync(appPath, 'utf-8');
    const routes = [];
    const re = /@app\.route\(['"]([^'"]+)['"]/g;
    let m;
    while ((m = re.exec(content)) !== null) routes.push(m[1]);
    return routes;
}

function extractProductIds(catalogPath) {
    const content = fs.readFileSync(catalogPath, 'utf-8');
    const ids = [];
    const re = /'id':\s*['"]([^'"]+)['"]/g;
    let m;
    while ((m = re.exec(content)) !== null) ids.push(m[1]);
    return [...new Set(ids)];
}

function main() {
    const appPath = path.join(root, 'app.py');
    const catalogPath = path.join(root, 'lib', 'products_catalog.py');
    const reportPath = path.join(root, 'docs', 'status-reports', '2026-02-06_product_ui_and_feature_audit.md');

    if (!fs.existsSync(appPath) || !fs.existsSync(catalogPath)) {
        console.error('app.py or lib/products_catalog.py not found');
        process.exit(1);
    }

    const routes = extractRoutes(appPath);
    const productIds = extractProductIds(catalogPath);

    const out = {
        generated: new Date().toISOString().slice(0, 10),
        routeCount: routes.length,
        routes: routes.filter(r => !r.startsWith('/health') && !r.startsWith('/live') && !r.startsWith('/ready') && r !== '/ping' && r !== '/test'),
        productIds,
        fullReport: fs.existsSync(reportPath)
            ? 'docs/status-reports/2026-02-06_product_ui_and_feature_audit.md'
            : null,
    };

    console.log(JSON.stringify(out, null, 2));
    if (out.fullReport) {
        console.log('\n# Full audit report: ' + out.fullReport);
    }
}

main();
