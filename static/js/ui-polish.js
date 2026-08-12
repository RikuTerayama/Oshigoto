/** Quiet visual polish: capability-aware cursor halo and text-link decoration. */
(function() {
    'use strict';

    var finePointer = window.matchMedia && window.matchMedia('(hover: hover) and (pointer: fine)');
    var reducedMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)');
    var halo = null;
    var frame = 0;
    var x = -100;
    var y = -100;

    function motionAllowed() {
        return Boolean(finePointer && finePointer.matches && !(reducedMotion && reducedMotion.matches));
    }

    function removeHalo() {
        if (halo) {
            halo.remove();
            halo = null;
        }
    }

    function paint() {
        frame = 0;
        if (!halo) return;
        halo.style.setProperty('--ui-cursor-x', x + 'px');
        halo.style.setProperty('--ui-cursor-y', y + 'px');
    }

    function requestPaint() {
        if (!frame) frame = window.requestAnimationFrame(paint);
    }

    function updateState(target) {
        if (!halo || !(target instanceof Element)) return;
        var input = target.closest('input, textarea, select, [contenteditable="true"]');
        var interactive = target.closest('a, button, summary, [role="button"], .tool-card-v2, .tool-catalog-card, .related-content__card');
        var primary = target.closest('.btn-primary, .link-button');
        halo.classList.toggle('is-input', Boolean(input));
        halo.classList.toggle('is-interactive', Boolean(interactive) && !input);
        halo.classList.toggle('is-primary', Boolean(primary) && !input);
    }

    function createHalo() {
        if (!motionAllowed() || halo) return;
        halo = document.createElement('span');
        halo.className = 'ui-cursor-halo';
        halo.setAttribute('aria-hidden', 'true');
        document.body.appendChild(halo);
    }

    function syncCapability() {
        if (motionAllowed()) createHalo();
        else removeHalo();
    }

    function markTextLinks() {
        var excluded = [
            '.btn', '.button', '.link-button', '.guide-card', '[download]',
            '.hero-tool-card', '.guide-preview-card', '.related-content__card', '.seo-link-hub__card',
            '.amazon-single-card', '.affiliate-cards-section', '.a8-creative-slot', '.affiliate-slot'
        ].join(',');
        document.querySelectorAll('.site-footer__summary a, .site-footer__copy a, footer h4 + div > a, main p > a, .related-content__intro a').forEach(function(link) {
            if (!link.matches(excluded) && !link.closest('.amazon-single-card, .affiliate-cards-section, .a8-creative-slot, .affiliate-slot')) {
                link.classList.add('ui-text-link');
            }
        });
    }

    function prepareFileDropzones() {
        document.querySelectorAll('[data-file-dropzone]').forEach(function(dropzone) {
            var input = dropzone.querySelector('input[type="file"]');
            if (!dropzone.hasAttribute('role')) dropzone.setAttribute('role', 'button');
            if (!dropzone.hasAttribute('tabindex')) dropzone.setAttribute('tabindex', '0');

            if (input && !dropzone.classList.contains('compress-dropzone')) {
                dropzone.addEventListener('keydown', function(event) {
                    if (event.key !== 'Enter' && event.key !== ' ') return;
                    event.preventDefault();
                    dropzone.click();
                });
            }

            ['dragenter', 'dragover'].forEach(function(name) {
                dropzone.addEventListener(name, function() { dropzone.classList.add('is-dragging'); });
            });
            ['dragleave', 'drop'].forEach(function(name) {
                dropzone.addEventListener(name, function() { dropzone.classList.remove('is-dragging'); });
            });
        });
    }

    function init() {
        markTextLinks();
        prepareFileDropzones();
        syncCapability();

        document.addEventListener('pointermove', function(event) {
            if (!halo || event.pointerType === 'touch') return;
            x = event.clientX;
            y = event.clientY;
            halo.classList.add('is-visible');
            updateState(event.target);
            requestPaint();
        }, { passive: true });

        document.addEventListener('pointerleave', function() {
            if (halo) halo.classList.remove('is-visible');
        });
        window.addEventListener('blur', function() {
            if (halo) halo.classList.remove('is-visible');
        });

        [finePointer, reducedMotion].forEach(function(query) {
            if (!query) return;
            if (query.addEventListener) query.addEventListener('change', syncCapability);
            else if (query.addListener) query.addListener(syncCapability);
        });
    }

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
    else init();
})();
