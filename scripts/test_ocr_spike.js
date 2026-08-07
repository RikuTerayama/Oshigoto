'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const read = (relativePath) => fs.readFileSync(path.join(root, relativePath), 'utf8');
const publicFiles = [
    'app.py',
    'lib/products_catalog.py',
    'lib/nav.py',
    'lib/seo.py',
    'templates/landing.html',
    'templates/tools/index.html',
    'templates/guide/index.html',
];

for (const relativePath of publicFiles) {
    const source = read(relativePath).toLowerCase();
    assert.equal(source.includes('/tools/ocr'), false, `${relativePath} must not publish /tools/ocr`);
    assert.equal(source.includes('/guide/ocr'), false, `${relativePath} must not publish /guide/ocr`);
    assert.equal(source.includes('/api/ocr'), false, `${relativePath} must not publish /api/ocr`);
}

assert.equal(fs.existsSync(path.join(root, 'static', 'vendor', 'tesseract')), false, 'No-Go commit must not retain Tesseract assets');
assert.equal(fs.existsSync(path.join(root, 'templates', 'internal', 'ocr-spike.html')), false, 'No-Go commit must not retain the internal UI');

const report = read('report/phase-9.6a-browser-ocr-spike.md');
assert.match(report, /Decision: \*\*NO-GO for public release\*\*/);
assert.match(report, /Japanese clean CER: 58\.65%/);
assert.match(report, /Multi-user standard: timed out after 310 seconds/);

process.stdout.write('OK: OCR No-Go report and public non-exposure guard\n');
