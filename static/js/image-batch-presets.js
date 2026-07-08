/**
 * 画像一括変換プリセット定義
 */

class ImageBatchPresets {
    /**
     * プリセット一覧を取得
     * @returns {Array<{id: string, name: string, description: string, defaultOptions: Object}>}
     */
    static getPresets() {
        return [
            {
                id: 'sns',
                name: 'SNS添付セット',
                description: 'SNS投稿用（1200px）',
                defaultOptions: {
                    variants: [{ width: 1200, suffix: '' }],
                    format: 'webp',
                    quality: 0.82,
                    preventUpscale: true,
                    renameTemplate: '{name}_{suffix}_{index}.{ext}'
                }
            },
            {
                id: 'web',
                name: 'Web軽量セット',
                description: 'Web表示用（1200px, 800px）',
                defaultOptions: {
                    variants: [
                        { width: 1200, suffix: '' },
                        { width: 800, suffix: '' }
                    ],
                    format: 'webp',
                    quality: 0.82,
                    preventUpscale: true,
                    renameTemplate: '{name}_{suffix}_{index}.{ext}'
                }
            },
            {
                id: 'ec',
                name: 'ECセット',
                description: 'ECサイト用（2000px, 1200px, 800px）',
                defaultOptions: {
                    variants: [
                        { width: 2000, suffix: '' },
                        { width: 1200, suffix: '' },
                        { width: 800, suffix: '' }
                    ],
                    format: 'jpeg',
                    quality: 0.8,
                    preventUpscale: true,
                    renameTemplate: '{name}_{suffix}_{index}.{ext}'
                }
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
