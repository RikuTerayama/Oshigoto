/**
 * PDF圧縮ユーティリティ（レンダリング→画像化→再PDF化）
 * 注意: この方式は文字検索やテキスト選択ができなくなります（ページが画像になります）
 */

const ENCRYPTED_PDF_USER_MESSAGE = 'このPDFはパスワード保護されています。正しいパスワードを入力してください。';

function isEncryptedPdfJsError(e) {
    const msg = String(e?.message || '').toLowerCase();
    const name = String(e?.name || '').toLowerCase();
    return name.includes('password') || msg.includes('password') || msg.includes('encrypted');
}

class PdfCompress {
    /**
     * PDFを圧縮（レンダリング→画像化→再PDF化）
     * @param {File} file - 入力PDFファイル
     * @param {Object} options - オプション
     * @param {number} options.quality - JPEG品質（0.1-1.0）
     * @param {number} options.scale - レンダリング倍率（例: 1.0, 1.5, 2.0）
     * @param {number} options.maxLongEdge - 出力画像の長辺上限（px）
     * @param {Object} ctx - コンテキスト
     * @returns {Promise<Array<{blob: Blob, filename: string, mime: string}>>}
     */
    static async compressPdfByRasterize(file, options = {}, ctx = {}) {
        if (typeof pdfjsLib === 'undefined') {
            throw new Error('pdfjs-distライブラリが読み込まれていません');
        }
        if (typeof PDFLib === 'undefined') {
            throw new Error('PDFLibライブラリが読み込まれていません');
        }

        const pdfjs = pdfjsLib;
        const { PDFDocument } = PDFLib;

        const {
            quality = 0.75,
            scale = 1.5,
            maxLongEdge = 2000
        } = options;

        // Workerの設定
        if (pdfjs.GlobalWorkerOptions) {
            pdfjs.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
        }

        if (ctx.signal && ctx.signal.cancelled) {
            throw new Error('キャンセルされました');
        }

        if (ctx.setTaskState) {
            ctx.setTaskState(0, { status: 'running', message: 'PDF読み込み中...' });
        }

        // PDFを読み込み
        const arrayBuffer = await file.arrayBuffer();
        const password = (options.password != null && options.password !== '') ? options.password : undefined;
        let pdf;
        try {
            const loadingTask = pdfjs.getDocument({ data: arrayBuffer, password });
            pdf = await loadingTask.promise;
        } catch (e) {
            if (isEncryptedPdfJsError(e)) {
                throw new Error(ENCRYPTED_PDF_USER_MESSAGE);
            }
            console.error('[PdfCompress] load_failed', { fileName: file.name });
            throw e;
        }
        const numPages = pdf.numPages;

        if (ctx.setProgress) {
            ctx.setProgress(5);
        }

        // 新しいPDFを作成
        const compressedPdf = await PDFDocument.create();
        const pageImages = [];

        // 各ページをレンダリングして画像化
        for (let pageNum = 1; pageNum <= numPages; pageNum++) {
            if (ctx.signal && ctx.signal.cancelled) {
                throw new Error('キャンセルされました');
            }

            if (ctx.setTaskState) {
                ctx.setTaskState(0, { 
                    status: 'running', 
                    message: `ページ ${pageNum}/${numPages} を処理中...` 
                });
            }

            const page = await pdf.getPage(pageNum);
            let viewport = page.getViewport({ scale });

            // 長辺が上限を超える場合はスケールを調整
            let actualScale = scale;
            const longEdge = Math.max(viewport.width, viewport.height);
            if (longEdge > maxLongEdge) {
                actualScale = (maxLongEdge / longEdge) * scale;
                viewport = page.getViewport({ scale: actualScale });
            }

            // Canvasを作成
            const canvas = document.createElement('canvas');
            canvas.width = viewport.width;
            canvas.height = viewport.height;
            const context = canvas.getContext('2d');

            // 背景を白で塗りつぶし
            context.fillStyle = '#FFFFFF';
            context.fillRect(0, 0, canvas.width, canvas.height);

            // ページをレンダリング
            const renderContext = {
                canvasContext: context,
                viewport: viewport
            };
            try {
                await page.render(renderContext).promise;
            } catch (e) {
                console.error('[PdfCompress] render_failed', { fileName: file.name, pageNum, error: e });
                throw e;
            }

            // JPEGに変換
            const imageBlob = await new Promise((resolve, reject) => {
                canvas.toBlob(
                    (blob) => {
                        if (blob) {
                            resolve(blob);
                            return;
                        }
                        console.error('[PdfCompress] toBlob_failed', {
                            fileName: file.name,
                            pageNum,
                            canvasWidth: canvas.width,
                            canvasHeight: canvas.height
                        });
                        reject(new Error('画像変換に失敗しました'));
                    },
                    'image/jpeg',
                    quality
                );
            });

            // pdf-libで画像を埋め込み
            const imageBytes = await imageBlob.arrayBuffer();
            const pdfImage = await compressedPdf.embedJpg(imageBytes);
            
            // ページサイズを設定
            const { width, height } = pdfImage.scale(1);
            const pdfPage = compressedPdf.addPage([width, height]);
            pdfPage.drawImage(pdfImage, {
                x: 0,
                y: 0,
                width: width,
                height: height
            });

            pageImages.push({ pageNum, imageBlob });

            // 進捗更新
            if (ctx.setProgress) {
                ctx.setProgress(5 + (pageNum / numPages) * 90);
            }

            // メモリ解放
            canvas.width = 0;
            canvas.height = 0;
        }

        if (ctx.signal && ctx.signal.cancelled) {
            throw new Error('キャンセルされました');
        }

        if (ctx.setTaskState) {
            ctx.setTaskState(0, { status: 'running', message: 'PDFを保存中...' });
        }

        // PDFを保存
        const pdfBytes = await compressedPdf.save();
        const blob = new Blob([pdfBytes], { type: 'application/pdf' });

        if (ctx.setProgress) {
            ctx.setProgress(100);
        }

        if (ctx.setTaskState) {
            ctx.setTaskState(0, { status: 'success', message: '完了' });
        }

        const baseName = FileUtils.getFilenameWithoutExtension(file.name);
        const filename = FileValidation.sanitizeFilename(`${baseName}_compressed.pdf`);

        return [{
            blob,
            filename,
            mime: 'application/pdf'
        }];
    }
}

if (typeof globalThis !== 'undefined') {
    globalThis.PdfCompress = PdfCompress;
}
if (typeof window !== 'undefined') {
    window.PdfCompress = PdfCompress;
}
