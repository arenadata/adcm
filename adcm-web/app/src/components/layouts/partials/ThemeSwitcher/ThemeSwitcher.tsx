import React, { useEffect } from 'react';
import s from './ThemeSwitcher.module.scss';
import { useLocalStorage } from '@uikit/hooks/useLocalStorage';
import Icon from '@uikit/Icon/Icon';
import cn from 'classnames';

enum THEME {
  DARK = 'dark',
  LIGHT = 'light',
}

const THEMES_CLASS = {
  [THEME.DARK]: 'theme-dark',
  [THEME.LIGHT]: 'theme-light',
};

const THEME_STORAGE_KEY = 'css_theme_name';

const switchToTheme = (theme: THEME) => {
  Object.entries(THEMES_CLASS).forEach(([themeName, className]) => {
    document.body.classList.toggle(className, themeName === theme);
  });
};

const ThemeSwitcher: React.FC = () => {
  const [theme, saveThemeToStorage] = useLocalStorage({ key: THEME_STORAGE_KEY });

  const darkOn = () => {
    saveThemeToStorage(THEME.DARK);
    switchToTheme(THEME.DARK);
  };
  const lightOn = () => {
    saveThemeToStorage(THEME.LIGHT);
    switchToTheme(THEME.LIGHT);
  };

  // save theme to storage for first connect to page
  useEffect(() => {
    if (theme === THEME.LIGHT) {
      lightOn();
    } else {
      darkOn();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className={s.themeSwitcher}>
      <button
        className={cn(s.themeSwitcher__btn, { 'is-active': theme === THEME.LIGHT })}
        onClick={lightOn}
        title={theme === THEME.DARK ? 'Switch to light theme' : undefined}
      >
        <Icon name="g2-sun" size={24} />
      </button>
      <button
        className={cn(s.themeSwitcher__btn, { 'is-active': theme === THEME.DARK })}
        onClick={darkOn}
        title={theme === THEME.LIGHT ? 'Switch to dark theme' : undefined}
      >
        <Icon name="g2-moon" size={24} />
      </button>
    </div>
  );
};

export default ThemeSwitcher;
