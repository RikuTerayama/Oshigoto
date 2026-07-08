/**
 * CSV/Excel ユーティリティ - ブラウザ内処理（サーバーへ送信しない）
 * ログにはファイル内容・パスワードを出さず、処理段階・件数のみ記述する。
 */
const CsvOps = {
    MAX_ROWS: 100000,
    PREVIEW_ROWS: 50,

    /**
     * ファイルを UTF-8 テキストとして読み込む
     * @param {File} file
     * @returns {Promise<string>}
     */
    readFileAsText(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result || '');
            reader.onerror = () => reject(new Error('ファイルの読み込みに失敗しました'));
            reader.readAsText(file, 'UTF-8');
        });
    },

    /**
     * ファイルをバイナリで読み、指定エンコーディングで文字列に変換
     * @param {File} file
     * @param {string} encoding - 'UTF-8' | 'SJIS'
     * @returns {Promise<string>}
     */
    readFileAsTextWithEncoding(file, encoding) {
        if (encoding === 'UTF-8' || !encoding) {
            return this.readFileAsText(file);
        }
        return this.readFileAsArrayBuffer(file).then(buf => {
            const arr = new Uint8Array(buf);
            if (typeof Encoding === 'undefined') throw new Error('encoding-japanese が読み込まれていません');
            return Encoding.convert(arr, { to: 'UNICODE', from: 'SJIS', type: 'string' });
        });
    },

    /**
     * CSV をパース（PapaParse）。プレビュー用は先頭のみ
     * @param {string} text
     * @param {Object} options - { preview: number }
     * @returns {{ data: string[][], meta: object, previewRows: number }}
     */
    parseCSV(text, options = {}) {
        if (typeof Papa === 'undefined') throw new Error('PapaParse が読み込まれていません');
        if (options.preview != null) {
            const result = Papa.parse(text, { preview: options.preview, skipEmptyLines: true });
            return { data: result.data || [], meta: result.meta || {}, previewRows: (result.data || []).length };
        }
        const full = Papa.parse(text, { skipEmptyLines: true });
        const rows = full.data || [];
        if (rows.length > this.MAX_ROWS) throw new Error(`行数が上限（${this.MAX_ROWS}行）を超えています。`);
        return { data: rows, meta: full.meta || {}, previewRows: rows.length };
    },

    /**
     * 列の抽出・並べ替え（インデックス配列で指定）
     * @param {string[][]} rows
     * @param {number[]} columnIndexes - 0-based
     * @returns {string[][]}
     */
    selectColumns(rows, columnIndexes) {
        if (!rows.length) return [];
        return rows.map(row => columnIndexes.map(i => row[i] != null ? row[i] : ''));
    },

    /**
     * 重複削除（キー列で先頭を残す）
     * @param {string[][]} rows - 1行目がヘッダー
     * @param {number} keyColumnIndex - 0-based
     * @returns {string[][]}
     */
    dedupeByKey(rows, keyColumnIndex) {
        if (!rows.length) return [];
        const header = rows[0];
        const data = rows.slice(1);
        const seen = new Set();
        const out = [header];
        for (const row of data) {
            const key = row[keyColumnIndex] != null ? String(row[keyColumnIndex]) : '';
            if (seen.has(key)) continue;
            seen.add(key);
            out.push(row);
        }
        return out;
    },

    /**
     * N行ごとに分割（1つ目にヘッダーを含む）
     * @param {string[][]} rows - 1行目がヘッダー
     * @param {number} chunkSize
     * @returns {string[][]][]}
     */
    splitByNRows(rows, chunkSize) {
        if (!rows.length || chunkSize < 1) return [];
        const header = rows[0];
        const data = rows.slice(1);
        const chunks = [];
        for (let i = 0; i < data.length; i += chunkSize) {
            chunks.push([header, ...data.slice(i, i + chunkSize)]);
        }
        return chunks;
    },

    /**
     * 二次元配列を CSV 文字列に
     * @param {string[][]} rows
     * @returns {string}
     */
    toCSVString(rows) {
        if (typeof Papa === 'undefined') {
            return rows.map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(',')).join('\r\n');
        }
        return Papa.unparse(rows);
    },

    /**
     * 配列を Blob に（UTF-8）
     * @param {string[][]} rows
     * @param {Object} options - { bom: boolean } BOM を付けるか
     * @returns {Blob}
     */
    rowsToBlob(rows, options = {}) {
        const csv = this.toCSVString(rows);
        const bom = options.bom !== false ? '\uFEFF' : '';
        return new Blob([bom + csv], { type: 'text/csv;charset=utf-8' });
    },

    /**
     * 文字列を Shift-JIS の Blob に（encoding-japanese 使用）
     * @param {string} text - UTF-8 文字列
     * @returns {Blob}
     */
    textToSJISBlob(text) {
        if (typeof Encoding === 'undefined') throw new Error('encoding-japanese が読み込まれていません');
        const unicodeArray = Encoding.stringToCode(text);
        const sjisArray = Encoding.convert(unicodeArray, { to: 'SJIS', from: 'UNICODE' });
        return new Blob([new Uint8Array(sjisArray)], { type: 'text/csv;charset=shift_jis' });
    },

    /**
     * ファイル名のベース＋サフィックス＋日付
     * @param {string} base
     * @param {string} suffix
     * @param {string} ext
     * @returns {string}
     */
    outputFilename(base, suffix, ext) {
        const safe = typeof FileValidation !== 'undefined' ? FileValidation.sanitizeFilename(base) : base.replace(/[<>:"/\\|?*]/g, '_');
        const date = new Date().toISOString().split('T')[0].replace(/-/g, '');
        return `${safe}_${suffix}_${date}.${ext}`;
    },

    /**
     * ファイルを ArrayBuffer で読み込む（XLSX用）
     * @param {File} file
     * @returns {Promise<ArrayBuffer>}
     */
    readFileAsArrayBuffer(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.onerror = () => reject(new Error('ファイルの読み込みに失敗しました'));
            reader.readAsArrayBuffer(file);
        });
    },

    /**
     * XLSX をパースして先頭シートを二次元配列に（SheetJS）
     * @param {ArrayBuffer} buf
     * @param {Object} options - { sheetIndex: number }
     * @returns {string[][]}
     */
    xlsxToRows(buf, options = {}) {
        if (typeof XLSX === 'undefined') throw new Error('SheetJS が読み込まれていません');
        const wb = XLSX.read(buf, { type: 'array' });
        const sheetIndex = options.sheetIndex != null ? options.sheetIndex : 0;
        const sheetName = wb.SheetNames[sheetIndex];
        if (!sheetName) throw new Error('シートがありません');
        const sheet = wb.Sheets[sheetName];
        const rows = XLSX.utils.sheet_to_json(sheet, { header: 1, defval: '' });
        return rows.map(row => Array.isArray(row) ? row : [row]);
    },

    /**
     * 二次元配列を XLSX にして Blob で返す（SheetJS）
     * @param {string[][]} rows
     * @returns {Blob}
     */
    rowsToXLSXBlob(rows) {
        if (typeof XLSX === 'undefined') throw new Error('SheetJS が読み込まれていません');
        const ws = XLSX.utils.aoa_to_sheet(rows);
        const wb = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(wb, ws, 'Sheet1');
        const out = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
        return new Blob([out], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
    }
};
