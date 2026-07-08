/**
 * 画像エクスポートユーティリティ
 */

class ImageExport {
    /**
     * CanvasをBlobに変換
     * @param {HTMLCanvasElement} canvas - Canvas要素
     * @param {string} mime - MIMEタイプ（'image/jpeg', 'image/png', 'image/webp'）
     * @param {number} quality - 品質（0.1-1.0、JPEG/WebPのみ）
     * @returns {Promise<Blob>}
     */
    static async canvasToBlob(canvas, mime = 'image/jpeg', quality = 0.9) {
        return new Promise((resolve, reject) => {
            const options = {};
            if (mime === 'image/jpeg' || mime === 'image/webp') {
                options.quality = quality;
            }
            
            canvas.toBlob(
                (blob) => {
                    if (blob) {
                        resolve(blob);
                    } else {
                        reject(new Error('画像変換に失敗しました'));
                    }
                },
                mime,
                options.quality
            );
        });
    }
}
