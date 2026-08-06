'use strict';

const assert = require('node:assert/strict');
const PdfRange = require('../static/js/pdf-range.js');

global.PdfRange = PdfRange;
global.FileUtils = {
    getFilenameWithoutExtension(filename) {
        return filename.replace(/\.pdf$/i, '');
    }
};
global.FileValidation = { sanitizeFilename: filename => filename };

class FakePage {
    constructor(id, angle = 0) {
        this.id = id;
        this.angle = angle;
    }
    getRotation() { return { angle: this.angle }; }
    setRotation(rotation) { this.angle = rotation.angle; }
}

class FakePdfDocument {
    constructor(pages = []) { this.pages = pages; }
    getPageCount() { return this.pages.length; }
    getPageIndices() { return this.pages.map((_, index) => index); }
    getPage(index) { return this.pages[index]; }
    async copyPages(source, indices) {
        return indices.map(index => new FakePage(source.pages[index].id, source.pages[index].angle));
    }
    addPage(page) { this.pages.push(page); }
    async save() {
        return new TextEncoder().encode(JSON.stringify(this.pages.map(page => ({ id: page.id, angle: page.angle }))));
    }
}

let nextDocument = null;
global.PDFLib = {
    PDFDocument: {
        async load() {
            if (nextDocument instanceof Error) throw nextDocument;
            return nextDocument;
        },
        async create() { return new FakePdfDocument(); }
    },
    degrees(angle) { return { angle }; }
};

const { PdfOps } = require('../static/js/pdf-ops.js');
const file = { name: 'document.pdf', async arrayBuffer() { return new ArrayBuffer(1); } };
const ctx = {
    signal: { cancelled: false },
    setTaskState() {},
    setProgress() {}
};

function fivePageDocument(rotations = [0, 0, 0, 0, 0]) {
    return new FakePdfDocument(rotations.map((angle, index) => new FakePage(index + 1, angle)));
}

async function blobPages(output) {
    return JSON.parse(new TextDecoder().decode(await output[0].blob.arrayBuffer()));
}

function expectRangeError(value, totalPages, pattern) {
    assert.throws(() => PdfRange.parsePageRange(value, { totalPages, maxExpandedPages: 500 }), pattern);
}

async function main() {
    assert.deepEqual(PdfRange.parsePageRange('1'), [1]);
    assert.deepEqual(PdfRange.parsePageRange('1,3,5'), [1, 3, 5]);
    assert.deepEqual(PdfRange.parsePageRange('2-5'), [2, 3, 4, 5]);
    assert.deepEqual(PdfRange.parsePageRange('1,3-5,8'), [1, 3, 4, 5, 8]);
    assert.deepEqual(PdfRange.parsePageRange('1, 3 - 5, 8'), [1, 3, 4, 5, 8]);
    assert.deepEqual(PdfRange.parsePageRange('2,2,4'), [2, 4]);
    assert.deepEqual(PdfRange.parsePageRange(''), []);
    assert.deepEqual(PdfRange.parseSplitRange('1-2;3,5', { totalPages: 5 }), [[1, 2], [3, 5]]);
    expectRangeError('0', 5, /1以上の整数/);
    expectRangeError('-1', 5, /1以上の整数/);
    expectRangeError('1.5', 5, /1以上の整数/);
    expectRangeError('6', 5, /5ページです/);
    expectRangeError('5-2', 5, /降順範囲/);
    expectRangeError('1--3', 5, /形式/);
    expectRangeError('１', 5, /形式/);
    expectRangeError('1,'.repeat(1100), 2000, /長すぎます/);

    nextDocument = fivePageDocument();
    let output = await PdfOps.deletePages(file, [2, 4], ctx);
    assert.deepEqual((await blobPages(output)).map(page => page.id), [1, 3, 5]);
    assert.equal(output[0].filename, 'document_pages-removed.pdf');

    nextDocument = fivePageDocument();
    output = await PdfOps.deletePages(file, [2, 3, 4], ctx);
    assert.deepEqual((await blobPages(output)).map(page => page.id), [1, 5]);

    nextDocument = fivePageDocument();
    await assert.rejects(() => PdfOps.deletePages(file, [1, 2, 3, 4, 5], ctx), /全ページ/);
    nextDocument = fivePageDocument();
    await assert.rejects(() => PdfOps.deletePages(file, [6], ctx), /5ページです/);
    nextDocument = new FakePdfDocument([new FakePage(1)]);
    await assert.rejects(() => PdfOps.deletePages(file, [1], ctx), /全ページ/);

    nextDocument = fivePageDocument([0, 90, 0, 270, 0]);
    output = await PdfOps.rotatePages(file, [1, 2, 3, 4, 5], 90, ctx);
    assert.deepEqual((await blobPages(output)).map(page => page.angle), [90, 180, 90, 0, 90]);
    assert.equal(output[0].filename, 'document_rotated-90.pdf');

    nextDocument = fivePageDocument([0, 90, 0, 270, 0]);
    output = await PdfOps.rotatePages(file, [1, 3], 180, ctx);
    assert.deepEqual((await blobPages(output)).map(page => page.angle), [180, 90, 180, 270, 0]);
    nextDocument = fivePageDocument();
    await assert.rejects(() => PdfOps.rotatePages(file, [1], 45, ctx), /90度、180度、270度/);
    nextDocument = fivePageDocument();
    await assert.rejects(() => PdfOps.rotatePages(file, [6], 90, ctx), /5ページです/);

    nextDocument = new Error('Input document is encrypted');
    await assert.rejects(() => PdfOps.deletePages(file, [1], ctx), /パスワード保護/);

    console.log('OK: PDF page parser, deletion, and rotation tests passed');
}

main().catch(error => {
    console.error(error.message);
    process.exitCode = 1;
});
