/**
 * HTMLメタタグ検査ユーティリティ
 */

class SeoHtmlInspector {
    /**
     * HTML文字列をDocumentに変換
     * @param {string} html - HTML文字列
     * @returns {Document}
     */
    static parseHtml(html) {
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        return doc;
    }

    /**
     * メタタグを抽出
     * @param {Document} doc - Documentオブジェクト
     * @returns {Object} - 抽出されたメタタグ
     */
    static extractMeta(doc) {
        const extracted = {
            title: null,
            description: null,
            canonical: null,
            robots: null,
            viewport: null,
            charset: null,
            og: {},
            twitter: {},
            hreflang: []
        };

        // title
        const titleEl = doc.querySelector('title');
        if (titleEl) {
            extracted.title = titleEl.textContent.trim();
        }

        // meta name="description"
        const descEl = doc.querySelector('meta[name="description"]');
        if (descEl) {
            extracted.description = descEl.getAttribute('content') || '';
        }

        // link rel="canonical"
        const canonicalEl = doc.querySelector('link[rel="canonical"]');
        if (canonicalEl) {
            extracted.canonical = canonicalEl.getAttribute('href') || '';
        }

        // meta name="robots"
        const robotsEl = doc.querySelector('meta[name="robots"]');
        if (robotsEl) {
            extracted.robots = robotsEl.getAttribute('content') || '';
        }

        // meta name="viewport"
        const viewportEl = doc.querySelector('meta[name="viewport"]');
        if (viewportEl) {
            extracted.viewport = viewportEl.getAttribute('content') || '';
        }

        // meta charset
        const charsetEl = doc.querySelector('meta[charset]');
        if (charsetEl) {
            extracted.charset = charsetEl.getAttribute('charset') || '';
        }

        // OGタグ
        const ogTags = ['title', 'description', 'url', 'image', 'type', 'site_name'];
        ogTags.forEach(tag => {
            const el = doc.querySelector(`meta[property="og:${tag}"]`);
            if (el) {
                extracted.og[tag] = el.getAttribute('content') || '';
            }
        });

        // Twitterタグ
        const twitterTags = ['card', 'title', 'description', 'image'];
        twitterTags.forEach(tag => {
            const el = doc.querySelector(`meta[name="twitter:${tag}"]`);
            if (el) {
                extracted.twitter[tag] = el.getAttribute('content') || '';
            }
        });

        // hreflang
        const hreflangEls = doc.querySelectorAll('link[rel="alternate"][hreflang]');
        hreflangEls.forEach(el => {
            extracted.hreflang.push({
                lang: el.getAttribute('hreflang') || '',
                href: el.getAttribute('href') || ''
            });
        });

        return extracted;
    }

    /**
     * メタタグの重複をチェック
     * @param {Document} doc - Documentオブジェクト
     * @returns {Array<{tag: string, count: number}>}
     */
    static checkDuplicates(doc) {
        const duplicates = [];

        // titleの重複
        const titles = doc.querySelectorAll('title');
        if (titles.length > 1) {
            duplicates.push({ tag: 'title', count: titles.length });
        }

        // descriptionの重複
        const descriptions = doc.querySelectorAll('meta[name="description"]');
        if (descriptions.length > 1) {
            duplicates.push({ tag: 'description', count: descriptions.length });
        }

        // canonicalの重複
        const canonicals = doc.querySelectorAll('link[rel="canonical"]');
        if (canonicals.length > 1) {
            duplicates.push({ tag: 'canonical', count: canonicals.length });
        }

        return duplicates;
    }

