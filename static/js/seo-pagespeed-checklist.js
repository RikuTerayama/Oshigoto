/**
 * PageSpeed改善チェックリスト生成
 */

class SeoPageSpeedChecklist {
    /**
     * チェックリストMarkdownを生成
     * @param {Object} options - オプション
     * @returns {string}
     */
    static buildChecklistMarkdown(options) {
        const {
            targetUrl = '',
            goal = 'other',
            framework = 'other',
            priority = 'balanced',
            includeThirdParty = true,
            includeImages = true,
            includeFonts = true,
            includeCaching = true
        } = options;

        let md = '# PageSpeed改善チェックリスト\n\n';

        // ヘッダー情報
        if (targetUrl) {
            md += `**対象URL:** ${targetUrl}\n\n`;
        }
        md += `**目的:** ${this.getGoalName(goal)}\n`;
        md += `**フレームワーク:** ${this.getFrameworkName(framework)}\n`;
        md += `**優先指標:** ${this.getPriorityName(priority)}\n\n`;
        md += '---\n\n';

        // Core Web Vitals
        md += '## Core Web Vitals\n\n';
        md += this.getCoreWebVitalsSection(priority);
        md += '\n';

        // 画像最適化
        if (includeImages) {
            md += '## 画像最適化\n\n';
            md += this.getImagesSection(framework);
            md += '\n';
        }

        // フォント最適化
        if (includeFonts) {
            md += '## フォント最適化\n\n';
            md += this.getFontsSection(framework);
            md += '\n';
        }

        // JavaScriptとCSS
        md += '## JavaScriptとCSS\n\n';
        md += this.getJsCssSection(framework);
        md += '\n';

        // キャッシュと配信
        if (includeCaching) {
            md += '## キャッシュと配信\n\n';
            md += this.getCachingSection(framework);
            md += '\n';
        }

        // 外部スクリプト
        if (includeThirdParty) {
            md += '## 外部スクリプト\n\n';
            md += this.getThirdPartySection(goal);
            md += '\n';
        }

        // フレームワーク固有
        if (framework !== 'other') {
            md += `## ${this.getFrameworkName(framework)}固有の最適化\n\n`;
            md += this.getFrameworkSpecificSection(framework);
            md += '\n';
        }

        // 目的固有
        if (goal !== 'other') {
            md += `## ${this.getGoalName(goal)}向け最適化\n\n`;
            md += this.getGoalSpecificSection(goal);
            md += '\n';
        }

        return md;
    }

    static getGoalName(goal) {
        const names = {
            adsense: 'AdSense承認',
            blog: 'ブログ',
            ec: 'ECサイト',
            corporate: 'コーポレートサイト',
            other: 'その他'
        };
        return names[goal] || 'その他';
    }

    static getFrameworkName(framework) {
        const names = {
            nextjs: 'Next.js',
            static: '静的サイト',
            wordpress: 'WordPress',
            other: 'その他'
        };
        return names[framework] || 'その他';
    }

    static getPriorityName(priority) {
        const names = {
            lcp: 'LCP（最大コンテンツの表示）',
            cls: 'CLS（累積レイアウトシフト）',
            inp: 'INP（操作までの応答性）',
            balanced: 'バランス型'
        };
        return names[priority] || 'バランス型';
    }

    static getCoreWebVitalsSection(priority) {
        let section = '- [ ] LCP（最大コンテンツの表示）を2.5秒以内にする\n';
        section += '- [ ] CLS（累積レイアウトシフト）を0.1以下にする\n';
        section += '- [ ] INP（操作までの応答性）を200ms以下にする\n';
        section += '- [ ] FID（初回入力遅延）を100ms以下にする\n';

        if (priority === 'lcp') {
            section += '\n**LCP改善の重点項目:**\n';
            section += '- [ ] サーバー応答時間を短縮する\n';
            section += '- [ ] レンダリングブロックリソースを削減する\n';
            section += '- [ ] リソース読み込み時間を短縮する\n';
        } else if (priority === 'cls') {
            section += '\n**CLS改善の重点項目:**\n';
            section += '- [ ] 画像と動画にサイズ属性を指定する\n';
            section += '- [ ] 広告や埋め込みコンテンツにサイズを指定する\n';
            section += '- [ ] フォント読み込み時のFOIT/FOUTを防ぐ\n';
        } else if (priority === 'inp') {
            section += '\n**INP改善の重点項目:**\n';
            section += '- [ ] JavaScriptの実行時間を短縮する\n';
            section += '- [ ] イベントハンドラーの処理を最適化する\n';
            section += '- [ ] メインスレッドのブロッキングを削減する\n';
        }

        return section;
    }

