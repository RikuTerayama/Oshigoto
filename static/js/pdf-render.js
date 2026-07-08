/**
 * PDF→画像レンダリングユーティリティ（pdfjs-dist使用）
 */

const ENCRYPTED_PDF_USER_MESSAGE = 'このPDFはパスワード保護されています。正しいパスワードを入力してください。';

/** pdf.js の暗号化/パスワード系エラーかどうか判定 */
function isEncryptedPdfJsError(e) {
    const msg = String(e?.message || '').toLowerCase();
    const name = String(e?.name || '').toLowerCase();
    return name.includes('password') || msg.includes('password') || msg.includes('encrypted');
}

/**
 * canvas を Blob に変換。null の場合は toBlob_failed をログし、toDataURL フォールバックを試す
 */
function toBlobWithLog(canvas, mimeType, quality, fileName, pageNum, format) {
    return new Promise((resolve, reject) => {
        canvas.toBlob((b) => {
            if (b) {
                resolve(b);
                return;
            }
            console.error('[PdfRender] toBlob_failed', {
                fileName,
                pageNum,
                format,
                canvasWidth: canvas.width,
                canvasHeight: canvas.height,
                mimeType
            });
            // フォールバック: toDataURL → Blob
            try {
                const dataURL = quality != null
                    ? canvas.toDataURL(mimeType, quality)
                    : canvas.toDataURL(mimeType);
                if (!dataURL || dataURL.slice(0, 5) !== 'data:') {
                    reject(new Error('画像変換に失敗しました'));
                    return;
                }
                const bin = atob(dataURL.split(',')[1]);
                const arr = new Uint8Array(bin.length);
                for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
                resolve(new Blob([arr], { type: mimeType }));
            } catch (e) {
                console.error('[PdfRender] toBlob_failed (toDataURL fallback error)', { fileName, pageNum, format, error: e });
                reject(new Error('画像変換に失敗しました'));
            }
        }, mimeType, quality);
    });
}

class PdfRender {
    /**
     * PDFを画像に変換
     * @param {File} file - PDFファイル
     * @param {Object} options - オプション
     * @param {string} options.format - 画像形式 ("png" | "jpeg")
     * @param {number} options.scale - スケール（例: 1.0, 1.5, 2.0）
     * @param {number} options.quality - 品質（JPEGのみ、0.1-1.0）
     * @param {Object} ctx - コンテキスト
     * @returns {Promise<Array<{blob: Blob, filename: string, mime: string}>>}
     */
    static async pdfToImages(file, options = {}, ctx = {}) {
        // pdfjs-distはグローバル変数として読み込まれる想定
        if (typeof pdfjsLib === 'undefined') {
            throw new Error('pdfjs-distライブラリが読み込まれていません');
        }
        
        const pdfjs = pdfjsLib;

        const {
            format = 'png',
            scale = 1.0,
            quality = 0.9
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
            console.error('[PdfRender] load_failed', { fileName: file.name, format });
            throw e;
        }
        const numPages = pdf.numPages;

        if (ctx.setProgress) {
            ctx.setProgress(10);
        }

        const outputs = [];

        for (let pageNum = 1; pageNum <= numPages; pageNum++) {
            if (ctx.signal && ctx.signal.cancelled) {
                throw new Error('キャンセルされました');
            }

            if (ctx.setTaskState) {
                ctx.setTaskState(0, { 
                    status: 'running', 
                    message: `ページ ${pageNum}/${numPages} を変換中...` 
                });
            }

            const page = await pdf.getPage(pageNum);
            const viewport = page.getViewport({ scale });

            // Canvasを作成
            const canvas = document.createElement('canvas');
            canvas.width = viewport.width;
            canvas.height = viewport.height;
            const context = canvas.getContext('2d');

            // ページをレンダリング
            const renderContext = {
                canvasContext: context,
                viewport: viewport
            };
            try {
                await page.render(renderContext).promise;
            } catch (e) {
                console.error('[PdfRender] render_failed', { fileName: file.name, pageNum, format, error: e });
                throw e;
            }

            // Blobに変換
            let blob;
            let mimeType;
            let ext;

            if (format === 'jpeg' || format === 'jpg') {
                mimeType = 'image/jpeg';
                ext = 'jpg';
                blob = await toBlobWithLog(canvas, mimeType, quality, file.name, pageNum, format);
            } else {
                mimeType = 'image/png';
                ext = 'png';
                blob = await toBlobWithLog(canvas, mimeType, undefined, file.name, pageNum, format);
            }

            const baseName = FileUtils.getFilenameWithoutExtension(file.name);
            const filename = FileValidation.sanitizeFilename(`${baseName}_p${pageNum}.${ext}`);

            outputs.push({
                blob,
                filename,
                mime: mimeType
            });

            // 進捗更新
            if (ctx.setProgress) {
                ctx.setProgress(10 + (pageNum / numPages) * 90);
            }

            // メモリ解放
            canvas.width = 0;
            canvas.height = 0;
        }

        if (ctx.setTaskState) {
            ctx.setTaskState(0, { status: 'success', message: '完了' });
        }

        return outputs;
    }
}
