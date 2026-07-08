/**
 * 画像読み込みユーティリティ
 */

class ImageLoad {
    /**
     * 画像ファイルをImageBitmapに読み込む
     * @param {File} file - 画像ファイル
     * @returns {Promise<ImageBitmap>}
     */
    static async loadToBitmap(file) {
        try {
            // createImageBitmap を優先（より効率的）
            return await createImageBitmap(file);
        } catch (e) {
            // フォールバック: HTMLImageElementを使用
            const img = await this.loadImageElement(file);
            const canvas = document.createElement('canvas');
            canvas.width = img.width;
            canvas.height = img.height;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(img, 0, 0);
            return await createImageBitmap(canvas);
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
     * ImageBitmapをCanvasに描画
     * @param {ImageBitmap} bitmap - ImageBitmap
     * @returns {HTMLCanvasElement}
     */
    static bitmapToCanvas(bitmap) {
        const canvas = document.createElement('canvas');
        canvas.width = bitmap.width;
        canvas.height = bitmap.height;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(bitmap, 0, 0);
        return canvas;
    }
}
