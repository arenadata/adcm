(() => {
  let theme;
  try {
    theme = JSON.parse(window.localStorage.getItem('css_theme_name') || '') || 'dark';
  } catch (e) {
    theme = 'dark';
  }
  document.body.classList.add(`theme-${theme}`);
})();
