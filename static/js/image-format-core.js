/**
 * Shared, side-effect-free image format inspection helpers.
 * Browser-only capability helpers are exposed behind runtime guards.
 */
(function (root, factory) {
    const api = factory();
    if (typeof module !== 'undefined' && module.exports) module.exports = api;
    if (root) root.ImageFormatCore = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
    'use strict';

    const FORMAT_MIME = Object.freeze({
        jpeg: 'image/jpeg', png: 'image/png', webp: 'image/webp',
        gif: 'image/gif', bmp: 'image/bmp', avif: 'image/avif',
    });
    const FORMAT_EXTENSION = Object.freeze({
        jpeg: 'jpg', png: 'png', webp: 'webp', gif: 'gif', bmp: 'bmp', avif: 'avif',
    });
    const EXTENSION_FORMAT = Object.freeze({
        jpg: 'jpeg', jpeg: 'jpeg', png: 'png', webp: 'webp', gif: 'gif', bmp: 'bmp', avif: 'avif',
        heic: 'heif', heif: 'heif', tif: 'tiff', tiff: 'tiff', svg: 'svg', ico: 'ico',
    });
    const MIME_FORMAT = Object.freeze({
        'image/jpeg': 'jpeg', 'image/png': 'png', 'image/webp': 'webp', 'image/gif': 'gif',
        'image/bmp': 'bmp', 'image/x-ms-bmp': 'bmp', 'image/avif': 'avif',
        'image/heic': 'heif', 'image/heif': 'heif', 'image/tiff': 'tiff',
        'image/svg+xml': 'svg', 'image/x-icon': 'ico', 'image/vnd.microsoft.icon': 'ico',
    });
    const AVIF_BRANDS = new Set(['avif', 'avis']);
    const HEIF_BRANDS = new Set(['heic', 'heix', 'hevc', 'hevx', 'heim', 'heis', 'mif1', 'msf1']);
    const OUTPUT_FORMATS = new Set(['jpeg', 'png', 'webp', 'avif']);
    const MAX_CHUNKS = 100000;

    function asBytes(buffer) {
        if (buffer instanceof Uint8Array) return buffer;
        if (buffer instanceof ArrayBuffer) return new Uint8Array(buffer);
        if (ArrayBuffer.isView(buffer)) return new Uint8Array(buffer.buffer, buffer.byteOffset, buffer.byteLength);
        return new Uint8Array(0);
    }

    function bytesToAscii(bytes, start, length) {
        if (start < 0 || length < 0 || start > bytes.length - length) return '';
        let value = '';
        for (let i = start; i < start + length; i += 1) value += String.fromCharCode(bytes[i]);
        return value;
    }

    function getExtension(filename) {
        const leaf = String(filename || '').replace(/\\/g, '/').split('/').pop();
        const dot = leaf.lastIndexOf('.');
        return dot > 0 ? leaf.slice(dot + 1).toLowerCase() : '';
    }

    function hasPngSignature(bytes) {
        return bytes.length >= 8 && bytes[0] === 0x89 && bytesToAscii(bytes, 1, 3) === 'PNG'
            && bytes[4] === 0x0d && bytes[5] === 0x0a && bytes[6] === 0x1a && bytes[7] === 0x0a;
    }

    function parseIsoBrands(buffer) {
        const bytes = asBytes(buffer);
        if (bytes.length < 16) return null;
        const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
        let offset = 0;
        let iterations = 0;
        while (offset + 8 <= bytes.length && iterations < 256) {
            iterations += 1;
            let size = view.getUint32(offset, false);
            const type = bytesToAscii(bytes, offset + 4, 4);
            let headerSize = 8;
            if (size === 1) {
                if (offset + 16 > bytes.length) return null;
                const high = view.getUint32(offset + 8, false);
                const low = view.getUint32(offset + 12, false);
                if (high !== 0) return null;
                size = low;
                headerSize = 16;
            } else if (size === 0) {
                size = bytes.length - offset;
            }
            if (size < headerSize || size > bytes.length - offset) return null;
            if (type === 'ftyp') {
                if (size < headerSize + 8) return null;
                const majorBrand = bytesToAscii(bytes, offset + headerSize, 4);
                const compatibleBrands = [];
                for (let cursor = offset + headerSize + 8; cursor + 4 <= offset + size; cursor += 4) {
                    compatibleBrands.push(bytesToAscii(bytes, cursor, 4));
                }
                return { majorBrand, compatibleBrands, brands: [majorBrand, ...compatibleBrands] };
            }
            offset += size;
        }
        return null;
    }

    function detectFileFormat(buffer) {
        const bytes = asBytes(buffer);
        if (bytes.length >= 3 && bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff) return 'jpeg';
        if (hasPngSignature(bytes)) return 'png';
        if (bytes.length >= 12 && bytesToAscii(bytes, 0, 4) === 'RIFF' && bytesToAscii(bytes, 8, 4) === 'WEBP') return 'webp';
        if (bytes.length >= 6 && ['GIF87a', 'GIF89a'].includes(bytesToAscii(bytes, 0, 6))) return 'gif';
        if (bytes.length >= 2 && bytesToAscii(bytes, 0, 2) === 'BM') return 'bmp';
        const iso = parseIsoBrands(bytes);
        if (iso && iso.brands.some((brand) => AVIF_BRANDS.has(brand))) return 'avif';
        if (iso && iso.brands.some((brand) => HEIF_BRANDS.has(brand))) return 'heif';
        return null;
    }

    function detectApng(buffer) {
        const bytes = asBytes(buffer);
        if (!hasPngSignature(bytes)) return false;
        const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
        let offset = 8;
        let iterations = 0;
        while (offset + 12 <= bytes.length && iterations < MAX_CHUNKS) {
            iterations += 1;
            const length = view.getUint32(offset, false);
            if (length > bytes.length - offset - 12) throw new Error('PNGデータが途中で切れています。');
            const type = bytesToAscii(bytes, offset + 4, 4);
            if (type === 'acTL') return true;
            if (type === 'IEND') return false;
            offset += 12 + length;
        }
        if (iterations >= MAX_CHUNKS) throw new Error('PNGの構造を安全に確認できませんでした。');
        throw new Error('PNGデータが途中で切れています。');
    }

    function detectAnimatedWebp(buffer) {
        const bytes = asBytes(buffer);
        if (detectFileFormat(bytes) !== 'webp') return false;
        const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
        let offset = 12;
        let iterations = 0;
        while (offset + 8 <= bytes.length && iterations < MAX_CHUNKS) {
            iterations += 1;
            const type = bytesToAscii(bytes, offset, 4);
            const length = view.getUint32(offset + 4, true);
            const paddedLength = length + (length % 2);
            if (length > bytes.length - offset - 8 || paddedLength > bytes.length - offset - 8) {
                throw new Error('WebPデータが途中で切れています。');
            }
            if (type === 'ANIM') return true;
            if (type === 'VP8X' && length >= 1 && (bytes[offset + 8] & 0x02) !== 0) return true;
            offset += 8 + paddedLength;
        }
        if (iterations >= MAX_CHUNKS) throw new Error('WebPの構造を安全に確認できませんでした。');
        return false;
    }

    function skipGifSubBlocks(bytes, start) {
        let offset = start;
        let iterations = 0;
        while (offset < bytes.length && iterations < MAX_CHUNKS) {
            iterations += 1;
            const length = bytes[offset];
            offset += 1;
            if (length === 0) return offset;
            if (length > bytes.length - offset) throw new Error('GIFデータが途中で切れています。');
            offset += length;
        }
        throw new Error(iterations >= MAX_CHUNKS ? 'GIFの構造を安全に確認できませんでした。' : 'GIFデータが途中で切れています。');
    }

    function countGifFrames(buffer) {
        const bytes = asBytes(buffer);
        if (detectFileFormat(bytes) !== 'gif' || bytes.length < 13) throw new Error('GIFデータが壊れています。');
        const packed = bytes[10];
        let offset = 13;
        if ((packed & 0x80) !== 0) {
            const tableBytes = 3 * (1 << ((packed & 0x07) + 1));
            if (tableBytes > bytes.length - offset) throw new Error('GIFデータが途中で切れています。');
            offset += tableBytes;
        }
        let frames = 0;
        let iterations = 0;
        while (offset < bytes.length && iterations < MAX_CHUNKS) {
            iterations += 1;
            const marker = bytes[offset];
            offset += 1;
            if (marker === 0x3b) return frames;
            if (marker === 0x21) {
                if (offset >= bytes.length) throw new Error('GIFデータが途中で切れています。');
                offset += 1;
                offset = skipGifSubBlocks(bytes, offset);
                continue;
            }
            if (marker === 0x2c) {
                if (offset + 9 > bytes.length) throw new Error('GIFデータが途中で切れています。');
                const descriptorPacked = bytes[offset + 8];
                offset += 9;
                if ((descriptorPacked & 0x80) !== 0) {
                    const tableBytes = 3 * (1 << ((descriptorPacked & 0x07) + 1));
                    if (tableBytes > bytes.length - offset) throw new Error('GIFデータが途中で切れています。');
                    offset += tableBytes;
                }
                if (offset >= bytes.length) throw new Error('GIFデータが途中で切れています。');
                offset += 1;
                offset = skipGifSubBlocks(bytes, offset);
                frames += 1;
                if (frames >= 2) return frames;
                continue;
            }
            throw new Error('GIFの構造を確認できませんでした。');
        }
        throw new Error(iterations >= MAX_CHUNKS ? 'GIFの構造を安全に確認できませんでした。' : 'GIFデータが途中で切れています。');
    }

    function parseBmp(buffer) {
        const bytes = asBytes(buffer);
        if (bytes.length < 54 || bytesToAscii(bytes, 0, 2) !== 'BM') throw new Error('BMPデータが壊れています。');
        const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
        const declaredSize = view.getUint32(2, true);
        const pixelOffset = view.getUint32(10, true);
        const dibSize = view.getUint32(14, true);
        if (declaredSize < 54 || declaredSize > bytes.length || pixelOffset < 54 || pixelOffset >= declaredSize) throw new Error('BMPのファイル構造が不正です。');
        if (dibSize < 40 || dibSize > 124 || 14 + dibSize > pixelOffset || 14 + dibSize > bytes.length) throw new Error('このBMPヘッダーには対応していません。');
        const width = view.getInt32(18, true);
        const height = view.getInt32(22, true);
        const planes = view.getUint16(26, true);
        const bitsPerPixel = view.getUint16(28, true);
        const compression = view.getUint32(30, true);
        if (width <= 0 || height === 0 || Math.abs(height) > 100000 || width > 100000 || planes !== 1) throw new Error('BMPの画像サイズまたは構造が不正です。');
        if (![24, 32].includes(bitsPerPixel) || compression !== 0) throw new Error('対応しているBMPは非圧縮の24bit・32bitです。');
        return { width, height: Math.abs(height), bitsPerPixel, compression, pixelOffset, declaredSize };
    }

    function unsupportedMessage(format) {
        const messages = {
            heif: 'HEIC・HEIFには現在対応していません。',
            tiff: 'TIFFには現在対応していません。',
            svg: 'SVGは安全性とベクター情報維持の観点から対象外です。',
            ico: 'ICOには現在対応していません。',
        };
        return messages[format] || '対応していない画像形式です。';
    }

    function validateFileIdentity(filename, mime, buffer, options) {
        const allowed = new Set((options && options.allowedFormats) || ['jpeg', 'png', 'webp']);
        const extensionFormat = EXTENSION_FORMAT[getExtension(filename)] || null;
        const normalizedMime = String(mime || '').trim().toLowerCase();
        const mimeFormat = normalizedMime ? (MIME_FORMAT[normalizedMime] || null) : null;
        const detectedFormat = detectFileFormat(buffer);
        const explicitlyUnsupported = extensionFormat && ['heif', 'tiff', 'svg', 'ico'].includes(extensionFormat)
            ? extensionFormat : (mimeFormat && ['heif', 'tiff', 'svg', 'ico'].includes(mimeFormat) ? mimeFormat : detectedFormat);
        if (explicitlyUnsupported && ['heif', 'tiff', 'svg', 'ico'].includes(explicitlyUnsupported)) throw new Error(unsupportedMessage(explicitlyUnsupported));
        if (!extensionFormat || !detectedFormat || (normalizedMime && !mimeFormat)) throw new Error('対応していない画像形式、または画像データが壊れています。');
        if (extensionFormat !== detectedFormat || (mimeFormat && mimeFormat !== detectedFormat)) throw new Error('拡張子、MIMEタイプ、画像データの形式が一致していません。');
        if (!allowed.has(detectedFormat)) throw new Error(unsupportedMessage(detectedFormat));
        if (detectedFormat === 'avif' && parseIsoBrands(buffer).brands.includes('avis')) {
            throw new Error('AVIFシーケンスやアニメーションAVIFには対応していません。静止AVIFを選択してください。');
        }
        if (detectedFormat === 'png' && detectApng(buffer)) throw new Error('アニメーションPNGには対応していません。');
        if (detectedFormat === 'webp' && detectAnimatedWebp(buffer)) throw new Error('アニメーションWebPには対応していません。');
        if (detectedFormat === 'gif') {
            const frames = countGifFrames(buffer);
            if (frames !== 1) throw new Error(frames > 1 ? 'アニメーションGIFには対応していません。静止GIFを選択してください。' : 'GIF画像のフレームを確認できませんでした。');
        }
        if (detectedFormat === 'bmp') parseBmp(buffer);
        return detectedFormat;
    }

    function validateEncodedBuffer(buffer, expectedFormat, reportedMime) {
        if (!OUTPUT_FORMATS.has(expectedFormat)) throw new Error('出力形式を確認してください。');
        const expectedMime = FORMAT_MIME[expectedFormat];
        const detectedFormat = detectFileFormat(buffer);
        if (reportedMime !== expectedMime || detectedFormat !== expectedFormat) {
            if (expectedFormat === 'avif') throw new Error('このブラウザではAVIF形式で保存できません。');
            throw new Error('要求した形式と生成された画像データが一致しません。');
        }
        return true;
    }

    function validateImageLimits(width, height, maxPixels, maxLongEdge) {
        if (!Number.isSafeInteger(width) || !Number.isSafeInteger(height) || width < 1 || height < 1) throw new Error('画像の寸法を確認できませんでした。');
        if (width > maxLongEdge || height > maxLongEdge) throw new Error(`画像の長辺は${maxLongEdge.toLocaleString('ja-JP')}px以下にしてください。`);
        if (width * height > maxPixels) throw new Error(`画像は最大${maxPixels.toLocaleString('ja-JP')}画素までです。`);
        return true;
    }

    function sanitizeFilename(filename) {
        const leaf = String(filename || '').replace(/\\/g, '/').split('/').pop();
        const cleaned = leaf.replace(/[\u0000-\u001f\u007f<>:"/\\|?*]/g, '_').trim();
        return cleaned || 'image';
    }

    function ensureOutputFilename(candidate, format, usedNames) {
        const extension = FORMAT_EXTENSION[format];
        if (!extension || !OUTPUT_FORMATS.has(format)) throw new Error('出力形式を確認してください。');
        const cleaned = sanitizeFilename(candidate);
        const dot = cleaned.lastIndexOf('.');
        let rawBase = dot > 0 ? cleaned.slice(0, dot) : cleaned;
        while (/\.(?:jpe?g|png|webp|gif|bmp|avif)$/i.test(rawBase)) rawBase = rawBase.replace(/\.[^.]+$/, '');
        const base = (rawBase || 'image').slice(0, 180);
        let sequence = 1;
        let output = `${base}.${extension}`;
        while (usedNames && usedNames.has(output.toLowerCase())) {
            sequence += 1;
            output = `${base}_${sequence}.${extension}`;
        }
        if (usedNames) usedNames.add(output.toLowerCase());
        return output;
    }

    async function loadImageElement(file) {
        if (typeof Image === 'undefined' || typeof URL === 'undefined') throw new Error('この環境では画像を読み込めません。');
        return new Promise((resolve, reject) => {
            const image = new Image();
            const url = URL.createObjectURL(file);
            const release = () => URL.revokeObjectURL(url);
            image.onload = () => { release(); resolve(image); };
            image.onerror = () => { release(); reject(new Error('このブラウザでは画像を読み込めません。')); };
            image.src = url;
        });
    }

    async function decodeImageFile(file) {
        if (typeof createImageBitmap === 'function') {
            try {
                const bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' });
                return { source: bitmap, width: bitmap.width, height: bitmap.height, release: () => bitmap.close() };
            } catch (error) {
                // HTMLImageElement is the compatibility fallback.
            }
        }
        const image = await loadImageElement(file);
        return { source: image, width: image.naturalWidth || image.width, height: image.naturalHeight || image.height, release: function () {} };
    }

    async function canDecodeFile(file) {
        let decoded = null;
        try {
            decoded = await decodeImageFile(file);
            return decoded.width > 0 && decoded.height > 0;
        } catch (error) {
            return false;
        } finally {
            if (decoded) decoded.release();
        }
    }

    function canvasToBlob(canvas, mime, quality) {
        return new Promise((resolve) => canvas.toBlob(resolve, mime, quality));
    }

    async function detectAvifEncodeSupport() {
        if (typeof document === 'undefined') return false;
        const canvas = document.createElement('canvas');
        canvas.width = 2;
        canvas.height = 2;
        const context = canvas.getContext('2d');
        if (!context) return false;
        context.fillStyle = '#ffffff';
        context.fillRect(0, 0, 2, 2);
        let blob = null;
        let decoded = null;
        try {
            blob = await canvasToBlob(canvas, FORMAT_MIME.avif, 0.8);
            if (!blob) return false;
            const buffer = await blob.arrayBuffer();
            validateEncodedBuffer(buffer, 'avif', blob.type);
            decoded = await decodeImageFile(blob);
            return decoded.width === 2 && decoded.height === 2;
        } catch (error) {
            return false;
        } finally {
            if (decoded) decoded.release();
            canvas.width = 0;
            canvas.height = 0;
            blob = null;
        }
    }

    function makeProbeBlob(format) {
        if (typeof Blob === 'undefined') return null;
        if (format === 'gif') {
            return new Blob([Uint8Array.from([
                0x47,0x49,0x46,0x38,0x39,0x61,0x01,0x00,0x01,0x00,0x80,0x00,0x00,
                0x00,0x00,0x00,0xff,0xff,0xff,0x21,0xf9,0x04,0x01,0x00,0x00,0x00,0x00,
                0x2c,0x00,0x00,0x00,0x00,0x01,0x00,0x01,0x00,0x00,0x02,0x02,0x44,0x01,0x00,0x3b,
            ])], { type: FORMAT_MIME.gif });
        }
        if (format === 'bmp') {
            const bytes = new Uint8Array(58);
            const view = new DataView(bytes.buffer);
            bytes[0] = 0x42; bytes[1] = 0x4d;
            view.setUint32(2, 58, true); view.setUint32(10, 54, true); view.setUint32(14, 40, true);
            view.setInt32(18, 1, true); view.setInt32(22, 1, true); view.setUint16(26, 1, true);
            view.setUint16(28, 24, true); view.setUint32(34, 4, true);
            bytes[54] = 0xff; bytes[55] = 0xff; bytes[56] = 0xff;
            return new Blob([bytes], { type: FORMAT_MIME.bmp });
        }
        return null;
    }

    async function detectRuntimeInputSupport(format) {
        const probe = makeProbeBlob(format);
        if (!probe) return false;
        return canDecodeFile(probe);
    }

    return Object.freeze({
        FORMAT_MIME, FORMAT_EXTENSION, EXTENSION_FORMAT, MIME_FORMAT,
        getExtension, detectFileFormat, parseIsoBrands, detectApng, detectAnimatedWebp,
        countGifFrames, parseBmp, validateFileIdentity, validateEncodedBuffer,
        validateImageLimits, sanitizeFilename, ensureOutputFilename,
        decodeImageFile, canDecodeFile, detectAvifEncodeSupport,
        detectRuntimeInputSupport,
    });
});
