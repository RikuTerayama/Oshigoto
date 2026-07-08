/**
 * 画像一括変換処理（v2: バリアント対応）
 */

class ImageBatchConvert {
    /**
     * 最大ピクセル数（幅 x 高さ）
     */
    static MAX_PIXELS = 80000000; // 80,000,000ピクセル

    /**
     * 画像のサイズを取得
     * @param {File} file - 画像ファイル
     * @returns {Promise<{width: number, height: number}>}
     */
    static async getImageSize(file) {
        try {
            const bitmap = await createImageBitmap(file);
            const size = { width: bitmap.width, height: bitmap.height };
            bitmap.close();
            return size;
        } catch (e) {
            // フォールバック: HTMLImageElementを使用
            const img = await ImageConverter.loadImageElement(file);
            return { width: img.width, height: img.height };
        }
    }

    /**
     * ピクセル数の上限チェック
     * @param {number} width - 幅
     * @param {number} height - 高さ
     * @returns {boolean}
     */
    static validatePixelCount(width, height) {
        const pixels = width * height;
        return pixels <= this.MAX_PIXELS;
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

        // 画像サイズを取得（ピクセル上限チェック用）
        const originalSize = await this.getImageSize(file);
        
        // ピクセル上限チェック
        if (!this.validatePixelCount(originalSize.width, originalSize.height)) {
            throw new Error(`画像サイズが大きすぎます（${originalSize.width}x${originalSize.height}）。最大80,000,000ピクセルまで対応しています。`);
        }

        // 画像を読み込み
        let imageBitmap;
        try {
            imageBitmap = await createImageBitmap(file);
        } catch (e) {
            // フォールバック: HTMLImageElementを使用
            const img = await this.loadImageElement(file);
            const canvas = document.createElement('canvas');
            canvas.width = img.width;
            canvas.height = img.height;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(img, 0, 0);
            imageBitmap = await createImageBitmap(canvas);
        }

        // リサイズ計算
        let targetWidth = variant.width || 0;
        let outputWidth = imageBitmap.width;
        let outputHeight = imageBitmap.height;

        if (targetWidth > 0) {
            // アップスケール抑止
            if (preventUpscale && imageBitmap.width <= targetWidth) {
                targetWidth = 0; // リサイズなし
            }

            if (targetWidth > 0 && imageBitmap.width > targetWidth) {
                const ratio = targetWidth / imageBitmap.width;
                outputWidth = targetWidth;
                outputHeight = Math.round(imageBitmap.height * ratio);
            }
        }

        // Canvasに描画
        const canvas = document.createElement('canvas');
        canvas.width = outputWidth;
        canvas.height = outputHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(imageBitmap, 0, 0, outputWidth, outputHeight);

        // MIMEタイプと品質設定
        let mimeType;
        let blobOptions = {};
        switch (outputFormat.toLowerCase()) {
            case 'jpeg':
            case 'jpg':
                mimeType = 'image/jpeg';
                blobOptions.quality = quality;
                break;
            case 'webp':
                mimeType = 'image/webp';
                blobOptions.quality = quality;
                break;
            case 'png':
                mimeType = 'image/png';
                break;
            default:
                throw new Error(`未対応の出力形式: ${outputFormat}`);
        }

        // Blobに変換
        const blob = await new Promise((resolve, reject) => {
            canvas.toBlob(
                (blob) => {
                    if (blob) {
                        resolve(blob);
                    } else {
                        reject(new Error('画像変換に失敗しました'));
                    }
                },
                mimeType,
                blobOptions.quality
            );
        });

        imageBitmap.close();

        return {
            blob,
            mime: mimeType,
            width: outputWidth,
            height: outputHeight
        };
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
console.debug('[image-batch-convert] loaded', typeof window !== 'undefined' ? !!window.ImageBatchConvert : 'no-window');
