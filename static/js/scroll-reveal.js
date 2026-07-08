/**
 * Scroll Reveal Animation
 * Minimal, professional scroll animations using IntersectionObserver
 * Respects prefers-reduced-motion for accessibility
 * Safe: Default visible, hidden only when JS is enabled
 */

(function() {
    'use strict';

    // Mark HTML as JS-enabled (for CSS to know JS is available)
    document.documentElement.classList.add('js');

    // Check for prefers-reduced-motion
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        // If user prefers reduced motion, reveal all elements immediately
        document.addEventListener('DOMContentLoaded', function() {
            const elements = document.querySelectorAll('[data-reveal], [data-reveal-stagger]');
            elements.forEach(function(el) {
                el.classList.add('revealed');
            });
        });
        return;
    }

    // IntersectionObserver options
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    // Create IntersectionObserver
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
            if (entry.isIntersecting) {
                entry.target.classList.add('revealed');
                // Unobserve after revealing to improve performance
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // Initialize on DOMContentLoaded
    function init() {
        // Find all elements with data-reveal or data-reveal-stagger attributes
        const revealElements = document.querySelectorAll('[data-reveal]');
        const staggerElements = document.querySelectorAll('[data-reveal-stagger]');

        // Observe single reveal elements
        revealElements.forEach(function(el) {
            // Apply custom delay if specified
            const delay = el.getAttribute('data-reveal-delay');
            if (delay) {
                el.style.setProperty('--reveal-delay', delay + 'ms');
            }
            observer.observe(el);
        });

        // Observe stagger container elements
        staggerElements.forEach(function(el) {
            observer.observe(el);
        });
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        // DOM is already ready
        init();
    }
})();
