/**
 * Pure validation and naming helpers for browser-based image compression.
 */
(function (root, factory) {
    const api = factory();
    if (typeof module !== 'undefined' && module.exports) module.exports = api;
    if (root) root.ImageCompressCore = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
    'use strict';

    const FORMAT_MIME = Object.freeze({ jpeg: 'image/jpeg', png: 'image/png', webp: 'image/webp' });
    const FORMAT_EXTENSION = Object.freeze({ jpeg: 'jpg', png: 'png', webp: 'webp' });
    const EXTENSION_FORMAT = Object.freeze({ jpg: 'jpeg', jpeg: 'jpeg', png: 'png', webp: 'webp' });
    const MIME_FORMAT = Object.freeze({ 'image/jpeg': 'jpeg', 'image/png': 'png', 'image/webp': 'webp' });

    function bytesToAscii(bytes, start, length) {
        let value = '';
        for (let i = start; i < start + length && i < bytes.length; i += 1) {
            value += String.fromCharCode(bytes[i]);
        }
        return value;
    }

    function getExtension(filename) {
        const safe = String(filename || '').replace(/\\/g, '/').split('/').pop();
        const dot = safe.lastIndexOf('.');
        return dot > 0 ? safe.slice(dot + 1).toLowerCase() : '';
    }

    function detectFileFormat(buffer) {
        const bytes = buffer instanceof Uint8Array ? buffer : new Uint8Array(buffer || 0);
        if (bytes.length >= 3 && bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff) return 'jpeg';
        if (bytes.length >= 8 && bytesToAscii(bytes, 1, 3) === 'PNG' && bytes[0] === 0x89 && bytes[4] === 0x0d && bytes[5] === 0x0a && bytes[6] === 0x1a && bytes[7] === 0x0a) return 'png';
        if (bytes.length >= 12 && bytesToAscii(bytes, 0, 4) === 'RIFF' && bytesToAscii(bytes, 8, 4) === 'WEBP') return 'webp';
        if (bytes.length >= 6 && (bytesToAscii(bytes, 0, 6) === 'GIF87a' || bytesToAscii(bytes, 0, 6) === 'GIF89a')) return 'gif';
        return null;
    }

    function detectApng(buffer) {
        const bytes = buffer instanceof Uint8Array ? buffer : new Uint8Array(buffer || 0);
        if (detectFileFormat(bytes) !== 'png') return false;
        const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
        let offset = 8;
        while (offset + 12 <= bytes.length) {
            const length = view.getUint32(offset, false);
            if (length > bytes.length - offset - 12) return false;
            const type = bytesToAscii(bytes, offset + 4, 4);
            if (type === 'acTL') return true;
            if (type === 'IEND') return false;
            offset += 12 + length;
        }
        return false;
    }

    function detectAnimatedWebp(buffer) {
        const bytes = buffer instanceof Uint8Array ? buffer : new Uint8Array(buffer || 0);
        if (detectFileFormat(bytes) !== 'webp') return false;
        const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
        let offset = 12;
        while (offset + 8 <= bytes.length) {
            const type = bytesToAscii(bytes, offset, 4);
            const length = view.getUint32(offset + 4, true);
            if (length > bytes.length - offset - 8) return false;
            if (type === 'ANIM') return true;
            if (type === 'VP8X' && length >= 1 && (bytes[offset + 8] & 0x02) !== 0) return true;
            offset += 8 + length + (length % 2);
        }
        return false;
    }

    function validateIdentity(filename, mime, buffer) {
        const extFormat = EXTENSION_FORMAT[getExtension(filename)] || null;
        const mimeFormat = MIME_FORMAT[String(mime || '').toLowerCase()] || null;
        const detectedFormat = detectFileFormat(buffer);
        if (detectedFormat === 'gif') throw new Error('アニメーション画像には対応していません。静止画のPNG・JPEG・WebPを選択してください。');
        if (!extFormat || !detectedFormat || (mime && !mimeFormat)) throw new Error('対応形式は静止画のJPEG・PNG・WebPです。');
        if (extFormat !== detectedFormat || (mimeFormat && mimeFormat !== detectedFormat)) throw new Error('拡張子、MIMEタイプ、画像データの形式が一致していません。');
        if (detectedFormat === 'png' && detectApng(buffer)) throw new Error('アニメーション画像には対応していません。静止画のPNG・JPEG・WebPを選択してください。');
        if (detectedFormat === 'webp' && detectAnimatedWebp(buffer)) throw new Error('アニメーション画像には対応していません。静止画のPNG・JPEG・WebPを選択してください。');
        return detectedFormat;
    }

    function parsePositiveInteger(value, maximum, label) {
        const text = String(value == null ? '' : value).trim();
        if (!text) return null;
        if (!/^\d+$/.test(text)) throw new Error(`${label}は1以上の整数で入力してください。`);
        const number = Number(text);
        if (!Number.isSafeInteger(number) || number < 1 || number > maximum) {
            throw new Error(`${label}は1〜${maximum.toLocaleString('ja-JP')}の範囲で入力してください。`);
        }
        return number;
    }

    function validateSelectionLimits(files, maxFiles, maxFileBytes, maxTotalBytes) {
        const selected = Array.from(files || []);
        if (selected.length > maxFiles) throw new Error(`選択できる画像は最大${maxFiles}件です。`);
        let totalBytes = 0;
        selected.forEach((file) => {
            const size = Number(file && file.size);
            if (!Number.isFinite(size) || size <= 0) throw new Error('0 byteのファイルは処理できません。');
            if (size > maxFileBytes) throw new Error(`1ファイル${Math.round(maxFileBytes / 1024 / 1024)}MB以下の画像を選択してください。`);
            totalBytes += size;
        });
        if (totalBytes > maxTotalBytes) throw new Error(`合計容量は${Math.round(maxTotalBytes / 1024 / 1024)}MB以下にしてください。`);
        return totalBytes;
    }

    function validateImageLimits(width, height, maxPixels, maxLongEdge) {
        if (!Number.isSafeInteger(width) || !Number.isSafeInteger(height) || width < 1 || height < 1) {
            throw new Error('画像の寸法を確認できませんでした。');
        }
        if (width > maxLongEdge || height > maxLongEdge) {
            throw new Error(`画像の長辺は${maxLongEdge.toLocaleString('ja-JP')}px以下にしてください。`);
        }
        if (width * height > maxPixels) {
            throw new Error(`画像は最大${maxPixels.toLocaleString('ja-JP')}画素までです。`);
        }
        return true;
    }

    function normalizeQuality(value, outputFormat) {
        if (outputFormat === 'png') return null;
        const text = String(value == null ? '' : value).trim();
        if (!/^\d+$/.test(text)) throw new Error('品質は1〜100の整数で指定してください。');
        const number = Number(text);
        if (number < 1 || number > 100) throw new Error('品質は1〜100の整数で指定してください。');
        return number / 100;
    }

    function calculateDimensions(width, height, maxWidth, maxHeight) {
        if (!Number.isSafeInteger(width) || !Number.isSafeInteger(height) || width < 1 || height < 1) {
            throw new Error('画像の寸法を確認できませんでした。');
        }
        const ratios = [1];
        if (maxWidth) ratios.push(maxWidth / width);
        if (maxHeight) ratios.push(maxHeight / height);
        const ratio = Math.min.apply(null, ratios);
        return {
            width: Math.max(1, Math.round(width * ratio)),
            height: Math.max(1, Math.round(height * ratio)),
        };
    }

    function sanitizeFilename(filename) {
        const leaf = String(filename || '').replace(/\\/g, '/').split('/').pop();
        const cleaned = leaf.replace(/[\u0000-\u001f\u007f<>:"/\\|?*]/g, '_').trim();
        return cleaned || 'image';
    }

    function generateOutputFilename(originalName, format, usedNames) {
        const cleaned = sanitizeFilename(originalName);
        const dot = cleaned.lastIndexOf('.');
        const rawBase = dot > 0 ? cleaned.slice(0, dot) : cleaned;
        const base = (rawBase || 'image').slice(0, 120);
        const extension = FORMAT_EXTENSION[format];
        if (!extension) throw new Error('出力形式を確認してください。');
        let index = 1;
        let candidate = `${base}_compressed.${extension}`;
        while (usedNames && usedNames.has(candidate.toLowerCase())) {
            index += 1;
            candidate = `${base}_compressed_${index}.${extension}`;
        }
        if (usedNames) usedNames.add(candidate.toLowerCase());
        return candidate;
    }

    function describeSizeChange(originalBytes, outputBytes) {
        if (!Number.isFinite(originalBytes) || originalBytes <= 0 || !Number.isFinite(outputBytes) || outputBytes < 0) {
            throw new Error('容量を比較できませんでした。');
        }
        const percent = ((outputBytes - originalBytes) / originalBytes) * 100;
        if (Math.abs(percent) < 0.5) return { kind: 'same', percent: 0, text: '容量はほぼ同じです' };
        const rounded = Math.abs(percent).toFixed(1);
        return percent < 0
            ? { kind: 'reduced', percent: Math.abs(percent), text: `${rounded}%削減` }
            : { kind: 'increased', percent, text: `${rounded}%増加` };
    }

    function resolveOutputFormat(selection, inputFormat) {
        if (selection === 'original') return inputFormat;
        if (!FORMAT_MIME[selection]) throw new Error('出力形式を確認してください。');
        return selection;
    }

    return Object.freeze({
        FORMAT_MIME,
        FORMAT_EXTENSION,
        EXTENSION_FORMAT,
        MIME_FORMAT,
        getExtension,
        detectFileFormat,
        detectApng,
        detectAnimatedWebp,
        validateIdentity,
        parsePositiveInteger,
        validateSelectionLimits,
        validateImageLimits,
        normalizeQuality,
        calculateDimensions,
        sanitizeFilename,
        generateOutputFilename,
        describeSizeChange,
        resolveOutputFormat,
    });
});
