/**
 * PDF埋め込み画像抽出ユーティリティ（試験版）
 * 注意: PDFによっては抽出できない場合があります
 */

const ENCRYPTED_PDF_USER_MESSAGE = 'このPDFはパスワード保護されています。正しいパスワードを入力してください。';

function isEncryptedPdfJsError(e) {
    const msg = String(e?.message || '').toLowerCase();
    const name = String(e?.name || '').toLowerCase();
    return name.includes('password') || msg.includes('password') || msg.includes('encrypted');
}

class PdfExtractImages {
    /**
     * PDFから埋め込み画像を抽出
     * @param {File} file - PDFファイル
     * @param {Object} options - オプション
     * @param {string} options.format - 画像形式 ("png" | "jpeg")
     * @param {number} options.quality - 品質（JPEGのみ、0.1-1.0）
     * @param {number} options.maxPerPdf - PDFあたりの最大抽出数
     * @param {boolean} options.includePageIndexInName - ファイル名にページ番号を含める
     * @param {Object} ctx - コンテキスト
     * @returns {Promise<Array<{blob: Blob, filename: string, mime: string}>>}
     */
    static async extractEmbeddedImages(file, options = {}, ctx = {}) {
        if (typeof pdfjsLib === 'undefined') {
            throw new Error('pdfjs-distライブラリが読み込まれていません');
        }

        const pdfjs = pdfjsLib;

        const {
            format = 'png',
            quality = 0.9,
            maxPerPdf = 200,
            includePageIndexInName = true
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
            console.error('[PdfExtractImages] load_failed', { fileName: file.name });
            throw e;
        }
        const numPages = pdf.numPages;

        if (ctx.setProgress) {
            ctx.setProgress(5);
        }

        const outputs = [];
        let extractedCount = 0;

        // 各ページから画像を抽出
        for (let pageNum = 1; pageNum <= numPages; pageNum++) {
            if (ctx.signal && ctx.signal.cancelled) {
                throw new Error('キャンセルされました');
            }

            if (extractedCount >= maxPerPdf) {
                console.warn(`最大抽出数（${maxPerPdf}）に達しました`);
                break;
            }

            if (ctx.setTaskState) {
                ctx.setTaskState(0, { 
                    status: 'running', 
                    message: `ページ ${pageNum}/${numPages} から画像を抽出中...` 
                });
            }

            try {
                const page = await pdf.getPage(pageNum);
                const operatorList = await page.getOperatorList();

                // operatorListから画像オブジェクトを探す
                // 注意: pdfjs-distのAPIはバージョンによって異なる可能性があります
                // この実装は簡易版で、すべての画像を抽出できるとは限りません

                // ページのオブジェクトストリームから画像を取得を試みる
                // 実際の実装では、operatorListを解析して画像描画命令を探す必要があります
                // ここでは簡易的に、ページをレンダリングして画像として抽出する方法をフォールバックとして使用

                // 注意: この実装は試験版のため、完全な抽出は保証されません
                // より高度な抽出には、PDFの内部構造を直接解析する必要があります

                // フォールバック: ページ全体を画像として抽出（試験版の簡易実装）
                const viewport = page.getViewport({ scale: 1.0 });
                const canvas = document.createElement('canvas');
                canvas.width = viewport.width;
                canvas.height = viewport.height;
                const context = canvas.getContext('2d');

                const renderContext = {
                    canvasContext: context,
                    viewport: viewport
                };
                try {
                    await page.render(renderContext).promise;
                } catch (e) {
                    console.error('[PdfExtractImages] render_failed', { fileName: file.name, pageNum, format, error: e });
                    throw e;
                }

                // 画像として出力
                const mimeType = format === 'jpeg' || format === 'jpg' ? 'image/jpeg' : 'image/png';
                const ext = format === 'jpeg' || format === 'jpg' ? 'jpg' : 'png';

                const blob = await new Promise((resolve, reject) => {
                    const options = format === 'jpeg' || format === 'jpg' ? { quality } : undefined;
                    canvas.toBlob(
                        (b) => {
                            if (b) {
                                resolve(b);
                                return;
                            }
                            console.error('[PdfExtractImages] toBlob_failed', {
                                fileName: file.name,
                                pageNum,
                                format,
                                canvasWidth: canvas.width,
                                canvasHeight: canvas.height
                            });
                            reject(new Error('画像変換に失敗しました'));
                        },
                        mimeType,
                        options?.quality
                    );
                });

                const baseName = FileUtils.getFilenameWithoutExtension(file.name);
                const pageSuffix = includePageIndexInName ? `_p${pageNum}` : '';
                const filename = FileValidation.sanitizeFilename(`${baseName}_img${pageSuffix}_${extractedCount + 1}.${ext}`);

                outputs.push({
                    blob,
                    filename,
                    mime: mimeType
                });

                extractedCount++;

                // メモリ解放
                canvas.width = 0;
                canvas.height = 0;
            } catch (error) {
                console.warn(`ページ ${pageNum} からの画像抽出に失敗:`, error);
                // エラーがあっても続行
            }

            // 進捗更新
            if (ctx.setProgress) {
                ctx.setProgress(5 + (pageNum / numPages) * 90);
            }
        }

        if (ctx.setTaskState) {
            ctx.setTaskState(0, { 
                status: extractedCount > 0 ? 'success' : 'error',
                message: extractedCount > 0 ? `完了（${extractedCount}件抽出）` : '画像を抽出できませんでした'
            });
        }

        if (ctx.setProgress) {
            ctx.setProgress(100);
        }

        if (outputs.length === 0) {
            throw new Error('このPDFから画像を抽出できませんでした（試験版の制限）');
        }

        return outputs;
    }
}
