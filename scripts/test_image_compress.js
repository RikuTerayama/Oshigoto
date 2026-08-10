'use strict';

const assert = require('node:assert/strict');
const Core = require('../static/js/image-compress-core.js');

function bytes(...values) {
    return Uint8Array.from(values);
}

function ascii(value) {
    return Array.from(Buffer.from(value, 'ascii'));
}

function pngWithChunk(type) {
    return bytes(
        0x89, ...ascii('PNG'), 0x0d, 0x0a, 0x1a, 0x0a,
        0, 0, 0, 0, ...ascii(type), 0, 0, 0, 0,
    );
}

function webpWithChunk(type, payload = []) {
    const chunkLength = payload.length;
    const riffLength = 4 + 8 + chunkLength + (chunkLength % 2);
    return bytes(
        ...ascii('RIFF'), riffLength & 0xff, (riffLength >> 8) & 0xff, (riffLength >> 16) & 0xff, (riffLength >> 24) & 0xff,
        ...ascii('WEBP'), ...ascii(type), chunkLength & 0xff, 0, 0, 0, ...payload,
        ...(chunkLength % 2 ? [0] : []),
    );
}

function throws(fn, pattern) {
    assert.throws(fn, pattern);
}

assert.deepEqual(Core.calculateDimensions(4000, 3000, 2000, 2000), { width: 2000, height: 1500 });
assert.deepEqual(Core.calculateDimensions(1000, 2000, 800, 800), { width: 400, height: 800 });
assert.deepEqual(Core.calculateDimensions(4000, 3000, 1000, null), { width: 1000, height: 750 });
assert.deepEqual(Core.calculateDimensions(4000, 3000, null, 600), { width: 800, height: 600 });
assert.deepEqual(Core.calculateDimensions(400, 300, 1000, 1000), { width: 400, height: 300 });
throws(() => Core.parsePositiveInteger('0', 16384, '最大幅'), /1〜/);
throws(() => Core.parsePositiveInteger('-1', 16384, '最大幅'), /整数/);
throws(() => Core.parsePositiveInteger('1.5', 16384, '最大幅'), /整数/);
assert.equal(Core.parsePositiveInteger('', 16384, '最大幅'), null);

assert.equal(Core.normalizeQuality('1', 'jpeg'), 0.01);
assert.equal(Core.normalizeQuality('80', 'webp'), 0.8);
assert.equal(Core.normalizeQuality('70', 'avif'), 0.7);
assert.equal(Core.normalizeQuality('100', 'jpeg'), 1);
assert.equal(Core.normalizeQuality('anything', 'png'), null);
throws(() => Core.normalizeQuality('0', 'jpeg'), /1〜100/);
throws(() => Core.normalizeQuality('101', 'jpeg'), /1〜100/);
throws(() => Core.normalizeQuality('high', 'jpeg'), /1〜100/);

assert.equal(Core.describeSizeChange(1000, 500).text, '50.0%削減');
assert.equal(Core.describeSizeChange(1000, 1000).text, '容量はほぼ同じです');
assert.equal(Core.describeSizeChange(1000, 1125).text, '12.5%増加');
throws(() => Core.describeSizeChange(0, 100), /比較/);

const jpeg = bytes(0xff, 0xd8, 0xff, 0xdb);
const png = pngWithChunk('IEND');
const webp = webpWithChunk('VP8 ', [0]);
const gif = bytes(...ascii('GIF89a'));
assert.equal(Core.validateIdentity('photo.jpg', 'image/jpeg', jpeg), 'jpeg');
assert.equal(Core.validateIdentity('photo.jpeg', 'image/jpeg', jpeg), 'jpeg');
assert.equal(Core.validateIdentity('diagram.png', 'image/png', png), 'png');
assert.equal(Core.validateIdentity('photo.webp', 'image/webp', webp), 'webp');
throws(() => Core.validateIdentity('move.gif', 'image/gif', gif), /アニメーション/);
throws(() => Core.validateIdentity('vector.svg', 'image/svg+xml', bytes(...ascii('<svg'))), /対応形式/);
throws(() => Core.validateIdentity('fake.jpg', 'image/jpeg', png), /一致/);
throws(() => Core.validateIdentity('move.png', 'image/png', pngWithChunk('acTL')), /アニメーション/);
throws(() => Core.validateIdentity('move.webp', 'image/webp', webpWithChunk('ANIM')), /アニメーション/);
throws(() => Core.validateIdentity('move.webp', 'image/webp', webpWithChunk('VP8X', [0x02])), /アニメーション/);

assert.equal(Core.sanitizeFilename(String.raw`../資料/画像\photo.jpg`), 'photo.jpg');
assert.equal(Core.sanitizeFilename('bad\u0000name.png'), 'bad_name.png');
assert.equal(Core.generateOutputFilename('写真.jpg', 'jpeg', new Set()), '写真_compressed.jpg');
assert.equal(Core.generateOutputFilename('README', 'webp', new Set()), 'README_compressed.webp');
assert.equal(Core.generateOutputFilename('report.final.png', 'png', new Set()), 'report.final_compressed.png');
assert.equal(Core.generateOutputFilename('photo.png', 'avif', new Set()), 'photo_compressed.avif');
const names = new Set();
assert.equal(Core.generateOutputFilename('same.jpg', 'jpeg', names), 'same_compressed.jpg');
assert.equal(Core.generateOutputFilename('same.jpeg', 'jpeg', names), 'same_compressed_2.jpg');
assert.ok(Core.generateOutputFilename('a'.repeat(200) + '.jpg', 'jpeg', new Set()).length <= 135);

assert.equal(Core.validateSelectionLimits([{ size: 10 }, { size: 20 }], 2, 20, 30), 30);
throws(() => Core.validateSelectionLimits([{ size: 1 }, { size: 1 }], 1, 20, 30), /最大1件/);
throws(() => Core.validateSelectionLimits([{ size: 21 }], 1, 20, 30), /1ファイル/);
throws(() => Core.validateSelectionLimits([{ size: 16 }, { size: 16 }], 2, 20, 30), /合計容量/);
throws(() => Core.validateSelectionLimits([{ size: 0 }], 1, 20, 30), /0 byte/);
assert.equal(Core.validateImageLimits(8000, 5000, 40_000_000, 16_384), true);
throws(() => Core.validateImageLimits(8001, 5000, 40_000_000, 16_384), /最大40,000,000画素/);
throws(() => Core.validateImageLimits(16_385, 1, 40_000_000, 16_384), /長辺/);

console.log('OK: image compression pure functions');
