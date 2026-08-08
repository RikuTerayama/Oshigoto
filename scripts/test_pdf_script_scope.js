'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const scripts = [
    'static/js/pdf-range.js',
    'static/js/pdf-ops.js',
    'static/js/pdf-render.js',
    'static/js/pdf-compress.js',
    'static/js/pdf-images-to-pdf.js',
    'static/js/pdf-extract-images.js'
];

const context = vm.createContext({ console });
for (const relativePath of scripts) {
    const source = fs.readFileSync(path.join(root, relativePath), 'utf8');
    assert.doesNotThrow(
        () => new vm.Script(source, { filename: relativePath }).runInContext(context),
        `${relativePath} must coexist with the preceding PDF scripts`
    );
}

console.log(`OK: ${scripts.length} PDF scripts share one page scope without declaration conflicts`);
