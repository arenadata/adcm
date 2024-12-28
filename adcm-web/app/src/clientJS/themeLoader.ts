(() => {
  let theme: string;
  try {
    theme = JSON.parse(window.localStorage.getItem('css_theme_name') || '') || 'dark';
  } catch (_e) {
    theme = 'dark';
  }
  document.body.classList.add(`theme-${theme}`);
})();
