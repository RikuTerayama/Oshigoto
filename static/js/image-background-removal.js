/**
 * 背景除去ユーティリティ（@imgly/background-removal使用）
 */

class ImageBackgroundRemoval {
    /**
     * 品質に応じた最大長辺を取得
     * @param {string} quality - 品質（'low' | 'medium' | 'high'）
     * @returns {number}
     */
    static getMaxLongEdge(quality) {
        switch (quality) {
            case 'low':
                return 1024;
            case 'medium':
                return 1536;
            case 'high':
                return 2560;
            default:
                return 1536;
        }
    }

    /**
     * Canvasから背景を除去
     * @param {HTMLCanvasElement} inputCanvas - 入力Canvas
     * @param {Object} options - オプション
     * @param {string} options.quality - 品質（'low' | 'medium' | 'high'）
     * @param {Object} ctx - コンテキスト
     * @returns {Promise<HTMLCanvasElement>} - 透明背景を持つCanvas
     */
    static async removeBackgroundFromCanvas(inputCanvas, options = {}, ctx = {}) {
        const { quality = 'medium' } = options;

        try {
            // dynamic importでライブラリを読み込む（クライアント側のみ）
            // 注意: このライブラリはブラウザ環境でのみ動作します
            let removeBackground;
            try {
                const mod = await import('@imgly/background-removal');
                removeBackground = mod.removeBackground || mod.default?.removeBackground;
                if (!removeBackground) {
                    throw new Error('背景除去ライブラリの読み込みに失敗しました');
                }
            } catch (importError) {
                throw new Error(`背景除去ライブラリが利用できません: ${importError.message}。ブラウザ環境で実行してください。`);
            }

            // 品質に応じて入力画像を縮小（処理速度向上）
            const maxLongEdge = this.getMaxLongEdge(quality);
            const longEdge = Math.max(inputCanvas.width, inputCanvas.height);
            
            let workCanvas = inputCanvas;
            if (longEdge > maxLongEdge) {
                const scale = maxLongEdge / longEdge;
                const scaledCanvas = document.createElement('canvas');
                scaledCanvas.width = Math.round(inputCanvas.width * scale);
                scaledCanvas.height = Math.round(inputCanvas.height * scale);
                const scaledCtx = scaledCanvas.getContext('2d');
                scaledCtx.drawImage(inputCanvas, 0, 0, scaledCanvas.width, scaledCanvas.height);
                workCanvas = scaledCanvas;
            }

            if (ctx.signal && ctx.signal.cancelled) {
                throw new Error('キャンセルされました');
            }

            // 背景除去を実行
            if (ctx.setTaskState) {
                ctx.setTaskState(ctx.index || 0, { status: 'running', message: '背景除去中...' });
            }

            // workCanvasをBlobに変換
            const blob = await new Promise((resolve, reject) => {
                workCanvas.toBlob(
                    (b) => b ? resolve(b) : reject(new Error('Blob変換に失敗しました')),
                    'image/png'
                );
            });

            // 背景除去を実行
            const blobWithoutBackground = await removeBackground(blob);

            if (ctx.signal && ctx.signal.cancelled) {
                throw new Error('キャンセルされました');
            }

            // 結果をCanvasに変換
            const resultCanvas = await this.blobToCanvas(blobWithoutBackground);

            // 元のサイズに戻す（縮小していた場合）
            if (workCanvas !== inputCanvas) {
                const finalCanvas = document.createElement('canvas');
                finalCanvas.width = inputCanvas.width;
                finalCanvas.height = inputCanvas.height;
                const finalCtx = finalCanvas.getContext('2d');
                finalCtx.drawImage(resultCanvas, 0, 0, finalCanvas.width, finalCanvas.height);
                return finalCanvas;
            }

            return resultCanvas;
        } catch (error) {
            // エラーメッセージを改善
            if (error.message.includes('キャンセル')) {
                throw error;
            }
            throw new Error(`背景除去に失敗しました: ${error.message}。形式が特殊、またはメモリ不足の可能性があります。`);
        }
    }

    /**
     * BlobをCanvasに変換
     * @param {Blob} blob - 画像Blob
     * @returns {Promise<HTMLCanvasElement>}
     */
    static blobToCanvas(blob) {
        return new Promise((resolve, reject) => {
            const img = new Image();
            const url = URL.createObjectURL(blob);
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
}
