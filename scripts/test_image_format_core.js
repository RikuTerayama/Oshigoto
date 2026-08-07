'use strict';

const assert = require('node:assert/strict');
const Core = require('../static/js/image-format-core.js');

const ascii = (value) => Array.from(Buffer.from(value, 'ascii'));
const bytes = (...values) => Uint8Array.from(values);
const u32be = (value) => [(value >>> 24) & 255, (value >>> 16) & 255, (value >>> 8) & 255, value & 255];

function pngChunk(type, payload = []) {
    return [...u32be(payload.length), ...ascii(type), ...payload, 0, 0, 0, 0];
}

function pngWith(...chunks) {
    return bytes(0x89, ...ascii('PNG'), 0x0d, 0x0a, 0x1a, 0x0a, ...chunks.flat());
}

function webpChunk(type, payload = []) {
    return [...ascii(type), payload.length & 255, (payload.length >>> 8) & 255, 0, 0, ...payload, ...(payload.length % 2 ? [0] : [])];
}

function webpWith(...chunks) {
    const body = [...ascii('WEBP'), ...chunks.flat()];
    return bytes(...ascii('RIFF'), ...[body.length, 0, 0, 0], ...body);
}

function gif(frameCount, includeExtension = false, truncate = false) {
    const header = [...ascii('GIF89a'), 1, 0, 1, 0, 0, 0, 0];
    const extension = includeExtension ? [0x21, 0xfe, 3, ...ascii('abc'), 0] : [];
    const frame = [0x2c, 0, 0, 0, 0, 1, 0, 1, 0, 0, 2, 2, 0x44, 0x01, 0];
    const output = [...header, ...extension];
    for (let i = 0; i < frameCount; i += 1) output.push(...frame);
    if (!truncate) output.push(0x3b);
    return bytes(...output);
}

function bmp(bits = 24, compression = 0, width = 1, height = 1, pixelOffset = 54, dibSize = 40) {
    const size = Math.max(58, pixelOffset + 4);
    const output = new Uint8Array(size);
    const view = new DataView(output.buffer);
    output[0] = 0x42; output[1] = 0x4d;
    view.setUint32(2, size, true); view.setUint32(10, pixelOffset, true); view.setUint32(14, dibSize, true);
    view.setInt32(18, width, true); view.setInt32(22, height, true); view.setUint16(26, 1, true);
    view.setUint16(28, bits, true); view.setUint32(30, compression, true); view.setUint32(34, 4, true);
    return output;
}

function ftyp(major, compatible = []) {
    const payload = [...ascii(major), 0, 0, 0, 0, ...compatible.flatMap(ascii)];
    return bytes(...u32be(payload.length + 8), ...ascii('ftyp'), ...payload);
}

function throws(fn, pattern) { assert.throws(fn, pattern); }

const jpeg = bytes(0xff, 0xd8, 0xff, 0xdb);
const png = pngWith(pngChunk('IEND'));
const webp = webpWith(webpChunk('VP8 ', [0]));
assert.equal(Core.detectFileFormat(jpeg), 'jpeg');
assert.equal(Core.validateFileIdentity('photo.jpg', 'image/jpeg', jpeg, { allowedFormats: ['jpeg'] }), 'jpeg');
throws(() => Core.validateFileIdentity('photo.png', 'image/png', jpeg, { allowedFormats: ['jpeg', 'png'] }), /一致/);
throws(() => Core.validateFileIdentity('photo.jpg', 'image/png', jpeg, { allowedFormats: ['jpeg'] }), /一致/);
assert.equal(Core.validateFileIdentity('diagram.png', 'image/png', png, { allowedFormats: ['png'] }), 'png');
assert.equal(Core.detectApng(png), false);
throws(() => Core.validateFileIdentity('move.png', 'image/png', pngWith(pngChunk('acTL'), pngChunk('IEND')), { allowedFormats: ['png'] }), /アニメーションPNG/);
throws(() => Core.detectApng(pngWith([...u32be(100), ...ascii('IDAT')])), /途中/);

