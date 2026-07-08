/**
 * ファイルバリデーション機能
 */

class FileValidation {
    /**
     * ファイルをバリデーション
     * @param {File[]} files - バリデーション対象のファイル配列
     * @param {Object} rules - バリデーションルール
     * @param {number} rules.maxFiles - 最大ファイル数
     * @param {number} rules.maxFileSize - 1ファイルの最大サイズ（バイト）
     * @param {number} rules.maxTotalSize - 合計サイズの上限（バイト）
     * @param {string[]} rules.allowedExtensions - 許可する拡張子（例: ['.png', '.jpg']）
     * @param {string[]} rules.allowedMimeTypes - 許可するMIMEタイプ（例: ['image/png', 'image/jpeg']）
     * @returns {{okFiles: File[], rejected: Array<{file: File, reason: string}>}}
     */
    static validateFiles(files, rules = {}) {
        const {
            maxFiles = 50,
            maxFileSize = 20 * 1024 * 1024, // 20MB
            maxTotalSize = 200 * 1024 * 1024, // 200MB
            allowedExtensions = [],
            allowedMimeTypes = []
        } = rules;

        const okFiles = [];
        const rejected = [];
        let totalSize = 0;

        // ファイル数チェック
        if (files.length > maxFiles) {
            files.forEach(file => {
                rejected.push({
                    file,
                    reason: `ファイル数が上限（${maxFiles}件）を超えています`
                });
            });
            return { okFiles, rejected };
        }

        for (const file of files) {
            let isValid = true;
            let reason = '';

            // ファイルサイズチェック
            if (file.size > maxFileSize) {
                isValid = false;
                reason = `ファイルサイズが上限（${this.formatBytes(maxFileSize)}）を超えています`;
            }

            // 拡張子チェック
            if (isValid && allowedExtensions.length > 0) {
                const ext = '.' + file.name.split('.').pop().toLowerCase();
                if (!allowedExtensions.includes(ext)) {
                    isValid = false;
                    reason = `対応していない拡張子です（${ext}）`;
                }
            }

            // MIMEタイプチェック
            if (isValid && allowedMimeTypes.length > 0) {
                if (!allowedMimeTypes.includes(file.type)) {
                    isValid = false;
                    reason = `対応していないファイル形式です（${file.type}）`;
                }
            }

            // 合計サイズチェック
            if (isValid) {
                totalSize += file.size;
                if (totalSize > maxTotalSize) {
                    isValid = false;
                    reason = `合計サイズが上限（${this.formatBytes(maxTotalSize)}）を超えています`;
                }
            }

            if (isValid) {
                okFiles.push(file);
            } else {
                rejected.push({ file, reason });
            }
        }

        return { okFiles, rejected };
    }

    /**
     * バイト数を人間が読める形式に変換
     * @param {number} bytes - バイト数
     * @returns {string}
     */
    static formatBytes(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }

    /**
     * ファイル名をサニタイズ
     * @param {string} filename - ファイル名
     * @returns {string}
     */
    static sanitizeFilename(filename) {
        // 危険な文字を削除・置換
        return filename
            .replace(/[<>:"/\\|?*]/g, '_')
            .replace(/\s+/g, '_')
            .replace(/_{2,}/g, '_')
            .replace(/^_+|_+$/g, '');
    }
}
