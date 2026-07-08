/**
 * PDFページ範囲パースユーティリティ
 */

class PdfRange {
    /**
     * ページ範囲文字列をパース（抽出用）
     * @param {string} rangeStr - 範囲文字列（例: "1-3,5,7-9"）
     * @returns {number[]} - 1始まりのページ番号配列（重複除外、昇順ソート）
     */
    static parseExtractRange(rangeStr) {
        if (!rangeStr || !rangeStr.trim()) {
            return [];
        }

        const pages = new Set();
        const parts = rangeStr.split(',').map(s => s.trim()).filter(s => s);

        for (const part of parts) {
            if (part.includes('-')) {
                const [start, end] = part.split('-').map(s => parseInt(s.trim()));
                if (isNaN(start) || isNaN(end) || start < 1 || end < 1) {
                    throw new Error(`無効な範囲: ${part}`);
                }
                if (start > end) {
                    throw new Error(`開始ページが終了ページより大きい: ${part}`);
                }
                for (let i = start; i <= end; i++) {
                    pages.add(i);
                }
            } else {
                const page = parseInt(part);
                if (isNaN(page) || page < 1) {
                    throw new Error(`無効なページ番号: ${part}`);
                }
                pages.add(page);
            }
        }

        return Array.from(pages).sort((a, b) => a - b);
    }

    /**
     * ページ範囲文字列をパース（分割用）
     * @param {string} rangeStr - 範囲文字列（例: "1-3;4-6;7-10"）
     * @returns {number[][]} - グループごとのページ番号配列
     */
    static parseSplitRange(rangeStr) {
        if (!rangeStr || !rangeStr.trim()) {
            return [];
        }

        const groups = [];
        const groupStrs = rangeStr.split(';').map(s => s.trim()).filter(s => s);

        for (const groupStr of groupStrs) {
            const pages = new Set();
            const parts = groupStr.split(',').map(s => s.trim()).filter(s => s);

            for (const part of parts) {
                if (part.includes('-')) {
                    const [start, end] = part.split('-').map(s => parseInt(s.trim()));
                    if (isNaN(start) || isNaN(end) || start < 1 || end < 1) {
                        throw new Error(`無効な範囲: ${part}`);
                    }
                    if (start > end) {
                        throw new Error(`開始ページが終了ページより大きい: ${part}`);
                    }
                    for (let i = start; i <= end; i++) {
                        pages.add(i);
                    }
                } else {
                    const page = parseInt(part);
                    if (isNaN(page) || page < 1) {
                        throw new Error(`無効なページ番号: ${part}`);
                    }
                    pages.add(page);
                }
            }

            if (pages.size > 0) {
                groups.push(Array.from(pages).sort((a, b) => a - b));
            }
        }

        return groups;
    }

    /**
     * ページ番号が有効範囲内かチェック
     * @param {number[]} pages - ページ番号配列
     * @param {number} totalPages - 総ページ数
     * @returns {{valid: boolean, invalid: number[]}}
     */
    static validatePages(pages, totalPages) {
        const invalid = pages.filter(p => p < 1 || p > totalPages);
        return {
            valid: invalid.length === 0,
            invalid
        };
    }
}
