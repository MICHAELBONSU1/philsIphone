// Debug helpers for mobile navbar menu visibility issues (iOS Safari portrait)
(function () {
  function logNavState(prefix) {
    const hamburger = document.querySelector('.hamburger');
    const navMenu = document.querySelector('.nav-menu');
    if (!navMenu) return;

    const cs = window.getComputedStyle(navMenu);
    const rect = navMenu.getBoundingClientRect();

    console.log('[nav-debug]', prefix, {
      openClass: navMenu.classList.contains('open'),
      opacity: cs.opacity,
      visibility: cs.visibility,
      pointerEvents: cs.pointerEvents,
      transform: cs.transform,
      zIndex: cs.zIndex,
      display: cs.display,
      rect: { x: rect.x, y: rect.y, w: rect.width, h: rect.height }
    });

    // Visual outline when open toggles
    navMenu.style.outline = navMenu.classList.contains('open') ? '3px solid rgba(255,0,0,0.9)' : 'none';
  }

  function ensureDebugStyles() {
    const styleId = 'nav-debug-style';
    if (document.getElementById(styleId)) return;
    const el = document.createElement('style');
    el.id = styleId;
    el.textContent = `
      .nav-menu.nav-debug-outline { outline: 3px solid rgba(255,0,0,0.9); }
    `;
    document.head.appendChild(el);
  }

  document.addEventListener('DOMContentLoaded', function () {
    ensureDebugStyles();

    const hamburger = document.querySelector('.hamburger');
    const navMenu = document.querySelector('.nav-menu');

    if (!hamburger || !navMenu) return;

    logNavState('initial');

    hamburger.addEventListener('click', function () {
      // Wait a tick so classList changes by your real handler are applied
      setTimeout(() => logNavState('after hamburger click'), 0);
    });

    window.addEventListener('resize', function () {
      logNavState('after resize');
    });

    // Periodic sampling helps catch cases where it becomes hidden without a click
    setInterval(() => logNavState('periodic'), 8000);
  });
})();

