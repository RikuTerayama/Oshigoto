/**
 * PDF操作ユーティリティ（pdf-lib使用）
 */

/** pdf-lib の暗号化PDFエラーかどうか判定 */
function isEncryptedPdfLibError(e) {
    return String(e?.message || '').toLowerCase().includes('encrypted');
}

/**
 * PDFDocument.load を実行し、暗号化PDFの場合はユーザー向けメッセージで throw
 * @param {ArrayBuffer} arrayBuffer
 * @param {string} filename - 表示用
 * @returns {Promise<PDFDocument>}
 */
async function loadPdfOrThrowUserMessage(arrayBuffer, filename) {
    if (typeof PDFLib === 'undefined') {
        throw new Error('PDFLibライブラリが読み込まれていません');
    }
    const { PDFDocument } = PDFLib;
    try {
        return await PDFDocument.load(arrayBuffer);
    } catch (e) {
        if (isEncryptedPdfLibError(e)) {
            throw new Error('このPDFはパスワード保護されているため処理できません。保護されていないPDFを使用してください。');
        }
        throw new Error('このPDFを読み込めません。ファイルが破損しているか、対応していない形式です。');
    }
}

class PdfOps {
    /**
     * PDFを結合
     * @param {File[]} files - 結合するPDFファイル
     * @param {Object} ctx - コンテキスト
     * @returns {Promise<Array<{blob: Blob, filename: string, mime: string}>>}
     */
    static async mergePdfs(files, ctx) {
        if (typeof PDFLib === 'undefined') {
            throw new Error('PDFLibライブラリが読み込まれていません');
        }

        const { PDFDocument } = PDFLib;
        const mergedPdf = await PDFDocument.create();

        for (let i = 0; i < files.length; i++) {
            if (ctx.signal.cancelled) {
                throw new Error('キャンセルされました');
            }

            const file = files[i];
            ctx.setTaskState(i, { status: 'running', message: '読み込み中...' });
            ctx.setProgress((i / files.length) * 100);

            try {
                const arrayBuffer = await file.arrayBuffer();
                const pdf = await loadPdfOrThrowUserMessage(arrayBuffer, file.name);
                const pages = await mergedPdf.copyPages(pdf, pdf.getPageIndices());
                pages.forEach(page => mergedPdf.addPage(page));

                ctx.setTaskState(i, { status: 'success', message: '完了' });
            } catch (error) {
                ctx.setTaskState(i, { status: 'error', message: error.message || 'エラー' });
                throw new Error(`${file.name}の処理に失敗しました: ${error.message}`);
            }
        }

        if (ctx.signal.cancelled) {
            throw new Error('キャンセルされました');
        }

        ctx.setProgress(100);
        const pdfBytes = await mergedPdf.save();
        const blob = new Blob([pdfBytes], { type: 'application/pdf' });

        const baseName = files.length > 0 
            ? FileUtils.getFilenameWithoutExtension(files[0].name)
            : 'merged';
        const filename = FileValidation.sanitizeFilename(`${baseName}_merged.pdf`);

        return [{
            blob,
            filename,
            mime: 'application/pdf'
        }];
    }

