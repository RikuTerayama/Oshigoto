/**
 * ファイルユーティリティ機能
 */

class FileUtils {
    /**
     * Blobをダウンロード
     * @param {Blob} blob - ダウンロードするBlob
     * @param {string} filename - ファイル名
     */
    static downloadBlob(blob, filename) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
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
     * ファイル名から拡張子を取得
     * @param {string} filename - ファイル名
     * @returns {string}
     */
    static getExtension(filename) {
        const parts = filename.split('.');
        return parts.length > 1 ? parts[parts.length - 1].toLowerCase() : '';
    }

    /**
     * ファイル名から拡張子を除いた部分を取得
     * @param {string} filename - ファイル名
     * @returns {string}
     */
    static getFilenameWithoutExtension(filename) {
        const lastDot = filename.lastIndexOf('.');
        return lastDot > 0 ? filename.substring(0, lastDot) : filename;
    }
}
