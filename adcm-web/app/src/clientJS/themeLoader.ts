(() => {
  let theme;
  try {
    theme = JSON.parse(window.localStorage.getItem('css_theme_name') || '') || 'dark';
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
  } catch (e) {
    theme = 'dark';
  }
  document.body.classList.add(`theme-${theme}`);
})();
