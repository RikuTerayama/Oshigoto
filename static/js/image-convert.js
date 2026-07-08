/**
 * 画像変換処理
 */

class ImageConverter {
    /**
     * 画像ファイルを変換
     * @param {File} file - 入力画像ファイル
     * @param {Object} options - 変換オプション
     * @param {string} options.outputFormat - 出力形式 ('jpeg' | 'webp' | 'png')
     * @param {number} options.width - リサイズ幅（0または未指定でリサイズなし）
     * @param {number} options.quality - 品質（0.1-1.0、jpeg/webpのみ）
     * @param {string} options.filename - 出力ファイル名
     * @returns {Promise<{blob: Blob, filename: string, mime: string}>}
     */
    static async convertImage(file, options = {}) {
        const {
            outputFormat = 'jpeg',
            width = 0,
            quality = 0.9,
            filename = null
        } = options;

        // 画像を読み込み
        let imageBitmap;
        try {
            // createImageBitmap を優先（より効率的）
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
        let outputWidth = imageBitmap.width;
        let outputHeight = imageBitmap.height;
        if (width > 0 && imageBitmap.width > width) {
            const ratio = width / imageBitmap.width;
            outputWidth = width;
            outputHeight = Math.round(imageBitmap.height * ratio);
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
                // PNGは品質パラメータを無視
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

        // ファイル名を決定
        const outputFilename = filename || this.generateFilename(file.name, outputFormat);

        imageBitmap.close();

        return {
            blob,
            filename: outputFilename,
            mime: mimeType
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
     * 出力ファイル名を生成
     * @param {string} originalName - 元のファイル名
     * @param {string} outputFormat - 出力形式
     * @returns {string}
     */
    static generateFilename(originalName, outputFormat) {
        const ext = FileUtils.getExtension(originalName);
        const nameWithoutExt = FileUtils.getFilenameWithoutExtension(originalName);
        const outputExt = outputFormat === 'jpg' ? 'jpeg' : outputFormat;
        return `${nameWithoutExt}.${outputExt}`;
    }

    /**
     * リネームテンプレートを適用
     * @param {string} template - テンプレート文字列（例: "{name}*{w}px*{index}"）
     * @param {Object} vars - 変数
     * @param {string} vars.name - 元のファイル名（拡張子なし）
     * @param {number} vars.index - インデックス
     * @param {number} vars.w - 幅
     * @param {string} vars.ext - 拡張子
     * @param {string} vars.suffix - サフィックス
     * @returns {string}
     */
    static applyRenameTemplate(template, vars) {
        let result = template;
        result = result.replace(/{name}/g, vars.name || '');
        result = result.replace(/{index}/g, String(vars.index || 0));
        result = result.replace(/{w}/g, String(vars.w || 0));
        result = result.replace(/{ext}/g, vars.ext || '');
        result = result.replace(/{suffix}/g, vars.suffix || '');
        
        // 拡張子が含まれていない場合は追加
        if (!result.includes('.')) {
            result += '.' + (vars.ext || '');
        }
        
        // ファイル名をサニタイズ
        return FileValidation.sanitizeFilename(result);
    }
}
