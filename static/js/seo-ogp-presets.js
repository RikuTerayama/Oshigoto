/**
 * OGP画像プリセット定義
 */

class SeoOgpPresets {
    /**
     * プリセット一覧を取得
     * @returns {Array<{id: string, name: string, width: number, height: number}>}
     */
    static getPresets() {
        return [
            {
                id: 'ogp_1200_630',
                name: 'OGP標準 (1200x630)',
                width: 1200,
                height: 630
            },
            {
                id: 'square_1080',
                name: '正方形 (1080x1080)',
                width: 1080,
                height: 1080
            },
            {
                id: 'wide_1200_675',
                name: 'ワイド (1200x675)',
                width: 1200,
                height: 675
            }
        ];
    }

    /**
     * プリセットIDからプリセットを取得
     * @param {string} presetId - プリセットID
     * @returns {Object|null}
     */
    static getPresetById(presetId) {
        return this.getPresets().find(p => p.id === presetId) || null;
    }
}

window.SeoOgpPresets = SeoOgpPresets;
console.debug('[seo-ogp-presets] loaded', true);
