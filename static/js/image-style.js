/**
 * 画像スタイル適用（余白・角丸・枠）
 * image-cleanup パイプラインの1段として使用
 */

function drawRoundRectPath(ctx, x, y, w, h, r) {
    if (typeof ctx.roundRect === 'function') {
        ctx.roundRect(x, y, w, h, r);
        return;
    }
    r = Math.min(r, w / 2, h / 2);
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
}

class ImageStyle {
    /**
     * 画像周りに均等パディングを追加
     * @param {HTMLCanvasElement} canvas - Canvas要素
     * @param {number} paddingPx - 余白（px）。0以下なら何もしない
     * @param {string} bgColor - 背景色（#rrggbb または 'transparent'）
     * @returns {HTMLCanvasElement}
     */
    static applyPadding(canvas, paddingPx, bgColor = '#ffffff') {
        if (paddingPx <= 0 || !canvas) return canvas;

        const w = canvas.width;
        const h = canvas.height;
        const newCanvas = document.createElement('canvas');
        newCanvas.width = w + 2 * paddingPx;
        newCanvas.height = h + 2 * paddingPx;
        const ctx = newCanvas.getContext('2d');

        if (bgColor !== 'transparent' && bgColor !== '') {
            ctx.fillStyle = bgColor;
            ctx.fillRect(0, 0, newCanvas.width, newCanvas.height);
        }
        ctx.drawImage(canvas, paddingPx, paddingPx, w, h);
        return newCanvas;
    }

    /**
     * 角丸を適用（角部分は背景色で塗りつぶし、または透明）
     * @param {HTMLCanvasElement} canvas - Canvas要素
     * @param {number} radiusPx - 角丸半径（px）。0以下なら何もしない
     * @param {string} bgColor - 角部分の背景色（#rrggbb または 'transparent'）
     * @returns {HTMLCanvasElement}
     */
    static applyRoundedCorners(canvas, radiusPx, bgColor = '#ffffff') {
        if (radiusPx <= 0 || !canvas) return canvas;

        const w = canvas.width;
        const h = canvas.height;
        const r = Math.min(radiusPx, w / 2, h / 2);
        const newCanvas = document.createElement('canvas');
        newCanvas.width = w;
        newCanvas.height = h;
        const ctx = newCanvas.getContext('2d');

        if (bgColor !== 'transparent' && bgColor !== '') {
            ctx.fillStyle = bgColor;
            drawRoundRectPath(ctx, 0, 0, w, h, r);
            ctx.fill();
        }
        ctx.save();
        drawRoundRectPath(ctx, 0, 0, w, h, r);
        ctx.clip();
        ctx.drawImage(canvas, 0, 0);
        ctx.restore();
        return newCanvas;
    }

    /**
     * 枠（ボーダー）を追加
     * @param {HTMLCanvasElement} canvas - Canvas要素
     * @param {number} borderWidthPx - 枠の幅（px）。0以下なら何もしない
     * @param {string} borderColor - 枠の色（#rrggbb 等）
     * @returns {HTMLCanvasElement}
     */
    static applyBorder(canvas, borderWidthPx, borderColor = '#000000') {
        if (borderWidthPx <= 0 || !canvas) return canvas;

        const w = canvas.width;
        const h = canvas.height;
        const b = borderWidthPx;
        const newCanvas = document.createElement('canvas');
        newCanvas.width = w + 2 * b;
        newCanvas.height = h + 2 * b;
        const ctx = newCanvas.getContext('2d');

        ctx.fillStyle = borderColor;
        ctx.fillRect(0, 0, newCanvas.width, newCanvas.height);
        ctx.drawImage(canvas, b, b, w, h);
        return newCanvas;
    }
}
