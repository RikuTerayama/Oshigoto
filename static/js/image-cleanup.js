/**
 * 画像クリーンアップ処理
 * 透過→白背景、余白トリム、縦横比統一のパイプライン
 */

class ImageCleanup {
    /**
     * 透過部分を白背景で合成
     * @param {HTMLCanvasElement} canvas - Canvas要素
     * @param {string} bgColor - 背景色（デフォルト: "#ffffff"）
     * @returns {HTMLCanvasElement} - 新しいCanvas
     */
    static applyWhiteBackground(canvas, bgColor = '#ffffff') {
        const newCanvas = document.createElement('canvas');
        newCanvas.width = canvas.width;
        newCanvas.height = canvas.height;
        const ctx = newCanvas.getContext('2d');
        
        // 背景色で塗りつぶし
        ctx.fillStyle = bgColor;
        ctx.fillRect(0, 0, newCanvas.width, newCanvas.height);
        
        // 元の画像を描画（透過部分は背景色が透ける）
        ctx.drawImage(canvas, 0, 0);
        
        return newCanvas;
    }

    /**
     * 余白をトリミング
     * @param {HTMLCanvasElement} canvas - Canvas要素
     * @param {Object} options - オプション
     * @param {number} options.tolerance - RGB差分のしきい値（0-60、デフォルト: 15）
     * @param {number} options.alphaThreshold - アルファ値のしきい値（デフォルト: 10）
     * @returns {HTMLCanvasElement} - トリミング後のCanvas
     */
    static trimMargins(canvas, options = {}) {
        const {
            tolerance = 15,
            alphaThreshold = 10
        } = options;

        const ctx = canvas.getContext('2d');
        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        const data = imageData.data;
        const width = canvas.width;
        const height = canvas.height;

        // 背景色を推定（4隅のピクセルの平均）
        const corners = [
            [0, 0], [width - 1, 0],
            [0, height - 1], [width - 1, height - 1]
        ];
        
        let bgR = 0, bgG = 0, bgB = 0, bgA = 0;
        let validCorners = 0;
        
        for (const [x, y] of corners) {
            const idx = (y * width + x) * 4;
            const a = data[idx + 3];
            if (a > alphaThreshold) {
                bgR += data[idx];
                bgG += data[idx + 1];
                bgB += data[idx + 2];
                bgA += a;
                validCorners++;
            }
        }
        
        if (validCorners === 0) {
            // 全透明の場合はトリムしない
            return canvas;
        }
        
        bgR = Math.round(bgR / validCorners);
        bgG = Math.round(bgG / validCorners);
        bgB = Math.round(bgB / validCorners);
        bgA = Math.round(bgA / validCorners);

        // 内容の外接矩形を求める
        let minX = width, minY = height, maxX = -1, maxY = -1;
        let hasContent = false;

        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                const idx = (y * width + x) * 4;
                const r = data[idx];
                const g = data[idx + 1];
                const b = data[idx + 2];
                const a = data[idx + 3];

                // 透過部分の判定
                if (a <= alphaThreshold) {
                    continue;
                }

                // 背景色との差分を計算
                const diffR = Math.abs(r - bgR);
                const diffG = Math.abs(g - bgG);
                const diffB = Math.abs(b - bgB);
                const totalDiff = diffR + diffG + diffB;

                // 内容と判定
                if (totalDiff > tolerance) {
                    hasContent = true;
                    minX = Math.min(minX, x);
                    minY = Math.min(minY, y);
                    maxX = Math.max(maxX, x);
                    maxY = Math.max(maxY, y);
                }
            }
        }

        // 内容が見つからない場合はトリムしない
        if (!hasContent || minX > maxX || minY > maxY) {
            return canvas;
        }

        // トリミング
        const cropWidth = maxX - minX + 1;
        const cropHeight = maxY - minY + 1;
        
        const newCanvas = document.createElement('canvas');
        newCanvas.width = cropWidth;
        newCanvas.height = cropHeight;
        const newCtx = newCanvas.getContext('2d');
        
        newCtx.drawImage(
            canvas,
            minX, minY, cropWidth, cropHeight,
            0, 0, cropWidth, cropHeight
        );

        return newCanvas;
    }

    /**
     * 縦横比を統一（パディング方式）
     * @param {HTMLCanvasElement} canvas - Canvas要素
     * @param {string} ratio - 縦横比（'original', '1:1', '4:5', '16:9'）
     * @param {string} bgColor - 背景色（デフォルト: "#ffffff"）
     * @returns {HTMLCanvasElement} - 新しいCanvas
     */
    static padToAspect(canvas, ratio = 'original', bgColor = '#ffffff') {
        return ImageAspect.padToAspect(canvas, ratio, bgColor);
    }

    /**
     * クリーンアップパイプラインを実行（v2対応）
     * @param {File} file - 入力画像ファイル
     * @param {Object} options - オプション
     * @param {boolean} options.whiteBackground - 透過→白背景を適用
     * @param {boolean} options.trimMargins - 余白トリムを適用
     * @param {number} options.trimTolerance - トリムのしきい値（0-60）
     * @param {boolean} options.padToAspect - 縦横比統一を適用
     * @param {string} options.aspectRatio - 縦横比（'original', '1:1', '4:5', '16:9'）
     * @param {string} options.aspectFit - フィット方式（'pad' | 'crop'）
     * @param {Object} options.style - 枠・余白・角丸（v1）
     * @param {number} options.style.paddingPx - 余白（0〜）
     * @param {number} options.style.borderWidthPx - 枠の幅（0〜）
     * @param {string} options.style.borderColor - 枠の色
     * @param {number} options.style.radiusPx - 角丸半径（0〜）
     * @param {string} options.style.bgColor - 余白・角丸用背景色
     * @param {Object} options.backgroundRemoval - 背景除去オプション
     * @param {boolean} options.backgroundRemoval.enabled - 背景除去を有効化
     * @param {string} options.backgroundRemoval.quality - 品質（'low' | 'medium' | 'high'）
     * @param {string} options.outputFormat - 出力形式（'jpeg', 'webp', 'png'）
     * @param {number} options.quality - 品質（0.1-1.0）
     * @param {string} options.filename - 出力ファイル名
     * @param {Object} options.style - 枠・余白・角丸（v1）
     * @param {number} options.style.paddingPx - 余白（0〜）
     * @param {number} options.style.radiusPx - 角丸（0〜）
     * @param {number} options.style.borderWidthPx - 枠幅（0〜）
     * @param {string} options.style.borderColor - 枠の色
     * @param {string} options.style.bgColor - 余白・角用背景色
     * @param {Object} ctx - コンテキスト
     * @returns {Promise<Array<{blob: Blob, filename: string, mime: string}>>}
     */
    static async runCleanupPipeline(file, options = {}, ctx = {}) {
        const {
            whiteBackground = false,
            trimMargins = false,
            trimTolerance = 15,
            padToAspect = false,
            aspectRatio = 'original',
            aspectFit = 'pad',
            style = { paddingPx: 0, borderWidthPx: 0, borderColor: '#000000', radiusPx: 0, bgColor: '#ffffff' },
            backgroundRemoval = { enabled: false, quality: 'medium' },
            outputFormat = 'jpeg',
            quality = 0.9,
            filename = null,
            style = {}
        } = options;
        const {
            paddingPx = 0,
            radiusPx = 0,
            borderWidthPx = 0,
            borderColor = '#000000',
            bgColor = '#ffffff'
        } = style;

        if (ctx.setTaskState) {
            ctx.setTaskState(ctx.index || 0, { status: 'running', message: '画像読み込み中...' });
        }

        // (1) 画像を読み込む
        const bitmap = await ImageLoad.loadToBitmap(file);
        
        // ピクセル上限チェック
        const pixels = bitmap.width * bitmap.height;
        const MAX_PIXELS = 80000000;
        if (pixels > MAX_PIXELS) {
            bitmap.close();
            throw new Error(`画像サイズが大きすぎます（${bitmap.width}x${bitmap.height}）。最大80,000,000ピクセルまで対応しています。`);
        }
        
        let canvas = ImageLoad.bitmapToCanvas(bitmap);
        bitmap.close();

        if (ctx.signal && ctx.signal.cancelled) {
            throw new Error('キャンセルされました');
        }

        // (2) 背景除去（v2、ONの場合）
        if (backgroundRemoval && backgroundRemoval.enabled) {
            try {
                canvas = await ImageBackgroundRemoval.removeBackgroundFromCanvas(canvas, {
                    quality: backgroundRemoval.quality || 'medium'
                }, ctx);
            } catch (error) {
                throw new Error(`背景除去に失敗しました: ${error.message}`);
            }
        }

        if (ctx.signal && ctx.signal.cancelled) {
            throw new Error('キャンセルされました');
        }

        // (3) 透過→白背景（必要な場合、またはJPEG出力の場合）
        // 背景除去後は透明背景になっているため、JPEG出力時は必ず白背景化が必要
        if (whiteBackground || outputFormat === 'jpeg' || outputFormat === 'jpg') {
            if (ctx.setTaskState) {
                ctx.setTaskState(ctx.index || 0, { status: 'running', message: '白背景化中...' });
            }
            canvas = this.applyWhiteBackground(canvas);
        }

        if (ctx.signal && ctx.signal.cancelled) {
            throw new Error('キャンセルされました');
        }

        // (4) 余白トリム（必要な場合）
        // 背景除去後は透明背景になっているため、alpha判定が効く
        if (trimMargins) {
            if (ctx.setTaskState) {
                ctx.setTaskState(ctx.index || 0, { status: 'running', message: '余白トリム中...' });
            }
            canvas = this.trimMargins(canvas, {
                tolerance: trimTolerance,
                alphaThreshold: 10
            });
        }

        if (ctx.signal && ctx.signal.cancelled) {
            throw new Error('キャンセルされました');
        }

        // (5) 縦横比統一（必要な場合）
        if (padToAspect && aspectRatio !== 'original') {
            if (ctx.setTaskState) {
                ctx.setTaskState(ctx.index || 0, { status: 'running', message: '縦横比調整中...' });
            }
            if (aspectFit === 'crop') {
                canvas = ImageAspect.cropToAspect(canvas, aspectRatio);
            } else {
                canvas = this.padToAspect(canvas, aspectRatio);
            }
        }

        if (ctx.signal && ctx.signal.cancelled) {
            throw new Error('キャンセルされました');
        }

        // (5b) 枠・余白・角丸（v1）
        if (typeof ImageStyle !== 'undefined' && (paddingPx > 0 || radiusPx > 0 || borderWidthPx > 0)) {
            if (ctx.setTaskState) {
                ctx.setTaskState(ctx.index || 0, { status: 'running', message: 'スタイル適用中...' });
            }
            if (paddingPx > 0) {
                canvas = ImageStyle.applyPadding(canvas, paddingPx, bgColor);
            }
            if (radiusPx > 0) {
                canvas = ImageStyle.applyRoundedCorners(canvas, radiusPx, bgColor);
            }
            if (borderWidthPx > 0) {
                canvas = ImageStyle.applyBorder(canvas, borderWidthPx, borderColor);
            }
        }

        if (ctx.signal && ctx.signal.cancelled) {
            throw new Error('キャンセルされました');
        }

        // (6) 書き出し
        if (ctx.setTaskState) {
            ctx.setTaskState(ctx.index || 0, { status: 'running', message: '書き出し中...' });
        }

        let mimeType;
        let ext;
        switch (outputFormat.toLowerCase()) {
            case 'jpeg':
            case 'jpg':
                mimeType = 'image/jpeg';
                ext = 'jpg';
                break;
            case 'webp':
                mimeType = 'image/webp';
                ext = 'webp';
                break;
            case 'png':
                mimeType = 'image/png';
                ext = 'png';
                break;
            default:
                mimeType = 'image/jpeg';
                ext = 'jpg';
        }

        const blob = await ImageExport.canvasToBlob(canvas, mimeType, quality);

        // ファイル名を決定
        const bgRemoved = backgroundRemoval && backgroundRemoval.enabled;
        const baseName = filename || this.generateFilename(file.name, ext, ctx.index + 1, null, bgRemoved);
        const outputFilename = FileValidation.sanitizeFilename(baseName);

        if (ctx.setTaskState) {
            ctx.setTaskState(ctx.index || 0, { status: 'success', message: '完了' });
        }

        return [{
            blob,
            filename: outputFilename,
            mime: mimeType
        }];
    }

    /**
     * 出力ファイル名を生成（v2対応）
     * @param {string} originalName - 元のファイル名
     * @param {string} ext - 拡張子
     * @param {number} index - インデックス（1始まり）
     * @param {string} template - テンプレート（例: "{name}_{bg}_{index}.{ext}"）
     * @param {boolean} bgRemoved - 背景除去が適用されたか
     * @returns {string}
     */
    static generateFilename(originalName, ext, index = 1, template = null, bgRemoved = false) {
        const nameWithoutExt = FileUtils.getFilenameWithoutExtension(originalName);
        
        if (template) {
            let result = template;
            result = result.replace(/{name}/g, nameWithoutExt);
            result = result.replace(/{index}/g, String(index));
            result = result.replace(/{ext}/g, ext);
            result = result.replace(/{bg}/g, bgRemoved ? 'bgremoved' : '');
            // 連続アンダースコアを1つに正規化
            result = result.replace(/_+/g, '_');
            if (!result.includes('.')) {
                result += '.' + ext;
            }
            return result;
        }
        
        const bgSuffix = bgRemoved ? '_bgremoved' : '';
        return `${nameWithoutExt}_clean${bgSuffix}_${index}.${ext}`;
    }
}

// 古典 script で読み込んだ場合にグローバルから参照できるよう明示的に露出（スコープ不整合対策）
if (typeof globalThis !== 'undefined') {
    globalThis.ImageCleanup = ImageCleanup;
}
if (typeof window !== 'undefined') {
    window.ImageCleanup = ImageCleanup;
}
