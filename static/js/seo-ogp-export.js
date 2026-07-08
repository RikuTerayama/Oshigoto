/**
 * OGP画像エクスポート
 */

class SeoOgpExport {
    /**
     * OGP画像をエクスポート
     * @param {Object} options - オプション
     * @returns {Promise<{blob: Blob, filename: string, mime: string}>}
     */
    static async exportOgpImage(options) {
        const canvas = SeoOgpCanvas.createOgpCanvas(options);
        const blob = await SeoOgpCanvas.canvasToBlob(
            canvas, 
            options.format || 'png', 
            options.quality || 0.9
        );

        // ファイル名を生成
        const preset = SeoOgpPresets.getPresetById(options.presetId);
        const fileSlug = options.fileSlug 
            ? FileValidation.sanitizeFilename(options.fileSlug)
            : 'ogp';
        const ext = options.format === 'jpeg' || options.format === 'jpg' ? 'jpg' : 'png';
        const filename = `ogp_${fileSlug}_${preset.width}x${preset.height}.${ext}`;

        return {
            blob,
            filename,
            mime: blob.type
        };
    }

    /**
     * OGPメタタグ例を生成
     * @param {Object} options - オプション
     * @param {string} imageUrl - 画像URL（プレースホルダー）
     * @returns {string}
     */
    static generateMetaTags(options, imageUrl = '/ogp/{fileSlug}.png') {
        const fileSlug = options.fileSlug || 'ogp';
        const preset = SeoOgpPresets.getPresetById(options.presetId);
        const actualImageUrl = imageUrl.replace('{fileSlug}', fileSlug);
        const ext = options.format === 'jpeg' || options.format === 'jpg' ? 'jpg' : 'png';
        const finalImageUrl = actualImageUrl.replace('.png', `.${ext}`);

        let meta = `<!-- OGPメタタグ例 -->\n`;
        meta += `<meta property="og:title" content="${options.title || ''}">\n`;
        if (options.subtitle) {
            meta += `<meta property="og:description" content="${options.subtitle}">\n`;
        }
        meta += `<meta property="og:image" content="${finalImageUrl}">\n`;
        meta += `<meta property="og:image:width" content="${preset.width}">\n`;
        meta += `<meta property="og:image:height" content="${preset.height}">\n`;
        meta += `<meta property="og:type" content="website">\n`;
        meta += `<meta property="og:url" content="https://example.com/page">\n`;

        return meta;
    }
}

window.SeoOgpExport = SeoOgpExport;
console.debug('[seo-ogp-export] loaded', true);
