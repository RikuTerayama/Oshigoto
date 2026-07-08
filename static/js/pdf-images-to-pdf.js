/**
 * 画像→PDF変換ユーティリティ
 */

class PdfImagesToPdf {
    /**
     * 複数画像から1つのPDFを作成
     * @param {File[]} files - 画像ファイル（png/jpg/webp）
     * @param {Object} options - オプション
     * @param {string} options.pageSize - ページサイズ ("auto" | "a4" | "letter")
     * @param {string} options.fit - フィット方法 ("contain" | "cover")
     * @param {number} options.margin - マージン（pt）
     * @param {string} options.background - 背景色
     * @param {Object} ctx - コンテキスト
     * @returns {Promise<Array<{blob: Blob, filename: string, mime: string}>>}
     */
    static async imagesToPdf(files, options = {}, ctx = {}) {
        if (typeof PDFLib === 'undefined') {
            throw new Error('PDFLibライブラリが読み込まれていません');
        }

        const { PDFDocument, rgb } = PDFLib;

        const {
            pageSize = 'auto',
            fit = 'contain',
            margin = 24,
            background = '#FFFFFF'
        } = options;

        // ページサイズ定義（pt単位）
        const pageSizes = {
            a4: { width: 595, height: 842 },
            letter: { width: 612, height: 792 }
        };

        if (ctx.signal && ctx.signal.cancelled) {
            throw new Error('キャンセルされました');
        }

        const pdf = await PDFDocument.create();
        const bgColor = this.parseColor(background);

        // 各画像を処理
        for (let i = 0; i < files.length; i++) {
            if (ctx.signal && ctx.signal.cancelled) {
                throw new Error('キャンセルされました');
            }

            const file = files[i];
            if (ctx.setTaskState) {
                ctx.setTaskState(i, { status: 'running', message: '読み込み中...' });
            }
            if (ctx.setProgress) {
                ctx.setProgress((i / files.length) * 90);
            }

            try {
                // 画像を読み込み
                let imageBytes;
                let imageType;

                if (file.type === 'image/webp') {
                    // WebPはCanvas経由でPNG化
                    const img = await this.loadImageToCanvas(file);
                    imageBytes = await this.canvasToPng(img);
                    imageType = 'png';
                } else {
                    const arrayBuffer = await file.arrayBuffer();
                    imageBytes = arrayBuffer;
                    imageType = file.type.includes('png') ? 'png' : 'jpg';
                }

                // pdf-libで画像を埋め込み
                let pdfImage;
                if (imageType === 'png') {
                    pdfImage = await pdf.embedPng(imageBytes);
                } else {
                    pdfImage = await pdf.embedJpg(imageBytes);
                }

                // ページサイズを決定
                let pageWidth, pageHeight;
                const imageDims = pdfImage.scale(1);

                if (pageSize === 'auto') {
                    // 画像サイズに合わせる
                    pageWidth = imageDims.width;
                    pageHeight = imageDims.height;
                } else {
                    // 指定サイズ
                    const size = pageSizes[pageSize];
                    pageWidth = size.width;
                    pageHeight = size.height;
                }

                // ページを追加
                const page = pdf.addPage([pageWidth, pageHeight]);

                // 背景を塗りつぶし
                page.drawRectangle({
                    x: 0,
                    y: 0,
                    width: pageWidth,
                    height: pageHeight,
                    color: bgColor
                });

                // 画像を配置
                if (pageSize === 'auto') {
                    // 画像サイズそのまま
                    page.drawImage(pdfImage, {
                        x: 0,
                        y: 0,
                        width: imageDims.width,
                        height: imageDims.height
                    });
                } else {
                    // containでフィット
                    const contentWidth = pageWidth - (margin * 2);
                    const contentHeight = pageHeight - (margin * 2);
                    const scale = Math.min(
                        contentWidth / imageDims.width,
                        contentHeight / imageDims.height
                    );
                    const scaledWidth = imageDims.width * scale;
                    const scaledHeight = imageDims.height * scale;
                    const x = (pageWidth - scaledWidth) / 2;
                    const y = (pageHeight - scaledHeight) / 2;

                    page.drawImage(pdfImage, {
                        x: x,
                        y: y,
                        width: scaledWidth,
                        height: scaledHeight
                    });
                }

                if (ctx.setTaskState) {
                    ctx.setTaskState(i, { status: 'success', message: '完了' });
                }
            } catch (error) {
                if (ctx.setTaskState) {
                    ctx.setTaskState(i, { status: 'error', message: error.message || 'エラー' });
                }
                throw new Error(`${file.name}の処理に失敗しました: ${error.message}`);
            }
        }

        if (ctx.signal && ctx.signal.cancelled) {
            throw new Error('キャンセルされました');
        }

        if (ctx.setTaskState) {
            ctx.setTaskState(0, { status: 'running', message: 'PDFを保存中...' });
        }
        if (ctx.setProgress) {
            ctx.setProgress(95);
        }

        // PDFを保存
        const pdfBytes = await pdf.save();
        const blob = new Blob([pdfBytes], { type: 'application/pdf' });

        if (ctx.setProgress) {
            ctx.setProgress(100);
        }

        const baseName = files.length > 0 
            ? FileUtils.getFilenameWithoutExtension(files[0].name)
            : 'images';
        const filename = FileValidation.sanitizeFilename(`${baseName}_from_images.pdf`);

        return [{
            blob,
            filename,
            mime: 'application/pdf'
        }];
    }

    /**
     * 画像をCanvasに読み込み
     * @param {File} file - 画像ファイル
     * @returns {Promise<HTMLCanvasElement>}
     */
    static loadImageToCanvas(file) {
        return new Promise((resolve, reject) => {
            const img = new Image();
            const url = URL.createObjectURL(file);
            img.onload = () => {
                URL.revokeObjectURL(url);
                const canvas = document.createElement('canvas');
                canvas.width = img.width;
                canvas.height = img.height;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0);
                resolve(canvas);
            };
            img.onerror = () => {
                URL.revokeObjectURL(url);
                reject(new Error('画像の読み込みに失敗しました'));
            };
            img.src = url;
        });
    }

    /**
     * CanvasをPNGに変換
     * @param {HTMLCanvasElement} canvas - Canvas要素
     * @returns {Promise<ArrayBuffer>}
     */
    static canvasToPng(canvas) {
        return new Promise((resolve, reject) => {
            canvas.toBlob(
                (blob) => {
                    if (blob) {
                        blob.arrayBuffer().then(resolve).catch(reject);
                    } else {
                        reject(new Error('PNG変換に失敗しました'));
                    }
                },
                'image/png'
            );
        });
    }

    /**
     * 色文字列をrgbに変換
     * @param {string} color - 色文字列（例: "#FFFFFF"）
     * @returns {Object} - rgbオブジェクト
     */
    static parseColor(color) {
        if (typeof PDFLib === 'undefined') {
            throw new Error('PDFLibライブラリが読み込まれていません');
        }
        const { rgb } = PDFLib;
        if (color.startsWith('#')) {
            const r = parseInt(color.slice(1, 3), 16) / 255;
            const g = parseInt(color.slice(3, 5), 16) / 255;
            const b = parseInt(color.slice(5, 7), 16) / 255;
            return rgb(r, g, b);
        }
        return rgb(1, 1, 1); // デフォルトは白
    }
}
