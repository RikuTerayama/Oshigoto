/**
 * ZIP作成ユーティリティ
 * JSZipライブラリを使用
 */

class ZipUtils {
    /**
     * 複数の出力ファイルからZIPを作成
     * @param {Array<{blob: Blob, filename: string}>} outputs - 出力ファイル配列
     * @param {string} zipName - ZIPファイル名
     * @returns {Promise<Blob>}
     */
    static async createZip(outputs, zipName = 'output.zip') {
        if (typeof JSZip === 'undefined') {
            throw new Error('JSZipライブラリが読み込まれていません');
        }

        const zip = new JSZip();

        for (const output of outputs) {
            zip.file(output.filename, output.blob);
        }

        const zipBlob = await zip.generateAsync({
            type: 'blob',
            compression: 'DEFLATE',
            compressionOptions: { level: 6 }
        });

        return zipBlob;
    }
}