    static getImagesSection(framework) {
        let section = '- [ ] 画像を適切なサイズで配信する（srcset使用）\n';
        section += '- [ ] 画像形式を最適化する（WebP/AVIF対応）\n';
        section += '- [ ] 画像を遅延読み込みする（loading="lazy"）\n';
        section += '- [ ] 画像にwidth/height属性を指定する\n';

        if (framework === 'nextjs') {
            section += '- [ ] Next.jsのImageコンポーネントを使用する\n';
            section += '- [ ] 画像最適化APIを有効にする\n';
        } else if (framework === 'wordpress') {
            section += '- [ ] 画像最適化プラグインを導入する\n';
        }

        return section;
    }

    static getFontsSection(framework) {
        let section = '- [ ] フォントの読み込みを最適化する（font-display: swap）\n';
        section += '- [ ] 不要なフォントを削除する\n';
        section += '- [ ] フォントのサブセット化を検討する\n';
        section += '- [ ] フォントのプリロードを検討する\n';

        if (framework === 'nextjs') {
            section += '- [ ] Next.jsのFont最適化を使用する\n';
        }

        return section;
    }

    static getJsCssSection(framework) {
        let section = '- [ ] JavaScriptとCSSを最小化する\n';
        section += '- [ ] 未使用のJavaScriptを削除する\n';
        section += '- [ ] クリティカルCSSをインライン化する\n';
        section += '- [ ] 非クリティカルCSSを遅延読み込みする\n';

        if (framework === 'nextjs') {
            section += '- [ ] 動的インポートを使用してコード分割する\n';
            section += '- [ ] ルート単位でコード分割する\n';
            section += '- [ ] Tree shakingを有効にする\n';
        } else if (framework === 'static') {
            section += '- [ ] ビルド時に未使用コードを削除する\n';
        }

        return section;
    }

    static getCachingSection(framework) {
        let section = '- [ ] ブラウザキャッシュを適切に設定する\n';
        section += '- [ ] CDNを活用する\n';
        section += '- [ ] HTTP/2またはHTTP/3を使用する\n';
        section += '- [ ] リソースの圧縮（gzip/brotli）を有効にする\n';

        if (framework === 'nextjs') {
            section += '- [ ] Next.jsの静的生成を活用する\n';
            section += '- [ ] ISR（Incremental Static Regeneration）を検討する\n';
        }

        return section;
    }

    static getThirdPartySection(goal) {
        let section = '- [ ] 外部スクリプトを遅延読み込みする\n';
        section += '- [ ] 外部スクリプトの読み込み順を最適化する\n';
        section += '- [ ] 不要な外部スクリプトを削除する\n';

        if (goal === 'adsense') {
            section += '\n**AdSense向け最適化:**\n';
            section += '- [ ] 広告タグの読み込みを最適化する\n';
            section += '- [ ] 広告の遅延読み込みを検討する\n';
            section += '- [ ] 広告の配置を最適化する\n';
            section += '- [ ] 広告の測定タグを最適化する\n';
        }

        return section;
    }

    static getFrameworkSpecificSection(framework) {
        if (framework === 'nextjs') {
            return '- [ ] next/imageを使用して画像を最適化する\n' +
                   '- [ ] next/fontを使用してフォントを最適化する\n' +
                   '- [ ] 動的インポートでコード分割する\n' +
                   '- [ ] 静的生成（SSG）を活用する\n' +
                   '- [ ] ISR（Incremental Static Regeneration）を検討する\n' +
                   '- [ ] API Routesの最適化を検討する\n';
        } else if (framework === 'wordpress') {
            return '- [ ] キャッシュプラグインを導入する\n' +
                   '- [ ] 画像最適化プラグインを導入する\n' +
                   '- [ ] 不要なプラグインを削除する\n' +
                   '- [ ] テーマの最適化を検討する\n';
        } else if (framework === 'static') {
            return '- [ ] ビルド時の最適化を有効にする\n' +
                   '- [ ] 静的アセットの最適化を検討する\n' +
                   '- [ ] プリレンダリングを検討する\n';
        }
        return '';
    }

    static getGoalSpecificSection(goal) {
        if (goal === 'adsense') {
            return '- [ ] 広告の配置を最適化する\n' +
                   '- [ ] 広告の読み込みを最適化する\n' +
                   '- [ ] コンテンツと広告のバランスを最適化する\n';
        } else if (goal === 'blog') {
            return '- [ ] 記事ページの読み込み速度を最適化する\n' +
                   '- [ ] 画像の最適化を徹底する\n' +
                   '- [ ] 関連記事の読み込みを最適化する\n';
        } else if (goal === 'ec') {
            return '- [ ] 商品画像の最適化を徹底する\n' +
                   '- [ ] カート機能の応答性を最適化する\n' +
                   '- [ ] 決済フローの最適化を検討する\n';
        } else if (goal === 'corporate') {
            return '- [ ] トップページの読み込み速度を最適化する\n' +
                   '- [ ] 企業情報ページの最適化を検討する\n';
        }
        return '';
    }
}
