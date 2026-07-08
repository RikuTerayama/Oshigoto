(function() {
  if (window.JobcanAffiliate) {
    return;
  }

  var RAKUTEN_COMMON = {
    affiliateId: '0ea62065.34400275.0ea62066.204f04c0',
    items: 'ranking',
    genreId: '0',
    recommend: 'on',
    design: 'slide',
    target: '_blank',
    border: 'on',
    autoMode: 'on',
    adNetworkId: 'a8Net',
    adNetworkUrl: 'https%3A%2F%2Frpx.a8.net%2Fsvt%2Fejp%3Fa8mat%3D4AX5KD%2B97MHI2%2B2HOM%2BBS629%26rakuten%3Dy%26a8ejpredirect%3D',
    pointbackId: 'a26020776127_4AX5KD_97MHI2_2HOM_BS629'
  };

  var RAKUTEN_BY_SIZE = {
    '300x250': {
      mediaId: '20011813',
      pixelSrc: 'https://www15.a8.net/0.gif?a8mat=4AX5KD+97MHI2+2HOM+BS629'
    },
    '728x90': {
      mediaId: '20011816',
      pixelSrc: 'https://www17.a8.net/0.gif?a8mat=4AX5KD+97MHI2+2HOM+BS629'
    }
  };

  var ROTATION_SRC = '//rot3.a8.net/jsa/fdf80b714de10cbdd802fd2333444e15/c6f057b86584942e415435ffb1fa93d4.js';
  var slots = [];
  var observer = null;

  function getDeviceClass() {
    var width = window.innerWidth || document.documentElement.clientWidth || 0;
    if (width >= 1200) {
      return 'desktop';
    }
    if (width >= 768) {
      return 'tablet';
    }
    return 'mobile';
  }

  function isDeviceEnabled(slot) {
    var device = getDeviceClass();
    if (device === 'desktop') {
      return slot.dataset.affiliateDesktopEnabled === 'true';
    }
    if (device === 'tablet') {
      return slot.dataset.affiliateTabletEnabled === 'true';
    }
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

  function renderRakuten(slot, mount) {
    var size = slot.dataset.affiliateSize;
    var sizeConfig = RAKUTEN_BY_SIZE[size];
    if (!sizeConfig) {
      return;
    }

    window.rakuten_affiliateId = RAKUTEN_COMMON.affiliateId;
    window.rakuten_items = RAKUTEN_COMMON.items;
    window.rakuten_genreId = RAKUTEN_COMMON.genreId;
    window.rakuten_recommend = RAKUTEN_COMMON.recommend;
    window.rakuten_design = RAKUTEN_COMMON.design;
    window.rakuten_size = size;
    window.rakuten_target = RAKUTEN_COMMON.target;
    window.rakuten_border = RAKUTEN_COMMON.border;
    window.rakuten_auto_mode = RAKUTEN_COMMON.autoMode;
    window.rakuten_adNetworkId = RAKUTEN_COMMON.adNetworkId;
    window.rakuten_adNetworkUrl = RAKUTEN_COMMON.adNetworkUrl;
    window.rakuten_pointbackId = RAKUTEN_COMMON.pointbackId;
    window.rakuten_mediaId = sizeConfig.mediaId;

    var configScript = document.createElement('script');
    configScript.type = 'text/javascript';
    configScript.text = '';
    mount.appendChild(configScript);

    var widgetScript = document.createElement('script');
    widgetScript.type = 'text/javascript';
    widgetScript.src = '//xml.affiliate.rakuten.co.jp/widget/js/rakuten_widget.js';
    mount.appendChild(widgetScript);

    var pixel = document.createElement('img');
    pixel.border = 0;
    pixel.width = 1;
    pixel.height = 1;
    pixel.src = sizeConfig.pixelSrc;
    pixel.alt = '';
    mount.appendChild(pixel);
  }

  function renderRotation(mount) {
    var script = document.createElement('script');
    script.type = 'text/javascript';
    script.src = ROTATION_SRC;
    mount.appendChild(script);
  }

  function widgetLooksLoaded(mount) {
    if (!mount) {
      return false;
    }
    if (mount.querySelector('iframe, ins, object, embed')) {
      return true;
    }
    return Array.prototype.some.call(mount.childNodes, function(node) {
      if (node.nodeType === 3) {
        return (node.textContent || '').trim().length > 0;
      }
      if (node.nodeType !== 1) {
        return false;
      }
      if (node.tagName === 'SCRIPT') {
        return false;
      }
      if (node.tagName === 'IMG' && node.width === 1 && node.height === 1) {
        return false;
      }
      return true;
    });
  }

  function updateFallbackVisibility(slot, mount) {
    if (!slot || !mount) {
      return;
    }
    if (widgetLooksLoaded(mount)) {
      slot.dataset.affiliateWidgetLoaded = 'true';
      return;
    }
    delete slot.dataset.affiliateWidgetLoaded;
  }

  function scheduleWidgetChecks(slot, mount) {
    [500, 1400, 2800].forEach(function(delay) {
      window.setTimeout(function() {
        updateFallbackVisibility(slot, mount);
      }, delay);
    });
    if (!window.MutationObserver) {
      return;
    }
    var observer = new MutationObserver(function() {
      updateFallbackVisibility(slot, mount);
    });
    observer.observe(mount, { childList: true, subtree: true });
    window.setTimeout(function() {
      observer.disconnect();
    }, 4000);
  }

  function renderSlot(slot) {
    if (!isRenderable(slot)) {
      return;
    }

    var mount = slot.querySelector('[data-affiliate-mount]');
    if (!mount) {
      return;
    }

    slot.dataset.affiliateRendered = 'true';
    mount.innerHTML = '';
    delete slot.dataset.affiliateWidgetLoaded;

    if (slot.dataset.affiliateKind === 'a8_rotation') {
      renderRotation(mount);
    } else {
      renderRakuten(slot, mount);
    }

    scheduleWidgetChecks(slot, mount);
  }

  function watchSlot(slot) {
    if (!slot || !isRenderable(slot)) {
      return;
    }

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
    slots = Array.prototype.slice.call(document.querySelectorAll('[data-affiliate-slot]'));
    slots.forEach(function(slot) {
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
    if (!slot) {
      return;
    }
    slot.dataset.affiliateToolReady = 'true';
    slot.hidden = false;
    slot.removeAttribute('aria-hidden');
    if (slot.dataset.affiliateRendered === 'true') {
      return;
    }
    watchSlot(slot);
  }

  function resetToolSlot(slotId) {
    var slot = document.querySelector('[data-affiliate-slot="' + slotId + '"]');
    if (!slot) {
      return;
    }
    slot.dataset.affiliateToolReady = 'false';
    slot.hidden = true;
    slot.setAttribute('aria-hidden', 'true');
  }

  window.JobcanAffiliate = {
    init: init,
    markToolResultReady: markToolResultReady,
    resetToolSlot: resetToolSlot
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
