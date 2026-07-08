/**
 * sitemap.xml生成ユーティリティ
 */

class SeoSitemap {
    /**
     * URLリストを正規化
     * @param {string} baseUrl - ベースURL
     * @param {string} urlList - URLリスト（改行区切り）
     * @returns {Object} - { urls: string[], warnings: string[] }
     */
    static normalizeUrls(baseUrl, urlList) {
        const warnings = [];
        const urlSet = new Set();
        const lines = urlList.split('\n').map(line => line.trim()).filter(line => line.length > 0);

        // baseUrlのバリデーション
        if (!baseUrl || baseUrl.length === 0) {
            warnings.push('baseUrlが空です');
            return { urls: [], warnings };
        }

        try {
            const baseUrlObj = new URL(baseUrl);
            if (baseUrlObj.protocol !== 'http:' && baseUrlObj.protocol !== 'https:') {
                warnings.push(`baseUrlが無効です: ${baseUrl}`);
                return { urls: [], warnings };
            }
        } catch (e) {
            warnings.push(`baseUrlが無効です: ${baseUrl}`);
            return { urls: [], warnings };
        }

        // 各行を処理
        lines.forEach((line, index) => {
            // コメント行をスキップ
            if (line.startsWith('#')) {
                return;
            }

            let url = line.trim();

            // パスの場合（/で始まる）
            if (url.startsWith('/')) {
                try {
                    const fullUrl = new URL(url, baseUrl).href;
                    urlSet.add(fullUrl);
                } catch (e) {
                    warnings.push(`行${index + 1}: 無効なパス "${line}"`);
                }
            }
            // 完全なURLの場合
            else if (url.startsWith('http://') || url.startsWith('https://')) {
                try {
                    const urlObj = new URL(url);
                    if (urlObj.protocol !== 'http:' && urlObj.protocol !== 'https:') {
                        warnings.push(`行${index + 1}: 無効なプロトコル "${line}"`);
                        return;
                    }
                    urlSet.add(url);
                } catch (e) {
                    warnings.push(`行${index + 1}: 無効なURL "${line}"`);
                }
            }
            // その他（パスとして扱う）
            else {
                try {
                    const fullUrl = new URL('/' + url, baseUrl).href;
                    urlSet.add(fullUrl);
                } catch (e) {
                    warnings.push(`行${index + 1}: 無効なパス "${line}"`);
                }
            }
        });

        const urls = Array.from(urlSet).sort();

        if (urls.length === 0) {
            warnings.push('有効なURLが1件も見つかりませんでした');
        }

        return { urls, warnings };
    }

    /**
     * sitemap.xmlを生成
     * @param {string[]} urls - URLリスト
     * @param {Object} options - オプション
     * @param {string} options.lastmodMode - lastmodモード（'none' | 'today'）
     * @param {string} options.changefreq - changefreq（'always' | 'hourly' | 'daily' | 'weekly' | 'monthly' | 'yearly' | 'never'）
     * @param {number} options.priority - priority（0.1-1.0）
     * @returns {string} - XML文字列
     */
    static buildSitemapXml(urls, options = {}) {
        const {
            lastmodMode = 'today',
            changefreq = null,
            priority = null
        } = options;

        let xml = '<?xml version="1.0" encoding="UTF-8"?>\n';
        xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n';

        const today = new Date().toISOString().split('T')[0];

        urls.forEach(url => {
            xml += '  <url>\n';
            xml += `    <loc>${this.escapeXml(url)}</loc>\n`;

            if (lastmodMode === 'today') {
                xml += `    <lastmod>${today}</lastmod>\n`;
            }

            if (changefreq) {
                xml += `    <changefreq>${changefreq}</changefreq>\n`;
            }

            if (priority !== null) {
                xml += `    <priority>${priority}</priority>\n`;
            }

            xml += '  </url>\n';
        });

        xml += '</urlset>';

        return xml;
    }

    /**
     * XMLエスケープ
     * @param {string} str - エスケープする文字列
     * @returns {string}
     */
    static escapeXml(str) {
        return str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&apos;');
    }
}
