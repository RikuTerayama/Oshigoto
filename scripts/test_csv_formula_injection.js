'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const root = path.resolve(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'static', 'js', 'csv-ops.js'), 'utf8');
const sandbox = { window: {} };
vm.createContext(sandbox);
vm.runInContext(`${source}\nglobalThis.__CsvOps = CsvOps;`, sandbox, { filename: 'csv-ops.js' });

const CsvOps = sandbox.__CsvOps;
assert.ok(CsvOps, 'CsvOps must be exported');

for (const dangerous of [
    '=HYPERLINK("https://example.invalid")',
    '=WEBSERVICE("https://example.invalid")',
    '+SUM(1,2)',
    '-1+2',
    '@SUM(A1:A2)',
    '\tformula',
    '\rformula'
]) {
    const safe = CsvOps.sanitizeSpreadsheetCell(dangerous);
    assert.strictEqual(safe, `'${dangerous}`, dangerous);
}

assert.strictEqual(CsvOps.sanitizeSpreadsheetCell('normal text'), 'normal text');
assert.strictEqual(CsvOps.sanitizeSpreadsheetCell(42), 42);
assert.deepStrictEqual(
    JSON.parse(JSON.stringify(CsvOps.sanitizeSpreadsheetRows([['=1+1', 'safe']]))),
    [["'=1+1", 'safe']]
);

console.log('PASS: CSV and XLSX exports neutralize spreadsheet formulas');
