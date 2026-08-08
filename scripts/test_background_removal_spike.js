'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const read = (relativePath) => fs.readFileSync(path.join(root, relativePath), 'utf8');

function validateInput({ files, bytes, pixels, longestEdge }) {
    if (files !== 1) throw new Error('one_file_only');
    if (bytes <= 0 || bytes > 5 * 1024 * 1024) throw new Error('file_size');
    if (pixels <= 0 || pixels > 4_000_000) throw new Error('pixel_limit');
    if (longestEdge <= 0 || longestEdge > 2048) throw new Error('edge_limit');
    return true;
}

function maskMetrics(reference, candidate) {
    assert.equal(reference.length, candidate.length);
    let intersection = 0;
    let union = 0;
    let referenceCount = 0;
    let candidateCount = 0;
    let correct = 0;
    let alphaError = 0;
    for (let index = 0; index < reference.length; index += 1) {
        const expected = reference[index];
        const actual = candidate[index];
        const expectedForeground = expected >= 128;
        const actualForeground = actual >= 128;
        if (expectedForeground && actualForeground) intersection += 1;
        if (expectedForeground || actualForeground) union += 1;
        if (expectedForeground) referenceCount += 1;
        if (actualForeground) candidateCount += 1;
        if (expectedForeground === actualForeground) correct += 1;
        alphaError += Math.abs(expected - actual) / 255;
    }
    return {
        iou: union === 0 ? 1 : intersection / union,
        dice: referenceCount + candidateCount === 0 ? 1 : (2 * intersection) / (referenceCount + candidateCount),
        pixelAccuracy: correct / reference.length,
        meanAlphaError: alphaError / reference.length,
    };
}

function boundaryFScore(reference, candidate, width, height) {
    const boundary = (mask) => mask.map((value, index) => {
        const x = index % width;
        const y = Math.floor(index / width);
        const neighbors = [];
        if (x > 0) neighbors.push(index - 1);
        if (x + 1 < width) neighbors.push(index + 1);
        if (y > 0) neighbors.push(index - width);
        if (y + 1 < height) neighbors.push(index + width);
        return neighbors.some((neighbor) => (mask[neighbor] >= 128) !== (value >= 128));
    });
    const expectedBoundary = boundary(reference);
    const actualBoundary = boundary(candidate);
    const expectedCount = expectedBoundary.filter(Boolean).length;
    const actualCount = actualBoundary.filter(Boolean).length;
    const matches = expectedBoundary.reduce((sum, value, index) => sum + (value && actualBoundary[index] ? 1 : 0), 0);
    if (expectedCount + actualCount === 0) return 1;
    return (2 * matches) / (expectedCount + actualCount);
}

function sanitizeFilename(value) {
    const basename = value.replace(/\\/g, '/').split('/').pop();
    return basename.replace(/[\u0000-\u001f<>:"|?*]/g, '_').slice(0, 128) || 'background-removed.png';
}

function acceptsResult(activeGeneration, resultGeneration) {
    return activeGeneration === resultGeneration;
}

async function withTimeout(promise, timeoutMs) {
    let timeoutId;
    try {
        return await Promise.race([
            promise,
            new Promise((_, reject) => {
                timeoutId = setTimeout(() => reject(new Error('timeout')), timeoutMs);
            }),
        ]);
    } finally {
        clearTimeout(timeoutId);
    }
}

assert.equal(validateInput({ files: 1, bytes: 5 * 1024 * 1024, pixels: 4_000_000, longestEdge: 2048 }), true);
assert.throws(() => validateInput({ files: 2, bytes: 1, pixels: 1, longestEdge: 1 }), /one_file_only/);
assert.throws(() => validateInput({ files: 1, bytes: 5 * 1024 * 1024 + 1, pixels: 1, longestEdge: 1 }), /file_size/);
assert.throws(() => validateInput({ files: 1, bytes: 1, pixels: 4_000_001, longestEdge: 1 }), /pixel_limit/);
assert.throws(() => validateInput({ files: 1, bytes: 1, pixels: 1, longestEdge: 2049 }), /edge_limit/);

const perfect = maskMetrics([0, 255, 255, 0], [0, 255, 255, 0]);
assert.deepEqual(perfect, { iou: 1, dice: 1, pixelAccuracy: 1, meanAlphaError: 0 });
const partial = maskMetrics([0, 255, 255, 0], [0, 255, 0, 0]);
assert.equal(partial.iou, 0.5);
assert.equal(partial.dice, 2 / 3);
assert.equal(partial.pixelAccuracy, 0.75);
assert.equal(partial.meanAlphaError, 0.25);
assert.equal(boundaryFScore([0, 255, 255, 0], [0, 255, 255, 0], 2, 2), 1);

assert.equal(sanitizeFilename('../unsafe<script>.png'), 'unsafe_script_.png');
assert.equal(acceptsResult(4, 4), true);
assert.equal(acceptsResult(5, 4), false);

const publicFiles = [
    'app.py',
    'lib/products_catalog.py',
    'lib/nav.py',
    'lib/seo.py',
    'templates/landing.html',
    'templates/tools/image-cleanup.html',
    'templates/guide/image-cleanup.html',
];
for (const relativePath of publicFiles) {
    const source = read(relativePath).toLowerCase();
    assert.equal(source.includes('/tools/background-removal'), false, `${relativePath} must not publish the tool`);
    assert.equal(source.includes('/guide/background-removal'), false, `${relativePath} must not publish the guide`);
    assert.equal(source.includes('/api/background-removal'), false, `${relativePath} must not publish the API`);
}

const cleanupTemplate = read('templates/tools/image-cleanup.html');
assert.equal(cleanupTemplate.includes('id="background-removal"'), false);
assert.equal(cleanupTemplate.includes('image-background-removal.js'), false);
assert.equal(cleanupTemplate.includes('innerHTML'), false);
assert.equal(fs.existsSync(path.join(root, 'static', 'js', 'image-background-removal.js')), false);
assert.equal(fs.existsSync(path.join(root, 'templates', 'internal', 'background-removal-spike.html')), false);
assert.match(read('report/phase-9.7a-background-removal-spike.md'), /Decision: \*\*NO-GO for public release\*\*/);

withTimeout(new Promise((resolve) => setTimeout(() => resolve('ok'), 1)), 50)
    .then((value) => {
        assert.equal(value, 'ok');
        return assert.rejects(() => withTimeout(new Promise(() => {}), 5), /timeout/);
    })
    .then(() => process.stdout.write('OK: background removal No-Go guards and pure helpers\n'))
    .catch((error) => {
        process.stderr.write(`${error.stack}\n`);
        process.exitCode = 1;
    });
