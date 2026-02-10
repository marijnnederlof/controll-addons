/**
 * Controll Branding Module
 * Replaces "Home Assistant" branding with "Controll" in the sidebar
 */

(function() {
  'use strict';

  const BRAND_NAME = 'Controll';
  const CHECK_INTERVAL = 500;
  const MAX_ATTEMPTS = 60; // 30 seconds max

  let attempts = 0;

  function applyBranding() {
    attempts++;

    // Find the sidebar title element
    const sidebar = document.querySelector('ha-sidebar');
    if (!sidebar || !sidebar.shadowRoot) {
      if (attempts < MAX_ATTEMPTS) {
        setTimeout(applyBranding, CHECK_INTERVAL);
      }
      return;
    }

    // Look for the title in the sidebar shadow DOM
    const titleElement = sidebar.shadowRoot.querySelector('.title');
    if (titleElement && titleElement.textContent.includes('Home Assistant')) {
      titleElement.textContent = BRAND_NAME;
      console.log('[Controll] Branding applied');
    }

    // Also update the document title
    if (document.title.includes('Home Assistant')) {
      document.title = document.title.replace('Home Assistant', BRAND_NAME);
    }

    // Apply custom styles
    applyStyles(sidebar.shadowRoot);

    // Watch for changes (SPA navigation)
    observeChanges(sidebar);
  }

  function applyStyles(shadowRoot) {
    const existingStyle = shadowRoot.querySelector('#controll-branding-style');
    if (existingStyle) return;

    const style = document.createElement('style');
    style.id = 'controll-branding-style';
    style.textContent = `
      /* Controll branding styles */
      .title {
        font-weight: 600 !important;
        letter-spacing: -0.02em !important;
        color: #f97316 !important;
      }

      /* Hide HA logo if present */
      .menu .logo {
        display: none !important;
      }
    `;
    shadowRoot.appendChild(style);
  }

  function observeChanges(sidebar) {
    // Watch for title changes
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.type === 'childList' || mutation.type === 'characterData') {
          const titleElement = sidebar.shadowRoot.querySelector('.title');
          if (titleElement && titleElement.textContent.includes('Home Assistant')) {
            titleElement.textContent = BRAND_NAME;
          }
        }
      });
    });

    const titleElement = sidebar.shadowRoot.querySelector('.title');
    if (titleElement) {
      observer.observe(titleElement, {
        childList: true,
        characterData: true,
        subtree: true
      });
    }

    // Also watch document title
    const titleObserver = new MutationObserver(() => {
      if (document.title.includes('Home Assistant')) {
        document.title = document.title.replace('Home Assistant', BRAND_NAME);
      }
    });

    const titleTag = document.querySelector('title');
    if (titleTag) {
      titleObserver.observe(titleTag, { childList: true });
    }
  }

  // Start when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', applyBranding);
  } else {
    applyBranding();
  }

  // Also try after a short delay for SPA behavior
  setTimeout(applyBranding, 1000);
  setTimeout(applyBranding, 3000);

})();
