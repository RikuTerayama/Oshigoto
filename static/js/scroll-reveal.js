/**
 * Scroll Reveal Animation
 * Minimal, professional scroll animations using IntersectionObserver
 * Respects prefers-reduced-motion for accessibility
 * Safe: Default visible, hidden only when JS is enabled
 */

(function() {
    'use strict';

    const root = document.documentElement;
    root.classList.add('js');

    const prefersReducedMotion = window.matchMedia &&
        window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    function initScrollProgress() {
        const progress = document.querySelector('.scroll-progress');
        if (!progress) {
            return;
        }

        const value = progress.querySelector('.scroll-progress__value');
        let ticking = false;

        function updateProgress() {
            const maxScroll = Math.max(1, root.scrollHeight - window.innerHeight);
            const currentScroll = Math.min(Math.max(window.scrollY || root.scrollTop || 0, 0), maxScroll);
            const percent = Math.round((currentScroll / maxScroll) * 100);

            progress.style.setProperty('--scroll-progress', percent + '%');
            if (value) {
                value.textContent = percent + '%';
            }
            ticking = false;
        }

        function requestUpdate() {
            if (!ticking) {
                ticking = true;
                window.requestAnimationFrame(updateProgress);
            }
        }

        window.addEventListener('scroll', requestUpdate, { passive: true });
        window.addEventListener('resize', requestUpdate);
        updateProgress();
    }

    function canReveal(el) {
        return !el.closest(
            '.affiliate-cards-section, .affiliate-context-a8, .affiliate-a8-banner, .adsbygoogle, [data-no-reveal]'
        );
    }

    function markRevealTargets() {
        const singleSelectors = [
            '.landing-page .page-header',
            '.landing-page .hero-v2__copy',
            '.landing-page .landing-hero__copy',
            '.landing-page .tool-flow',
            '.landing-page .tool-note',
            '.landing-page .tool-flow-side-box',
            '.landing-page .related-tools-heading',
            '.landing-page .content-card',
            '.landing-page .info-card'
        ];

        const staggerSelectors = [
            '.landing-page .tool-card-grid',
            '.landing-page .tool-step-list',
            '.landing-page .tool-flow-side-box__steps',
            '.landing-page .content-grid--three.glossary-grid',
            '.landing-page .landing-use-grid'
        ];

        singleSelectors.forEach(function(selector) {
            document.querySelectorAll(selector).forEach(function(el) {
                if (canReveal(el) && !el.hasAttribute('data-reveal') && !el.hasAttribute('data-reveal-stagger')) {
                    el.setAttribute('data-reveal', '');
                }
            });
        });

        staggerSelectors.forEach(function(selector) {
            document.querySelectorAll(selector).forEach(function(el) {
                if (canReveal(el) && !el.hasAttribute('data-reveal') && !el.hasAttribute('data-reveal-stagger')) {
                    el.setAttribute('data-reveal-stagger', '');
                }
            });
        });
    }

    function revealImmediately() {
        document.querySelectorAll('[data-reveal], [data-reveal-stagger], .reveal-up').forEach(function(el) {
            el.classList.add('revealed');
        });
    }

    function initReveal() {
        markRevealTargets();

        if (prefersReducedMotion || !('IntersectionObserver' in window)) {
            revealImmediately();
            return;
        }

        const observer = new IntersectionObserver(function(entries) {
            entries.forEach(function(entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('revealed');
                    observer.unobserve(entry.target);
                }
            });
        }, {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        });

        document.querySelectorAll('[data-reveal], .reveal-up').forEach(function(el) {
            const delay = el.getAttribute('data-reveal-delay');
            if (delay) {
                el.style.setProperty('--reveal-delay', delay + 'ms');
            }
            observer.observe(el);
        });

        document.querySelectorAll('[data-reveal-stagger]').forEach(function(el) {
            observer.observe(el);
        });
    }

    function init() {
        initScrollProgress();
        initReveal();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
