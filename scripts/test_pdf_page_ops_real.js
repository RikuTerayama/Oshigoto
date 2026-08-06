'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');

const pdfLibPath = process.env.PDF_LIB_PATH;
if (!pdfLibPath) {
    throw new Error('PDF_LIB_PATH must point to the existing pdf-lib 1.17.1 build.');
}

global.PDFLib = require(pdfLibPath);
global.PdfRange = require('../static/js/pdf-range.js');
global.FileUtils = { getFilenameWithoutExtension: filename => filename.replace(/\.pdf$/i, '') };
global.FileValidation = { sanitizeFilename: filename => filename.replace(/[<>:"/\\|?*\x00-\x1F]/g, '_') };
const { PdfOps } = require('../static/js/pdf-ops.js');

const ctx = {
    signal: { cancelled: false },
    setTaskState() {},
    setProgress() {}
};

function asFile(bytes, name = 'document.pdf') {
    return { name, async arrayBuffer() { return Uint8Array.from(bytes).buffer; } };
}

async function makePdf(widths, rotations = []) {
    const pdf = await PDFLib.PDFDocument.create();
    widths.forEach((width, index) => {
        const page = pdf.addPage([width, 600]);
        if (rotations[index]) page.setRotation(PDFLib.degrees(rotations[index]));
    });
    return pdf.save();
}

async function loadOutput(output) {
    return PDFLib.PDFDocument.load(await output[0].blob.arrayBuffer());
}

async function main() {
    let source = await makePdf([100, 200, 300, 400, 500]);
    let output = await PdfOps.deletePages(asFile(source), [2, 4], ctx);
    let result = await loadOutput(output);
    assert.equal(result.getPageCount(), 3);
    assert.deepEqual(result.getPages().map(page => page.getWidth()), [100, 300, 500]);
    assert.equal(output[0].filename, 'document_pages-removed.pdf');

    source = await makePdf([100, 200, 300, 400, 500]);
    output = await PdfOps.deletePages(asFile(source), [2, 3, 4], ctx);
    result = await loadOutput(output);
    assert.deepEqual(result.getPages().map(page => page.getWidth()), [100, 500]);

    source = await makePdf([100, 200, 300, 400, 500]);
    await assert.rejects(() => PdfOps.deletePages(asFile(source), [1, 2, 3, 4, 5], ctx), /全ページ/);
    source = await makePdf([100]);
    await assert.rejects(() => PdfOps.deletePages(asFile(source), [1], ctx), /全ページ/);

    source = await makePdf([100, 200, 300, 400], [0, 90, 0, 270]);
    output = await PdfOps.rotatePages(asFile(source), [1, 2, 3, 4], 90, ctx);
    result = await loadOutput(output);
    assert.deepEqual(result.getPages().map(page => page.getRotation().angle), [90, 180, 90, 0]);

    source = await makePdf([100, 200, 300, 400], [0, 90, 0, 270]);
    output = await PdfOps.rotatePages(asFile(source), [1, 3], 180, ctx);
    result = await loadOutput(output);
    assert.deepEqual(result.getPages().map(page => page.getRotation().angle), [180, 90, 180, 270]);
    await assert.rejects(() => PdfOps.rotatePages(asFile(source), [1], 45, ctx), /90度、180度、270度/);

    await assert.rejects(() => PdfOps.deletePages(asFile(Uint8Array.from([1, 2, 3])), [1], ctx), /読み込めません/);
    if (process.env.ENCRYPTED_PDF_PATH) {
        const encrypted = fs.readFileSync(process.env.ENCRYPTED_PDF_PATH);
        await assert.rejects(() => PdfOps.deletePages(asFile(encrypted), [1], ctx), /パスワード保護/);
    }

    console.log('OK: real pdf-lib deletion and rotation integration tests passed');
}

main().catch(error => {
    console.error(error.message);
    process.exitCode = 1;
});
