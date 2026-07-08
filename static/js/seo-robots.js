/**
 * robots.txt生成ユーティリティ
 */

class SeoRobots {
    /**
     * robots.txtを生成
     * @param {Object} options - オプション
     * @param {boolean} options.allowAll - すべてを許可するか
     * @param {string} options.disallowPaths - 禁止パス（改行区切り）
     * @param {string} options.sitemapUrl - sitemap.xmlのURL
     * @param {string} options.userAgent - User-agent（既定: "*"）
     * @returns {string} - robots.txt文字列
     */
    static buildRobotsTxt(options = {}) {
        const {
            allowAll = true,
            disallowPaths = '',
            sitemapUrl = '',
            userAgent = '*'
        } = options;

        let txt = '';

        // User-agent
        txt += `User-agent: ${userAgent}\n`;

        // Disallow設定
        if (allowAll) {
            // 禁止パスがある場合のみDisallowを追加
            const paths = disallowPaths.split('\n')
                .map(line => line.trim())
                .filter(line => line.length > 0 && !line.startsWith('#'));

            if (paths.length > 0) {
                paths.forEach(path => {
                    txt += `Disallow: ${path}\n`;
                });
            }
            // 禁止パスが無い場合は何も書かない（全許可）
        } else {
            // 全禁止
            txt += 'Disallow: /\n';
        }

        txt += '\n';

        // Sitemap
        if (sitemapUrl && sitemapUrl.length > 0) {
            txt += `Sitemap: ${sitemapUrl}\n`;
        }

        return txt;
    }
}
