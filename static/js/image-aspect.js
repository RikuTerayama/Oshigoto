/**
 * 縦横比統一ユーティリティ（パディングとクロップ）
 */

class ImageAspect {
    /**
     * 縦横比を統一（パディング方式）
     * @param {HTMLCanvasElement} canvas - Canvas要素
     * @param {string} ratio - 縦横比（'original', '1:1', '4:5', '16:9'）
     * @param {string} bgColor - 背景色（デフォルト: "#ffffff"）
     * @returns {HTMLCanvasElement} - 新しいCanvas
     */
    static padToAspect(canvas, ratio = 'original', bgColor = '#ffffff') {
        if (ratio === 'original') {
            return canvas;
        }

        const currentRatio = canvas.width / canvas.height;
        let targetRatio;

        switch (ratio) {
            case '1:1':
                targetRatio = 1;
                break;
            case '4:5':
                targetRatio = 4 / 5;
                break;
            case '16:9':
                targetRatio = 16 / 9;
                break;
            default:
                return canvas;
        }

        let targetWidth, targetHeight;

        if (currentRatio < targetRatio) {
            // 幅を拡張
            targetWidth = Math.ceil(canvas.height * targetRatio);
            targetHeight = canvas.height;
        } else {
            // 高さを拡張
            targetWidth = canvas.width;
            targetHeight = Math.ceil(canvas.width / targetRatio);
        }

        const newCanvas = document.createElement('canvas');
        newCanvas.width = targetWidth;
        newCanvas.height = targetHeight;
        const ctx = newCanvas.getContext('2d');

        // 背景色で塗りつぶし
        ctx.fillStyle = bgColor;
        ctx.fillRect(0, 0, targetWidth, targetHeight);

        // 元の画像を中央に配置
        const offsetX = (targetWidth - canvas.width) / 2;
        const offsetY = (targetHeight - canvas.height) / 2;
        ctx.drawImage(canvas, offsetX, offsetY);

        return newCanvas;
    }

    /**
     * 縦横比を統一（クロップ方式）
     * @param {HTMLCanvasElement} canvas - Canvas要素
     * @param {string} ratio - 縦横比（'original', '1:1', '4:5', '16:9'）
     * @returns {HTMLCanvasElement} - 新しいCanvas
     */
    static cropToAspect(canvas, ratio = 'original') {
        if (ratio === 'original') {
            return canvas;
        }

        const currentRatio = canvas.width / canvas.height;
        let targetRatio;

        switch (ratio) {
            case '1:1':
                targetRatio = 1;
                break;
            case '4:5':
                targetRatio = 4 / 5;
                break;
            case '16:9':
                targetRatio = 16 / 9;
                break;
            default:
                return canvas;
        }

        let cropWidth, cropHeight;
        let sx = 0, sy = 0;

        if (currentRatio > targetRatio) {
            // 現在の方が横長 → 幅を詰める
            cropHeight = canvas.height;
            cropWidth = Math.floor(canvas.height * targetRatio);
            sx = Math.floor((canvas.width - cropWidth) / 2);
        } else {
            // 現在の方が縦長 → 高さを詰める
            cropWidth = canvas.width;
            cropHeight = Math.floor(canvas.width / targetRatio);
            sy = Math.floor((canvas.height - cropHeight) / 2);
        }

        const newCanvas = document.createElement('canvas');
        newCanvas.width = cropWidth;
        newCanvas.height = cropHeight;
        const ctx = newCanvas.getContext('2d');

        // 中央から切り抜き
        ctx.drawImage(
            canvas,
            sx, sy, cropWidth, cropHeight,
            0, 0, cropWidth, cropHeight
        );

        return newCanvas;
    }
}