assert.equal(Core.validateFileIdentity('photo.webp', 'image/webp', webp, { allowedFormats: ['webp'] }), 'webp');
throws(() => Core.validateFileIdentity('move.webp', 'image/webp', webpWith(webpChunk('ANIM')), { allowedFormats: ['webp'] }), /アニメーションWebP/);
throws(() => Core.validateFileIdentity('move.webp', 'image/webp', webpWith(webpChunk('VP8X', [0x02])), { allowedFormats: ['webp'] }), /アニメーションWebP/);
throws(() => Core.detectAnimatedWebp(bytes(...ascii('RIFF'), 20, 0, 0, 0, ...ascii('WEBPVP8 '), 100, 0, 0, 0)), /途中/);

assert.equal(Core.countGifFrames(gif(1)), 1);
assert.equal(Core.countGifFrames(bytes(...ascii('GIF87a'), ...gif(1).slice(6))), 1);
assert.equal(Core.countGifFrames(gif(1, true)), 1);
assert.equal(Core.countGifFrames(gif(2)), 2);
throws(() => Core.validateFileIdentity('move.gif', 'image/gif', gif(2), { allowedFormats: ['gif'] }), /アニメーションGIF/);
throws(() => Core.countGifFrames(gif(1, false, true)), /途中/);
throws(() => Core.countGifFrames(bytes(...ascii('GIF89a'), 1, 0, 1, 0, 0, 0, 0, 0x21, 0xfe, 10, 1)), /途中/);

assert.equal(Core.parseBmp(bmp(24)).bitsPerPixel, 24);
assert.equal(Core.parseBmp(bmp(32)).bitsPerPixel, 32);
throws(() => Core.parseBmp(bmp(24, 1)), /24bit・32bit/);
throws(() => Core.parseBmp(bmp(24, 0, 1, 1, 20)), /構造/);
throws(() => Core.parseBmp(bmp(24, 0, 1, 1, 54, 12)), /ヘッダー/);
throws(() => Core.parseBmp(bmp(24, 0, -1, 1)), /サイズ/);
throws(() => Core.parseBmp(bmp(24).slice(0, 30)), /壊れ/);

assert.equal(Core.detectFileFormat(ftyp('avif')), 'avif');
assert.equal(Core.detectFileFormat(ftyp('mif1', ['avis'])), 'avif');
throws(
    () => Core.validateFileIdentity('sequence.avif', 'image/avif', ftyp('mif1', ['avis']), { allowedFormats: ['avif'] }),
    /AVIFシーケンス/
);
assert.equal(Core.detectFileFormat(ftyp('heic', ['mif1'])), 'heif');
assert.equal(Core.detectFileFormat(ftyp('mif1')), 'heif');
assert.equal(Core.parseIsoBrands(ftyp('avif')).majorBrand, 'avif');
assert.equal(Core.parseIsoBrands(bytes(0, 0, 0, 40, ...ascii('ftyp'), ...ascii('avif'))), null);
assert.equal(Core.parseIsoBrands(bytes(0, 0, 0, 4, ...ascii('ftyp'))), null);

assert.equal(Core.validateEncodedBuffer(jpeg, 'jpeg', 'image/jpeg'), true);
assert.equal(Core.validateEncodedBuffer(png, 'png', 'image/png'), true);
assert.equal(Core.validateEncodedBuffer(webp, 'webp', 'image/webp'), true);
assert.equal(Core.validateEncodedBuffer(ftyp('avif'), 'avif', 'image/avif'), true);
throws(() => Core.validateEncodedBuffer(png, 'avif', 'image/png'), /AVIF/);
throws(() => Core.validateEncodedBuffer(png, 'jpeg', 'image/jpeg'), /一致/);

assert.equal(Core.ensureOutputFilename('photo.gif', 'png', new Set()), 'photo.png');
assert.equal(Core.ensureOutputFilename('photo.bmp', 'jpeg', new Set()), 'photo.jpg');
assert.equal(Core.ensureOutputFilename('photo.avif', 'webp', new Set()), 'photo.webp');
assert.equal(Core.ensureOutputFilename('report.final.png.exe', 'png', new Set()), 'report.final.png');
assert.equal(Core.ensureOutputFilename('日本語.gif', 'png', new Set()), '日本語.png');
const names = new Set();
assert.equal(Core.ensureOutputFilename('same.gif', 'png', names), 'same.png');
assert.equal(Core.ensureOutputFilename('same.bmp', 'png', names), 'same_2.png');
assert.ok(Core.ensureOutputFilename(`bad\u0000${'a'.repeat(250)}.gif`, 'png', new Set()).length <= 186);

console.log('OK: shared image format pure functions');
