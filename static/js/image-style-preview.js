/**
 * 枠・余白・角丸の即時プレビュー（サンプル画像で表示、アップロード不要）
 * image-cleanup の「枠・余白・角丸」セクション用。image-style.js の apply* を利用。
 */
(function () {
    'use strict';

    const DEBOUNCE_MS = 150;
    const PREVIEW_WIDTH = 360;
    const PREVIEW_HEIGHT = 240;
    const SAMPLE_WIDTH = 280;
    const SAMPLE_HEIGHT = 180;

    let sampleCanvas = null;
    let debounceTimer = null;

    function createSampleCanvas() {
        const c = document.createElement('canvas');
        c.width = SAMPLE_WIDTH;
        c.height = SAMPLE_HEIGHT;
        const ctx = c.getContext('2d');
        const g = ctx.createLinearGradient(0, 0, c.width, c.height);
        g.addColorStop(0, '#5a6a8a');
        g.addColorStop(0.5, '#4a5a7a');
        g.addColorStop(1, '#3a4a6a');
        ctx.fillStyle = g;
        ctx.fillRect(0, 0, c.width, c.height);
        ctx.fillStyle = 'rgba(255,255,255,0.15)';
        ctx.fillRect(20, 20, c.width - 40, c.height - 40);
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 28px "Noto Sans JP", sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('SAMPLE', c.width / 2, c.height / 2 - 12);
        ctx.font = '14px sans-serif';
        ctx.fillText('余白・角丸・枠のプレビュー', c.width / 2, c.height / 2 + 18);
        ctx.strokeStyle = 'rgba(255,255,255,0.4)';
        ctx.lineWidth = 2;
        ctx.strokeRect(24, 24, c.width - 48, c.height - 48);
        return c;
    }

    function getStyleOptionsFromDom() {
        const padding = parseInt(document.getElementById('style-padding')?.value, 10) || 0;
        const radius = parseInt(document.getElementById('style-radius')?.value, 10) || 0;
        const borderWidth = parseInt(document.getElementById('style-border-width')?.value, 10) || 0;
        const borderColorSel = document.getElementById('style-border-color')?.value;
        const borderColor = borderColorSel === 'custom'
            ? (document.getElementById('style-border-color-custom')?.value || '#000000')
            : (borderColorSel || '#000000');
        const bgSel = document.getElementById('style-bg-color')?.value;
        const bgColor = bgSel === 'custom'
            ? (document.getElementById('style-bg-color-custom')?.value || '#ffffff')
            : (bgSel === 'transparent' ? 'transparent' : (bgSel || '#ffffff'));
        return { padding, radius, borderWidth, borderColor, bgColor };
    }

    function normalizeHex(s) {
        if (!s || s === 'transparent') return s;
        if (/^#[0-9a-fA-F]{6}$/.test(s)) return s;
        if (/^#[0-9a-fA-F]{3}$/.test(s)) {
            const r = s[1] + s[1], g = s[2] + s[2], b = s[3] + s[3];
            return '#' + r + g + b;
        }
        return s;
    }

    function renderPreview() {
        const canvas = document.getElementById('style-preview-canvas');
        if (!canvas || typeof ImageStyle === 'undefined') return;
        if (!sampleCanvas) sampleCanvas = createSampleCanvas();

        const opts = getStyleOptionsFromDom();
        const pad = opts.padding;
        const rad = opts.radius;
        const border = opts.borderWidth;
        const borderColor = normalizeHex(opts.borderColor);
        const bgColor = normalizeHex(opts.bgColor);

        let c = sampleCanvas;
        if (pad > 0) c = ImageStyle.applyPadding(c, pad, bgColor);
        if (rad > 0) c = ImageStyle.applyRoundedCorners(c, rad, bgColor);
        if (border > 0) c = ImageStyle.applyBorder(c, border, borderColor);

        const ctx = canvas.getContext('2d');
        const scale = Math.min(PREVIEW_WIDTH / c.width, PREVIEW_HEIGHT / c.height, 1);
        const dx = (PREVIEW_WIDTH - c.width * scale) / 2;
        const dy = (PREVIEW_HEIGHT - c.height * scale) / 2;
        ctx.fillStyle = 'rgba(0,0,0,0.3)';
        ctx.fillRect(0, 0, PREVIEW_WIDTH, PREVIEW_HEIGHT);
        ctx.drawImage(c, dx, dy, c.width * scale, c.height * scale);
    }

    function scheduleRender() {
        if (debounceTimer) clearTimeout(debounceTimer);
        debounceTimer = setTimeout(function () {
            debounceTimer = null;
            renderPreview();
        }, DEBOUNCE_MS);
    }

    const PRESETS = {
        clean: { padding: 48, radius: 8, borderWidth: 2, borderColor: 'custom', borderColorCustom: '#111111', bgColor: '#ffffff', bgColorCustom: '#ffffff' },
        sns:   { padding: 64, radius: 24, borderWidth: 0, borderColor: '#000000', borderColorCustom: '#000000', bgColor: '#ffffff', bgColorCustom: '#ffffff' },
        soft:  { padding: 40, radius: 32, borderWidth: 4, borderColor: 'custom', borderColorCustom: '#ffffff', bgColor: 'custom', bgColorCustom: '#111111' }
    };

    function applyPreset(presetName) {
        const p = PRESETS[presetName];
        if (!p) return;
        const padEl = document.getElementById('style-padding');
        const radEl = document.getElementById('style-radius');
        const borderEl = document.getElementById('style-border-width');
        const borderSel = document.getElementById('style-border-color');
        const borderCustom = document.getElementById('style-border-color-custom');
        const bgSel = document.getElementById('style-bg-color');
        const bgCustom = document.getElementById('style-bg-color-custom');
        const padVal = document.getElementById('padding-value');
        const radVal = document.getElementById('radius-value');
        const borderVal = document.getElementById('border-width-value');
        if (padEl) { padEl.value = p.padding; if (padVal) padVal.textContent = p.padding; }
        if (radEl) { radEl.value = p.radius; if (radVal) radVal.textContent = p.radius; }
        if (borderEl) { borderEl.value = p.borderWidth; if (borderVal) borderVal.textContent = p.borderWidth; }
        if (borderSel) borderSel.value = p.borderColor;
        if (borderCustom) borderCustom.value = p.borderColorCustom;
        if (bgSel) bgSel.value = p.bgColor;
        if (bgCustom) bgCustom.value = p.bgColorCustom;
        if (typeof toggleStyleBorderCustom === 'function') toggleStyleBorderCustom();
        if (typeof toggleStyleBgCustom === 'function') toggleStyleBgCustom();
        renderPreview();
    }

    function bindPresets() {
        document.querySelectorAll('.style-preview__presets [data-preset]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                applyPreset(this.getAttribute('data-preset'));
            });
        });
    }

    function bindInputs() {
        const ids = ['style-padding', 'style-radius', 'style-border-width', 'style-border-color', 'style-border-color-custom', 'style-bg-color', 'style-bg-color-custom'];
        ids.forEach(function (id) {
            const el = document.getElementById(id);
            if (el) {
                el.addEventListener('input', scheduleRender);
                el.addEventListener('change', scheduleRender);
            }
        });
    }

    function initStylePreview() {
        const canvas = document.getElementById('style-preview-canvas');
        if (!canvas) return;
        bindInputs();
        bindPresets();
        renderPreview();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initStylePreview);
    } else {
        initStylePreview();
    }
})();
