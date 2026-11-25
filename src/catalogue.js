(() => {
  'use strict';
  const root = document.documentElement;
  const toggle = document.querySelector('[data-theme-toggle]');
  try { const saved = localStorage.getItem('titancsa-theme'); if (saved === 'light' || saved === 'dark') root.dataset.theme = saved; } catch (_) {}
  const dark = () => root.dataset.theme === 'dark' || (!root.dataset.theme && matchMedia('(prefers-color-scheme: dark)').matches);
  const updateThemeLabel = () => {
    if (toggle) toggle.textContent = root.lang === 'fr' ? (dark() ? 'Clair' : 'Sombre') : (dark() ? 'Light' : 'Dark');
  };
  if (toggle) toggle.addEventListener('click', () => { const value = dark() ? 'light' : 'dark'; root.dataset.theme = value; try { localStorage.setItem('titancsa-theme', value); } catch (_) {} updateThemeLabel(); });
  updateThemeLabel();
  const search = document.querySelector('#project-search');
  if (!search) return;
  const category = document.querySelector('#category-filter');
  const noDriver = document.querySelector('#no-driver-filter');
  const reset = document.querySelector('[data-reset]');
  const projects = [...document.querySelectorAll('[data-project]')];
  const groups = [...document.querySelectorAll('[data-project-group]')];
  const counter = document.querySelector('#result-count');
  const empty = document.querySelector('#empty-results');
  const french = root.lang === 'fr';
  const countLabel = count => french ? `${count} ${count === 1 ? 'projet' : 'projets'}` : `${count} ${count === 1 ? 'entry' : 'entries'}`;
  const normalize = value => value.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  function filter() {
    const words = normalize(search.value.trim()).split(/\s+/).filter(Boolean);
    let count = 0;
    for (const entry of projects) {
      const text = normalize(entry.dataset.search);
      const match = words.every(word => text.includes(word)) && (!category.value || entry.dataset.category === category.value) && (!noDriver.checked || entry.dataset.noDriver === 'true');
      entry.hidden = !match; if (match) count++;
    }
    for (const group of groups) {
      const visible = [...group.querySelectorAll('[data-project]')].filter(entry => !entry.hidden).length;
      group.hidden = visible === 0;
      group.querySelector('[data-group-count]').textContent = countLabel(visible);
    }
    const suffix = french ? (count === 1 ? 'affiché' : 'affichés') : 'shown';
    counter.textContent = `${countLabel(count)} ${suffix}`;
    empty.hidden = count !== 0;
  }
  search.addEventListener('input', filter); category.addEventListener('change', filter); noDriver.addEventListener('change', filter);
  reset.addEventListener('click', () => { search.value = ''; category.value = ''; noDriver.checked = false; filter(); search.focus(); });
  document.querySelectorAll('[data-category-jump]').forEach(link => link.addEventListener('click', () => { category.value = ''; search.value = ''; noDriver.checked = false; filter(); }));
  filter();
})();