    /**
     * メタタグ検査を実行
     * @param {Object} extracted - 抽出されたメタタグ
     * @param {Array} duplicates - 重複情報
     * @returns {Array<{id: string, label: string, level: string, value: string, message: string}>}
     */
    static runMetaChecks(extracted, duplicates = []) {
        const checks = [];

        // title チェック
        if (!extracted.title || extracted.title.length === 0) {
            checks.push({
                id: 'title_exists',
                label: 'titleタグ',
                level: 'fail',
                value: '',
                message: 'titleタグが存在しません'
            });
        } else {
            const titleLen = extracted.title.length;
            if (titleLen < 10) {
                checks.push({
                    id: 'title_length',
                    label: 'titleタグの長さ',
                    level: 'warn',
                    value: extracted.title,
                    message: `titleが短すぎます（${titleLen}文字）。10文字以上を推奨します。`
                });
            } else if (titleLen > 60) {
                checks.push({
                    id: 'title_length',
                    label: 'titleタグの長さ',
                    level: 'warn',
                    value: extracted.title.substring(0, 60) + '...',
                    message: `titleが長すぎます（${titleLen}文字）。60文字以下を推奨します。`
                });
            } else {
                checks.push({
                    id: 'title_exists',
                    label: 'titleタグ',
                    level: 'ok',
                    value: extracted.title,
                    message: 'titleタグが適切に設定されています'
                });
            }
        }

        // description チェック
        if (!extracted.description || extracted.description.length === 0) {
            checks.push({
                id: 'description_exists',
                label: 'description',
                level: 'fail',
                value: '',
                message: 'descriptionが存在しません'
            });
        } else {
            const descLen = extracted.description.length;
            if (descLen < 50) {
                checks.push({
                    id: 'description_length',
                    label: 'descriptionの長さ',
                    level: 'warn',
                    value: extracted.description,
                    message: `descriptionが短すぎます（${descLen}文字）。50文字以上を推奨します。`
                });
            } else if (descLen > 160) {
                checks.push({
                    id: 'description_length',
                    label: 'descriptionの長さ',
                    level: 'warn',
                    value: extracted.description.substring(0, 160) + '...',
                    message: `descriptionが長すぎます（${descLen}文字）。160文字以下を推奨します。`
                });
            } else {
                checks.push({
                    id: 'description_exists',
                    label: 'description',
                    level: 'ok',
                    value: extracted.description,
                    message: 'descriptionが適切に設定されています'
                });
            }
        }

        // canonical チェック
        if (!extracted.canonical || extracted.canonical.length === 0) {
            checks.push({
                id: 'canonical_exists',
                label: 'canonical',
                level: 'warn',
                value: '',
                message: 'canonicalが設定されていません（静的サイトでは推奨）'
            });
        } else {
            if (extracted.canonical.startsWith('/')) {
                checks.push({
                    id: 'canonical_relative',
                    label: 'canonical（相対URL）',
                    level: 'warn',
                    value: extracted.canonical,
                    message: 'canonicalが相対URLです。絶対URLを推奨します。'
                });
            } else {
                checks.push({
                    id: 'canonical_exists',
                    label: 'canonical',
                    level: 'ok',
                    value: extracted.canonical,
                    message: 'canonicalが適切に設定されています'
                });
            }
        }

        // robots チェック
        if (extracted.robots && extracted.robots.toLowerCase().includes('noindex')) {
            checks.push({
                id: 'robots_noindex',
                label: 'robots（noindex）',
                level: 'warn',
                value: extracted.robots,
                message: 'robotsにnoindexが含まれています。意図したページ以外では削除を検討してください。'
            });
        } else if (extracted.robots) {
            checks.push({
                id: 'robots_exists',
                label: 'robots',
                level: 'ok',
                value: extracted.robots,
                message: 'robotsが設定されています'
            });
        }

        // charset チェック
        if (!extracted.charset || extracted.charset.length === 0) {
            checks.push({
                id: 'charset_exists',
                label: 'charset',
                level: 'warn',
                value: '',
                message: 'charsetが設定されていません（head内に推奨）'
            });
        } else {
            checks.push({
                id: 'charset_exists',
                label: 'charset',
                level: 'ok',
                value: extracted.charset,
                message: 'charsetが設定されています'
            });
        }

        // OG必須チェック
        const ogRequired = ['title', 'description', 'url', 'image'];
        const ogMissing = ogRequired.filter(tag => !extracted.og[tag] || extracted.og[tag].length === 0);
        if (ogMissing.length > 0) {
            checks.push({
                id: 'og_required',
                label: 'OG必須タグ',
                level: 'fail',
                value: `不足: ${ogMissing.join(', ')}`,
                message: `OG必須タグが不足しています: ${ogMissing.join(', ')}`
            });
        } else {
            checks.push({
                id: 'og_required',
                label: 'OG必須タグ',
                level: 'ok',
                value: 'すべて揃っています',
                message: 'OG必須タグがすべて揃っています'
            });
        }

        // Twitter必須チェック
        const twitterRequired = ['card', 'title', 'description'];
        const twitterMissing = twitterRequired.filter(tag => !extracted.twitter[tag] || extracted.twitter[tag].length === 0);
        if (twitterMissing.length > 0) {
            checks.push({
                id: 'twitter_required',
                label: 'Twitter必須タグ',
                level: 'warn',
                value: `不足: ${twitterMissing.join(', ')}`,
                message: `Twitter必須タグが不足しています: ${twitterMissing.join(', ')}`
            });
        } else {
            checks.push({
                id: 'twitter_required',
                label: 'Twitter必須タグ',
                level: 'ok',
                value: 'すべて揃っています',
                message: 'Twitter必須タグがすべて揃っています'
            });
        }

        // 重複チェック
        duplicates.forEach(dup => {
            checks.push({
                id: `duplicate_${dup.tag}`,
                label: `${dup.tag}の重複`,
                level: 'warn',
                value: `${dup.count}件`,
                message: `${dup.tag}が${dup.count}件見つかりました。1つに統一してください。`
            });
        });

        return checks;
    }

