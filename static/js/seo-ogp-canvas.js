/**
 * OGP画像生成（Canvas）
 */

class SeoOgpCanvas {
    /**
     * OGP画像のCanvasを作成
     * @param {Object} options - オプション
     * @param {string} options.presetId - プリセットID
     * @param {string} options.title - タイトル
     * @param {string} options.subtitle - サブタイトル
     * @param {string} options.badge - バッジ
     * @param {string} options.author - 作成者
     * @param {string} options.date - 日付
     * @param {string} options.layout - レイアウト（'left' | 'center'）
     * @param {string} options.background - 背景（'light' | 'dark'）
     * @returns {HTMLCanvasElement}
     */
    static createOgpCanvas(options) {
        const preset = SeoOgpPresets.getPresetById(options.presetId);
        if (!preset) {
            throw new Error('無効なプリセットIDです');
        }

        const canvas = document.createElement('canvas');
        canvas.width = preset.width;
        canvas.height = preset.height;

        this.drawOgp(canvas, options);

        return canvas;
    }

    /**
     * OGP画像を描画
     * @param {HTMLCanvasElement} canvas - Canvas要素
     * @param {Object} options - オプション
     */
    static drawOgp(canvas, options) {
        const ctx = canvas.getContext('2d');
        const width = canvas.width;
        const height = canvas.height;

        // 背景色
        const bgColor = options.background === 'dark' 
            ? '#1A1A1A' 
            : '#FFFFFF';
        ctx.fillStyle = bgColor;
        ctx.fillRect(0, 0, width, height);

        // グラデーション装飾（オプション）
        if (options.background === 'dark') {
            const gradient = ctx.createLinearGradient(0, 0, width, height);
            gradient.addColorStop(0, 'rgba(74, 158, 255, 0.1)');
            gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');
            ctx.fillStyle = gradient;
            ctx.fillRect(0, 0, width, height);
        }

        // テキスト色
        const textColor = options.background === 'dark' ? '#FFFFFF' : '#1A1A1A';
        const subTextColor = options.background === 'dark' 
            ? 'rgba(255, 255, 255, 0.7)' 
            : 'rgba(0, 0, 0, 0.6)';

        // レイアウト設定
        const isLeft = options.layout === 'left';
        const padding = 60;
        const maxWidth = width - (padding * 2);
        let currentY = padding + 40;

        // バッジ（左上）
        if (options.badge) {
            ctx.fillStyle = '#4A9EFF';
            ctx.font = 'bold 24px "Noto Sans JP", sans-serif';
            const badgeMetrics = ctx.measureText(options.badge);
            const badgeWidth = badgeMetrics.width + 20;
            const badgeHeight = 36;
            ctx.fillRect(padding, padding, badgeWidth, badgeHeight);
            ctx.fillStyle = '#FFFFFF';
            ctx.textBaseline = 'middle';
            ctx.fillText(options.badge, padding + 10, padding + badgeHeight / 2);
            currentY += badgeHeight + 20;
        }

        // タイトル
        if (options.title) {
            ctx.fillStyle = textColor;
            ctx.font = 'bold 48px "Noto Sans JP", sans-serif';
            ctx.textBaseline = 'top';
            const titleLines = this.wrapText(ctx, options.title, maxWidth, 48);
            titleLines.forEach((line, index) => {
                const x = isLeft ? padding : (width - ctx.measureText(line).width) / 2;
                ctx.fillText(line, x, currentY);
                currentY += 60;
            });
            currentY += 20;
        }

        // サブタイトル
        if (options.subtitle) {
            ctx.fillStyle = subTextColor;
            ctx.font = '32px "Noto Sans JP", sans-serif';
            ctx.textBaseline = 'top';
            const subtitleLines = this.wrapText(ctx, options.subtitle, maxWidth, 32);
            subtitleLines.forEach((line) => {
                const x = isLeft ? padding : (width - ctx.measureText(line).width) / 2;
                ctx.fillText(line, x, currentY);
                currentY += 45;
            });
            currentY += 30;
        }

        // 作成者と日付（下部）
        const footerY = height - padding - 30;
        if (options.author || options.date) {
            ctx.fillStyle = subTextColor;
            ctx.font = '24px "Noto Sans JP", sans-serif';
            ctx.textBaseline = 'bottom';
            
            let footerText = '';
            if (options.author) {
                footerText += options.author;
            }
            if (options.date) {
                if (footerText) footerText += ' • ';
                footerText += options.date;
            }
            
            if (footerText) {
                const x = isLeft ? padding : (width - ctx.measureText(footerText).width) / 2;
                ctx.fillText(footerText, x, footerY);
            }
        }
    }