    /**
     * PDFからページを抽出
     * @param {File} file - 抽出元のPDFファイル
     * @param {number[]} pages - 抽出するページ番号（1始まり）
     * @param {Object} ctx - コンテキスト
     * @returns {Promise<Array<{blob: Blob, filename: string, mime: string}>>}
     */
    static async extractPdf(file, pages, ctx) {
        if (typeof PDFLib === 'undefined') {
            throw new Error('PDFLibライブラリが読み込まれていません');
        }

        if (ctx.signal.cancelled) {
            throw new Error('キャンセルされました');
        }

        const { PDFDocument } = PDFLib;
        ctx.setTaskState(0, { status: 'running', message: '読み込み中...' });
        ctx.setProgress(10);

        const arrayBuffer = await file.arrayBuffer();
        const pdf = await loadPdfOrThrowUserMessage(arrayBuffer, file.name);
        const totalPages = pdf.getPageCount();

        // ページ番号のバリデーション
        const validation = PdfRange.validatePages(pages, totalPages);
        if (!validation.valid) {
            throw new Error(`無効なページ番号: ${validation.invalid.join(', ')} (総ページ数: ${totalPages})`);
        }

        ctx.setProgress(30);
        const extractedPdf = await PDFDocument.create();

        // ページインデックスに変換（0始まり）
        const pageIndices = pages.map(p => p - 1);
        const copiedPages = await extractedPdf.copyPages(pdf, pageIndices);
        copiedPages.forEach(page => extractedPdf.addPage(page));

        ctx.setProgress(80);
        const pdfBytes = await extractedPdf.save();
        const blob = new Blob([pdfBytes], { type: 'application/pdf' });

        const baseName = FileUtils.getFilenameWithoutExtension(file.name);
        const rangeStr = pages.length === 1 
            ? `p${pages[0]}`
            : `p${pages[0]}-${pages[pages.length - 1]}`;
        const filename = FileValidation.sanitizeFilename(`${baseName}_extract_${rangeStr}.pdf`);

        ctx.setProgress(100);
        ctx.setTaskState(0, { status: 'success', message: '完了' });

        return [{
            blob,
            filename,
            mime: 'application/pdf'
        }];
    }

    /**
     * PDFを分割
     * @param {File} file - 分割元のPDFファイル
     * @param {number[][]} pageGroups - 分割グループ（各グループはページ番号配列）
     * @param {Object} ctx - コンテキスト
     * @returns {Promise<Array<{blob: Blob, filename: string, mime: string}>>}
     */
    static async splitPdf(file, pageGroups, ctx) {
        if (typeof PDFLib === 'undefined') {
            throw new Error('PDFLibライブラリが読み込まれていません');
        }

        if (ctx.signal.cancelled) {
            throw new Error('キャンセルされました');
        }

        const { PDFDocument } = PDFLib;
        ctx.setTaskState(0, { status: 'running', message: '読み込み中...' });
        ctx.setProgress(10);

        const arrayBuffer = await file.arrayBuffer();
        const pdf = await loadPdfOrThrowUserMessage(arrayBuffer, file.name);
        const totalPages = pdf.getPageCount();

        // すべてのページグループをバリデーション
        for (const group of pageGroups) {
            const validation = PdfRange.validatePages(group, totalPages);
            if (!validation.valid) {
                throw new Error(`無効なページ番号: ${validation.invalid.join(', ')} (総ページ数: ${totalPages})`);
            }
        }

        const outputs = [];

        for (let i = 0; i < pageGroups.length; i++) {
            if (ctx.signal.cancelled) {
                throw new Error('キャンセルされました');
            }

            const group = pageGroups[i];
            ctx.setProgress(20 + (i / pageGroups.length) * 70);
            ctx.setTaskState(0, { 
                status: 'running', 
                message: `分割中... (${i + 1}/${pageGroups.length})` 
            });

            const splitPdf = await PDFDocument.create();
            const pageIndices = group.map(p => p - 1);
            const copiedPages = await splitPdf.copyPages(pdf, pageIndices);
            copiedPages.forEach(page => splitPdf.addPage(page));

            const pdfBytes = await splitPdf.save();
            const blob = new Blob([pdfBytes], { type: 'application/pdf' });

            const baseName = FileUtils.getFilenameWithoutExtension(file.name);
            const rangeStr = group.length === 1 
                ? `p${group[0]}`
                : `p${group[0]}-${group[group.length - 1]}`;
            const filename = FileValidation.sanitizeFilename(`${baseName}_part${i + 1}_${rangeStr}.pdf`);

            outputs.push({
                blob,
                filename,
                mime: 'application/pdf'
            });
        }

        ctx.setProgress(100);
        ctx.setTaskState(0, { status: 'success', message: '完了' });

        return outputs;
    }

