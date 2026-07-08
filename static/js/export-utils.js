/**
 * 汎用エクスポートユーティリティ（ダウンロード・クリップボード・トースト）
 * FileValidation と FileUtils に依存（読み込み順で先に読み込むこと）
 */
const ExportUtils = {
    /**
     * テキストをクリップボードにコピー
     * @param {string} text - コピーするテキスト
     * @returns {Promise<boolean>}
     */
    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            return true;
        } catch (err) {
            const textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.style.position = 'fixed';
            textarea.style.opacity = '0';
            document.body.appendChild(textarea);
            textarea.select();
            try {
                document.execCommand('copy');
                document.body.removeChild(textarea);
                return true;
            } catch (e) {
                document.body.removeChild(textarea);
                return false;
            }
        }
    },

    /**
     * トーストメッセージを表示
     * @param {string} message - メッセージ
     * @param {string} type - 'success' | 'error'
     */
    showToast(message, type = 'success') {
        const existing = document.getElementById('toast-message');
        if (existing) existing.remove();
        const toast = document.createElement('div');
        toast.id = 'toast-message';
        toast.style.cssText = `
            position: fixed; bottom: 20px; right: 20px; padding: 12px 24px;
            background: ${type === 'success' ? 'rgba(76, 175, 80, 0.9)' : 'rgba(244, 67, 54, 0.9)'};
            color: white; border-radius: 8px; z-index: 10000; font-size: 0.95em;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        `;
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transition = 'opacity 0.3s';
            setTimeout(() => toast.remove(), 300);
        }, 2000);
    },

    /**
     * Markdown/テキストを .md でダウンロード
     * @param {string} text - 内容
     * @param {string} filenameBase - ファイル名のベース（拡張子なし）
     */
    downloadMarkdown(text, filenameBase = 'export') {
        const blob = new Blob([text], { type: 'text/markdown;charset=utf-8' });
        const sanitized = typeof FileValidation !== 'undefined' ? FileValidation.sanitizeFilename(filenameBase) : filenameBase.replace(/[^a-zA-Z0-9_-]/g, '_');
        const date = new Date().toISOString().split('T')[0].replace(/-/g, '');
        const filename = `${sanitized}_${date}.md`;
        if (typeof FileUtils !== 'undefined' && FileUtils.downloadBlob) {
            FileUtils.downloadBlob(blob, filename);
        } else {
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = filename;
            a.click();
            URL.revokeObjectURL(a.href);
        }
    }
};