    /**
     * テキストを折り返す
     * @param {CanvasRenderingContext2D} ctx - Canvasコンテキスト
     * @param {string} text - テキスト
     * @param {number} maxWidth - 最大幅
     * @param {number} fontSize - フォントサイズ
     * @returns {string[]}
     */
    static wrapText(ctx, text, maxWidth, fontSize) {
        const words = text.split('');
        const lines = [];
        let currentLine = '';

        for (let i = 0; i < words.length; i++) {
            const char = words[i];
            const testLine = currentLine + char;
            const metrics = ctx.measureText(testLine);
            
            if (metrics.width > maxWidth && currentLine.length > 0) {
                lines.push(currentLine);
                currentLine = char;
            } else {
                currentLine = testLine;
            }
        }
        
        if (currentLine.length > 0) {
            lines.push(currentLine);
        }

        return lines.length > 0 ? lines : [text];
    }

    /**
     * dataURLをBlobに変換（toBlob未対応・null時のフォールバック用）
     * data:<mime>;base64,<payload> を想定。base64でない場合は fetch にフォールバック
     * @param {string} dataURL - data:image/... 形式の文字列
     * @returns {Promise<Blob>}
     */
    static dataURLToBlob(dataURL) {
        if (!dataURL || typeof dataURL !== 'string' || !dataURL.startsWith('data:')) {
            return Promise.reject(new Error('無効な dataURL です'));
        }
        const commaIndex = dataURL.indexOf(',');
        if (commaIndex === -1) {
            return Promise.reject(new Error('dataURL の形式が不正です'));
        }
        const header = dataURL.slice(0, commaIndex);
        const payload = dataURL.slice(commaIndex + 1);
        const base64 = header.toLowerCase().endsWith(';base64');
        const mime = (header.slice(5).split(';')[0] || 'application/octet-stream').trim();

        if (base64 && payload) {
            try {
                const binaryString = atob(payload);
                const len = binaryString.length;
                const u8 = new Uint8Array(len);
                for (let i = 0; i < len; i++) {
                    u8[i] = binaryString.charCodeAt(i);
                }
                return Promise.resolve(new Blob([u8], { type: mime }));
            } catch (e) {
                return Promise.reject(new Error('dataURL の base64 デコードに失敗しました: ' + (e && e.message ? e.message : String(e))));
            }
        }

        // base64 でない dataURL（rare）は fetch で取得
        try {
            return fetch(dataURL).then(r => r.blob());
        } catch (e) {
            return Promise.reject(new Error('dataURL の Blob 変換に失敗しました: ' + (e && e.message ? e.message : String(e))));
        }
    }

    /**
     * CanvasをBlobに変換
     * toBlob未対応またはblobがnullの場合はtoDataURLでフォールバック
     * @param {HTMLCanvasElement} canvas - Canvas要素
     * @param {string} format - 形式（'png' | 'jpeg'）
     * @param {number} quality - 品質（0.1-1.0、JPEGのみ）
     * @returns {Promise<Blob>}
     */
    static async canvasToBlob(canvas, format = 'png', quality = 0.9) {
        const mimeType = format === 'jpeg' || format === 'jpg'
            ? 'image/jpeg'
            : 'image/png';
        const isPng = mimeType === 'image/png';

        const fallbackViaDataURL = () => {
            try {
                const qualityArg = isPng ? undefined : quality;
                const dataURL = canvas.toDataURL(mimeType, qualityArg);
                return this.dataURLToBlob(dataURL);
            } catch (e) {
                return Promise.reject(new Error('画像変換に失敗しました（toDataURL: ' + (e && e.message ? e.message : 'unknown') + ')'));
            }
        };

        if (typeof canvas.toBlob !== 'function') {
            return fallbackViaDataURL();
        }

        return new Promise((resolve, reject) => {
            const callback = (blob) => {
                if (blob) {
                    resolve(blob);
                } else {
                    fallbackViaDataURL().then(resolve).catch(reject);
                }
            };
            if (isPng) {
                canvas.toBlob(callback, mimeType);
            } else {
                canvas.toBlob(callback, mimeType, quality);
            }
        });
    }
}

window.SeoOgpCanvas = SeoOgpCanvas;
console.debug('[seo-ogp-canvas] loaded', true);
