/**
 * 画像一括変換処理（v2: バリアント対応）
 */

class ImageBatchConvert {
    /**
     * 最大ピクセル数（幅 x 高さ）
     */
    static MAX_PIXELS = 40000000;
    static MAX_LONG_EDGE = 16384;

    /**
     * 画像のサイズを取得
     * @param {File} file - 画像ファイル
     * @returns {Promise<{width: number, height: number}>}
     */
    static async getImageSize(file) {
        const decoded = await ImageFormatCore.decodeImageFile(file);
        try {
            return { width: decoded.width, height: decoded.height };
        } finally {
            decoded.release();
        }
    }

    /**
     * ピクセル数の上限チェック
     * @param {number} width - 幅
     * @param {number} height - 高さ
     * @returns {boolean}
     */
    static validatePixelCount(width, height) {
        try {
            ImageFormatCore.validateImageLimits(width, height, this.MAX_PIXELS, this.MAX_LONG_EDGE);
            return true;
        } catch (error) {
            return false;
        }
    }

    /**
     * バリアントで画像を変換
     * @param {File} file - 入力画像ファイル
     * @param {Object} options - 変換オプション
     * @param {string} options.outputFormat - 出力形式
     * @param {number} options.quality - 品質
     * @param {Object} variant - バリアント
     * @param {number} variant.width - リサイズ幅（0でリサイズなし）
     * @param {string} variant.suffix - サフィックス（空なら自動生成）
     * @param {boolean} options.preventUpscale - アップスケール抑止
     * @param {Object} ctx - コンテキスト
     * @returns {Promise<{blob: Blob, filename: string, mime: string, width: number, height: number}>}
     */
    static async convertImageWithVariant(file, options, variant, ctx = {}) {
        const {
            outputFormat = 'jpeg',
            quality = 0.9,
            preventUpscale = false
        } = options;

        const normalizedFormat = outputFormat.toLowerCase() === 'jpg' ? 'jpeg' : outputFormat.toLowerCase();
        if (!['jpeg', 'png', 'webp', 'avif'].includes(normalizedFormat)) {
            throw new Error(`未対応の出力形式: ${outputFormat}`);
        }
        let decoded;
        let canvas;
        try {
            if (ctx.signal && ctx.signal.cancelled) throw new Error('キャンセルされました');
            decoded = await ImageFormatCore.decodeImageFile(file);
            ImageFormatCore.validateImageLimits(decoded.width, decoded.height, this.MAX_PIXELS, this.MAX_LONG_EDGE);

            // リサイズ計算
            let targetWidth = variant.width || 0;
            let outputWidth = decoded.width;
            let outputHeight = decoded.height;

            if (targetWidth > 0) {
                if (preventUpscale && decoded.width <= targetWidth) targetWidth = 0;

                if (targetWidth > 0 && decoded.width > targetWidth) {
                    const ratio = targetWidth / decoded.width;
                    outputWidth = targetWidth;
                    outputHeight = Math.max(1, Math.round(decoded.height * ratio));
                }
            }
            ImageFormatCore.validateImageLimits(outputWidth, outputHeight, this.MAX_PIXELS, this.MAX_LONG_EDGE);
            if (ctx.signal && ctx.signal.cancelled) throw new Error('キャンセルされました');

            canvas = document.createElement('canvas');
            canvas.width = outputWidth;
            canvas.height = outputHeight;
            const outputContext = canvas.getContext('2d');
            if (!outputContext) throw new Error('画像変換を開始できませんでした。');
            if (normalizedFormat === 'jpeg') {
                outputContext.fillStyle = '#ffffff';
                outputContext.fillRect(0, 0, outputWidth, outputHeight);
            }
            outputContext.drawImage(decoded.source, 0, 0, outputWidth, outputHeight);

            const mimeType = ImageFormatCore.FORMAT_MIME[normalizedFormat];
            const blob = await new Promise((resolve, reject) => {
                canvas.toBlob((result) => {
                    if (result) resolve(result);
                    else reject(new Error(normalizedFormat === 'avif' ? 'このブラウザではAVIF形式で保存できません。' : '画像変換に失敗しました'));
                }, mimeType, normalizedFormat === 'png' ? undefined : quality);
            });
            ImageFormatCore.validateEncodedBuffer(await blob.slice(0, 4096).arrayBuffer(), normalizedFormat, blob.type);
            return { blob, mime: mimeType, width: outputWidth, height: outputHeight };
        } finally {
            if (decoded) decoded.release();
            if (canvas) {
                canvas.width = 0;
                canvas.height = 0;
            }
        }
    }

    /**
     * HTMLImageElementで画像を読み込み（フォールバック用）
     * @param {File} file - 画像ファイル
     * @returns {Promise<HTMLImageElement>}
     */
    static loadImageElement(file) {
        return new Promise((resolve, reject) => {
            const img = new Image();
            const url = URL.createObjectURL(file);
            img.onload = () => {
                URL.revokeObjectURL(url);
                resolve(img);
            };
            img.onerror = () => {
                URL.revokeObjectURL(url);
                reject(new Error('画像の読み込みに失敗しました'));
            };
            img.src = url;
        });
    }

    /**
     * サフィックスを自動生成
     * @param {number} width - 幅（0の場合は'original'）
     * @returns {string}
     */
    static generateSuffix(width) {
        if (width === 0) {
            return 'original';
        }
        return `w${width}`;
    }
}

if (typeof window !== 'undefined') {
    window.ImageBatchConvert = ImageBatchConvert;
}