    /** Create a new PDF containing every page except the selected pages. */
    static async deletePages(file, pages, ctx) {
        if (typeof PDFLib === 'undefined') {
            throw new Error('PDFLibライブラリが読み込まれていません');
        }
        if (ctx.signal.cancelled) throw new Error('キャンセルされました');

        const { PDFDocument } = PDFLib;
        ctx.setTaskState(0, { status: 'running', message: 'ページを確認中...' });
        ctx.setProgress(10);
        const pdf = await loadPdfOrThrowUserMessage(await file.arrayBuffer(), file.name);
        const totalPages = pdf.getPageCount();
        const validation = PdfRange.validatePages(pages, totalPages);
        if (!validation.valid) {
            throw new Error(`このPDFは${totalPages}ページです。${validation.invalid[0]}ページ目は指定できません。`);
        }

        const uniquePages = new Set(pages);
        if (uniquePages.size >= totalPages) {
            throw new Error('全ページは削除できません。残すページを1ページ以上確保してください。');
        }
        if (ctx.signal.cancelled) throw new Error('キャンセルされました');

        const remainingIndices = pdf.getPageIndices().filter(index => !uniquePages.has(index + 1));
        const outputPdf = await PDFDocument.create();
        const copiedPages = await outputPdf.copyPages(pdf, remainingIndices);
        copiedPages.forEach(page => outputPdf.addPage(page));
        ctx.setProgress(80);

        const pdfBytes = await outputPdf.save();
        const baseName = FileUtils.getFilenameWithoutExtension(file.name);
        ctx.setProgress(100);
        ctx.setTaskState(0, { status: 'success', message: '完了' });
        return [{
            blob: new Blob([pdfBytes], { type: 'application/pdf' }),
            filename: FileValidation.sanitizeFilename(`${baseName}_pages-removed.pdf`),
            mime: 'application/pdf'
        }];
    }

    /** Rotate selected 1-based pages clockwise, preserving page order and size. */
    static async rotatePages(file, pages, angle, ctx) {
        if (typeof PDFLib === 'undefined') {
            throw new Error('PDFLibライブラリが読み込まれていません');
        }
        if (![90, 180, 270].includes(angle)) {
            throw new Error('回転角度は90度、180度、270度から選んでください。');
        }
        if (ctx.signal.cancelled) throw new Error('キャンセルされました');

        const { degrees } = PDFLib;
        ctx.setTaskState(0, { status: 'running', message: 'ページを回転中...' });
        ctx.setProgress(10);
        const pdf = await loadPdfOrThrowUserMessage(await file.arrayBuffer(), file.name);
        const totalPages = pdf.getPageCount();
        const validation = PdfRange.validatePages(pages, totalPages);
        if (!pages.length) throw new Error('回転するページを指定してください。');
        if (!validation.valid) {
            throw new Error(`このPDFは${totalPages}ページです。${validation.invalid[0]}ページ目は指定できません。`);
        }

        pages.forEach(pageNumber => {
            const page = pdf.getPage(pageNumber - 1);
            const currentAngle = Number(page.getRotation()?.angle || 0);
            page.setRotation(degrees(((currentAngle + angle) % 360 + 360) % 360));
        });
        if (ctx.signal.cancelled) throw new Error('キャンセルされました');
        ctx.setProgress(80);

        const pdfBytes = await pdf.save();
        const baseName = FileUtils.getFilenameWithoutExtension(file.name);
        ctx.setProgress(100);
        ctx.setTaskState(0, { status: 'success', message: '完了' });
        return [{
            blob: new Blob([pdfBytes], { type: 'application/pdf' }),
            filename: FileValidation.sanitizeFilename(`${baseName}_rotated-${angle}.pdf`),
            mime: 'application/pdf'
        }];
    }

    /**
     * PDFの総ページ数を取得
     * @param {File} file - PDFファイル
     * @returns {Promise<number>}
     */
    static async getPageCount(file) {
        if (typeof PDFLib === 'undefined') {
            throw new Error('PDFLibライブラリが読み込まれていません');
        }
        const arrayBuffer = await file.arrayBuffer();
        const pdf = await loadPdfOrThrowUserMessage(arrayBuffer, file.name);
        return pdf.getPageCount();
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = { PdfOps, loadPdfOrThrowUserMessage };
}
