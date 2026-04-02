/* =========================================
   ACLAS – Effects JS
   Loader | Cursor Glow | Parallax | Theme
   ========================================= */

(function () {
  'use strict';

  /* ---- Theme Toggle ---- */
  const THEME_KEY = 'aclas-theme';
  const html      = document.documentElement;
  const toggleBtn = document.getElementById('themeToggle');

  function applyTheme(theme) {
    if (theme === 'light') {
      html.setAttribute('data-theme', 'light');
      if (toggleBtn) toggleBtn.textContent = '☀️';
    } else {
      html.removeAttribute('data-theme');
      if (toggleBtn) toggleBtn.textContent = '🌙';
    }
  }

  // Load saved preference, or detect OS preference
  const saved = localStorage.getItem(THEME_KEY);
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  applyTheme(saved || (prefersDark ? 'dark' : 'light'));

  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      const current = html.getAttribute('data-theme');
      const next    = current === 'light' ? 'dark' : 'light';
      localStorage.setItem(THEME_KEY, next);
      applyTheme(next);
    });
  }

  /* ---- Page Loader ---- */
  const loader = document.getElementById('aclas-loader');
  if (loader) {
    window.addEventListener('load', () => {
      setTimeout(() => loader.classList.add('hidden'), 400);
    });
  }

  /* ---- Cursor Glow ---- */
  const cursorGlow = document.getElementById('cursor-glow');
  if (cursorGlow) {
    document.addEventListener('mousemove', (e) => {
      cursorGlow.style.left = e.clientX + 'px';
      cursorGlow.style.top  = e.clientY + 'px';
    });
  }

  /* ---- Parallax Orbs (Dashboard only) ---- */
  const p1 = document.querySelector('.p-orb-1');
  const p2 = document.querySelector('.p-orb-2');
  if (p1 && p2) {
    document.addEventListener('mousemove', (e) => {
      const cx = window.innerWidth / 2;
      const cy = window.innerHeight / 2;
      const dx = (e.clientX - cx) / cx;
      const dy = (e.clientY - cy) / cy;
      p1.style.transform = `translate(${dx * 18}px, ${dy * 18}px)`;
      p2.style.transform = `translate(${-dx * 24}px, ${-dy * 24}px)`;
    });
  }

  /* ---- Copy Token ---- */
  document.querySelectorAll('[data-copy]').forEach(btn => {
    btn.addEventListener('click', () => {
      const text = btn.dataset.copy;
      navigator.clipboard.writeText(text).then(() => {
        const orig = btn.textContent;
        btn.textContent = 'Copied!';
        btn.style.color = 'var(--green)';
        btn.style.borderColor = 'var(--green)';
        setTimeout(() => {
          btn.textContent = orig;
          btn.style.color = '';
          btn.style.borderColor = '';
        }, 2000);
      });
    });
  });

  /* ---- Filter Table ---- */
  const filterInput = document.getElementById('statsSearch');
  if (filterInput) {
    filterInput.addEventListener('input', () => {
      const q = filterInput.value.toLowerCase();
      document.querySelectorAll('#statsTable tbody tr').forEach(row => {
        row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
      });
    });
  }
  const langFilter = document.getElementById('langFilter');
  if (langFilter) {
    langFilter.addEventListener('change', () => {
      const val = langFilter.value.toLowerCase();
      document.querySelectorAll('#statsTable tbody tr').forEach(row => {
        if (!val) { row.style.display = ''; return; }
        const badge = row.querySelector('.badge');
        row.style.display = badge && badge.textContent.toLowerCase().includes(val) ? '' : 'none';
      });
    });
  }

  /* ---- Dynamic Greeting ---- */
  const greetEl = document.getElementById('greeting-word');
  if (greetEl) {
    const h = new Date().getHours();
    greetEl.textContent = h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
  }

  /* ---- Active nav link ---- */
  const currentPath = window.location.pathname;
  document.querySelectorAll('.nav-link').forEach(link => {
    if (link.getAttribute('href') === currentPath) link.classList.add('active');
  });

})();

