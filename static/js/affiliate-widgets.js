(function() {
  if (window.OshigotoAffiliate) {
    return;
  }

  var ROTATION_SRC = '//rot3.a8.net/jsa/fdf80b714de10cbdd802fd2333444e15/c6f057b86584942e415435ffb1fa93d4.js';
  var observer = null;

  function getDeviceClass() {
    var width = window.innerWidth || document.documentElement.clientWidth || 0;
    if (width >= 1200) return 'desktop';
    if (width >= 768) return 'tablet';
    return 'mobile';
  }

  function isDeviceEnabled(slot) {
    var device = getDeviceClass();
    if (device === 'desktop') return slot.dataset.affiliateDesktopEnabled === 'true';
    if (device === 'tablet') return slot.dataset.affiliateTabletEnabled === 'true';
    return slot.dataset.affiliateMobileEnabled === 'true';
  }

  function isToolSlotReady(slot) {
    return slot.dataset.affiliateToolReady !== 'false';
  }

  function isWidgetDisabled(slot) {
    return slot.dataset.affiliateDisableWidget === 'true';
  }

  function isServerManaged(slot) {
    return slot.dataset.affiliateServerManaged === 'true';
  }

  function isRenderable(slot) {
    return !slot.dataset.affiliateRendered && !isServerManaged(slot) && !isWidgetDisabled(slot) && isDeviceEnabled(slot) && isToolSlotReady(slot);
  }

  function renderRotation(mount) {
    var script = document.createElement('script');
    script.type = 'text/javascript';
    script.src = ROTATION_SRC;
    mount.appendChild(script);
  }

  function widgetLooksLoaded(mount) {
    if (!mount) return false;
    if (mount.querySelector('iframe, ins, object, embed')) return true;
    return Array.prototype.some.call(mount.childNodes, function(node) {
      if (node.nodeType === 3) return (node.textContent || '').trim().length > 0;
      if (node.nodeType !== 1 || node.tagName === 'SCRIPT') return false;
      if (node.tagName === 'IMG' && node.width === 1 && node.height === 1) return false;
      return true;
    });
  }

  function updateFallbackVisibility(slot, mount) {
    if (!slot || !mount) return;
    if (widgetLooksLoaded(mount)) {
      slot.dataset.affiliateWidgetLoaded = 'true';
      return;
    }
    delete slot.dataset.affiliateWidgetLoaded;
  }

  function scheduleWidgetChecks(slot, mount) {
    [500, 1400, 2800].forEach(function(delay) {
      window.setTimeout(function() { updateFallbackVisibility(slot, mount); }, delay);
    });
    if (!window.MutationObserver) return;
    var localObserver = new MutationObserver(function() { updateFallbackVisibility(slot, mount); });
    localObserver.observe(mount, { childList: true, subtree: true });
    window.setTimeout(function() { localObserver.disconnect(); }, 4000);
  }

  function renderSlot(slot) {
    if (!isRenderable(slot) || slot.dataset.affiliateKind !== 'a8_rotation') return;
    var mount = slot.querySelector('[data-affiliate-mount]');
    if (!mount) return;
    slot.dataset.affiliateRendered = 'true';
    mount.innerHTML = '';
    delete slot.dataset.affiliateWidgetLoaded;
    renderRotation(mount);
    scheduleWidgetChecks(slot, mount);
  }

  function watchSlot(slot) {
    if (!slot || !isRenderable(slot)) return;
    if (!observer) {
      observer = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
          if (entry.isIntersecting) {
            renderSlot(entry.target);
            observer.unobserve(entry.target);
          }
        });
      }, { rootMargin: '200px 0px' });
    }
    observer.observe(slot);
  }

  function init() {
    Array.prototype.slice.call(document.querySelectorAll('[data-affiliate-slot]')).forEach(function(slot) {
      var mount = slot.querySelector('[data-affiliate-mount]');
      if (isServerManaged(slot) && mount) {
        scheduleWidgetChecks(slot, mount);
        return;
      }
      watchSlot(slot);
    });
  }

  function markToolResultReady(slotId) {
    var slot = document.querySelector('[data-affiliate-slot="' + slotId + '"]');
    if (!slot) return;
    slot.dataset.affiliateToolReady = 'true';
    slot.hidden = false;
    slot.removeAttribute('aria-hidden');
    if (slot.dataset.affiliateRendered !== 'true') watchSlot(slot);
  }

  function resetToolSlot(slotId) {
    var slot = document.querySelector('[data-affiliate-slot="' + slotId + '"]');
    if (!slot) return;
    slot.dataset.affiliateToolReady = 'false';
    slot.hidden = true;
    slot.setAttribute('aria-hidden', 'true');
  }

  window.OshigotoAffiliate = { init: init, markToolResultReady: markToolResultReady, resetToolSlot: resetToolSlot };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