    /**
     * 検査結果のMarkdownを生成
     * @param {Object} result - 検査結果
     * @param {Array} result.items - チェック項目
     * @param {Object} result.extracted - 抽出されたメタタグ
     * @param {Object} result.summary - サマリ
     * @returns {string}
     */
    static buildMetaAuditMarkdown(result) {
        const { items, extracted, summary } = result;

        let md = '# SEOメタタグ検査結果\n\n';
        md += `**検査日時:** ${new Date().toLocaleString('ja-JP')}\n\n`;
        md += `**サマリ:** OK: ${summary.ok}件、警告: ${summary.warn}件、NG: ${summary.fail}件\n\n`;
        md += '---\n\n';

        md += '## 検査結果\n\n';

        // レベルごとにグループ化
        const failItems = items.filter(item => item.level === 'fail');
        const warnItems = items.filter(item => item.level === 'warn');
        const okItems = items.filter(item => item.level === 'ok');

        if (failItems.length > 0) {
            md += '### ❌ NG項目\n\n';
            failItems.forEach(item => {
                md += `- **${item.label}**: ${item.message}\n`;
                if (item.value) {
                    md += `  - 値: ${item.value.length > 100 ? item.value.substring(0, 100) + '...' : item.value}\n`;
                }
            });
            md += '\n';
        }

        if (warnItems.length > 0) {
            md += '### ⚠️ 警告項目\n\n';
            warnItems.forEach(item => {
                md += `- **${item.label}**: ${item.message}\n`;
                if (item.value) {
                    md += `  - 値: ${item.value.length > 100 ? item.value.substring(0, 100) + '...' : item.value}\n`;
                }
            });
            md += '\n';
        }

        if (okItems.length > 0) {
            md += '### ✅ OK項目\n\n';
            okItems.forEach(item => {
                md += `- **${item.label}**: ${item.message}\n`;
            });
            md += '\n';
        }

        md += '---\n\n';
        md += '## 抽出されたメタタグ\n\n';

        md += '### 基本メタタグ\n\n';
        md += `- **title**: ${extracted.title || '(なし)'}\n`;
        md += `- **description**: ${extracted.description || '(なし)'}\n`;
        md += `- **canonical**: ${extracted.canonical || '(なし)'}\n`;
        md += `- **robots**: ${extracted.robots || '(なし)'}\n`;
        md += `- **viewport**: ${extracted.viewport || '(なし)'}\n`;
        md += `- **charset**: ${extracted.charset || '(なし)'}\n\n`;

        if (Object.keys(extracted.og).length > 0) {
            md += '### OGタグ\n\n';
            Object.entries(extracted.og).forEach(([key, value]) => {
                md += `- **og:${key}**: ${value || '(なし)'}\n`;
            });
            md += '\n';
        }

        if (Object.keys(extracted.twitter).length > 0) {
            md += '### Twitterタグ\n\n';
            Object.entries(extracted.twitter).forEach(([key, value]) => {
                md += `- **twitter:${key}**: ${value || '(なし)'}\n`;
            });
            md += '\n';
        }

        if (extracted.hreflang.length > 0) {
            md += '### hreflang\n\n';
            extracted.hreflang.forEach(item => {
                md += `- **${item.lang}**: ${item.href}\n`;
            });
            md += '\n';
        }

        return md;
    }
}
