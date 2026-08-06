/**
 * PDF page-range parser shared by extract, split, delete, and rotate modes.
 */

class PdfRange {
    static MAX_INPUT_LENGTH = 2000;
    static MAX_EXPANDED_PAGES = 2000;

    /**
     * Parse a comma-separated, 1-based page range.
     * @param {string} rangeStr
     * @param {{totalPages?: number|null, maxExpandedPages?: number}} options
     * @returns {number[]}
     */
    static parsePageRange(rangeStr, options = {}) {
        const raw = String(rangeStr || '').trim();
        if (!raw) return [];
        if (raw.length > PdfRange.MAX_INPUT_LENGTH) {
            throw new Error('ページ指定が長すぎます。範囲を短く分けて入力してください。');
        }

        const totalPages = Number.isInteger(options.totalPages) ? options.totalPages : null;
        const maxExpandedPages = Number.isInteger(options.maxExpandedPages)
            ? options.maxExpandedPages
            : PdfRange.MAX_EXPANDED_PAGES;
        const tokens = raw.split(',');
        if (tokens.some(token => !token.trim())) {
            throw new Error('ページ指定の形式を確認してください。');
        }

        const pages = new Set();
        for (const token of tokens) {
            const part = token.trim();
            const singleMatch = part.match(/^([1-9]\d*)$/);
            const rangeMatch = part.match(/^([1-9]\d*)\s*-\s*([1-9]\d*)$/);

            if (singleMatch) {
                PdfRange.addValidatedRange(pages, Number(singleMatch[1]), Number(singleMatch[1]), totalPages, maxExpandedPages);
                continue;
            }
            if (rangeMatch) {
                const start = Number(rangeMatch[1]);
                const end = Number(rangeMatch[2]);
                if (start > end) {
                    throw new Error(`${start}-${end}のような降順範囲は指定できません。`);
                }
                PdfRange.addValidatedRange(pages, start, end, totalPages, maxExpandedPages);
                continue;
            }
            if (/^-?\d+(?:\.\d+)?$/.test(part)) {
                throw new Error('ページ番号は1以上の整数で入力してください。');
            }
            throw new Error('ページ指定の形式を確認してください。');
        }

        return Array.from(pages).sort((a, b) => a - b);
    }

    static addValidatedRange(pages, start, end, totalPages, maxExpandedPages) {
        if (!Number.isSafeInteger(start) || !Number.isSafeInteger(end) || start < 1 || end < 1) {
            throw new Error('ページ番号は1以上の整数で入力してください。');
        }
        if (totalPages !== null && end > totalPages) {
            throw new Error(`このPDFは${totalPages}ページです。${end}ページ目は指定できません。`);
        }
        if ((end - start + 1) > maxExpandedPages || pages.size + (end - start + 1) > maxExpandedPages) {
            throw new Error('指定できるページ数の上限を超えています。範囲を短くしてください。');
        }
        for (let page = start; page <= end; page += 1) pages.add(page);
    }

    static parseExtractRange(rangeStr, options = {}) {
        return PdfRange.parsePageRange(rangeStr, options);
    }

    /** Parse semicolon-separated page groups used by split mode. */
    static parseSplitRange(rangeStr, options = {}) {
        const raw = String(rangeStr || '').trim();
        if (!raw) return [];
        if (raw.length > PdfRange.MAX_INPUT_LENGTH) {
            throw new Error('ページ指定が長すぎます。範囲を短く分けて入力してください。');
        }
        const groups = raw.split(';');
        if (groups.some(group => !group.trim())) {
            throw new Error('ページ指定の形式を確認してください。');
        }
        return groups.map(group => PdfRange.parsePageRange(group, options));
    }

    static validatePages(pages, totalPages) {
        const invalid = pages.filter(page => !Number.isInteger(page) || page < 1 || page > totalPages);
        return { valid: invalid.length === 0, invalid };
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = PdfRange;
}
