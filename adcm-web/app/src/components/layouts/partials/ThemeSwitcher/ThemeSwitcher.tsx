import React, { useEffect } from 'react';
import s from './ThemeSwitcher.module.scss';
import { useLocalStorage } from '@uikit/hooks/useLocalStorage';
import Icon from '@uikit/Icon/Icon';
import cn from 'classnames';

enum THEME {
  Dark = 'dark',
  Light = 'light',
}

const THEMES_CLASS = {
  [THEME.Dark]: 'theme-dark',
  [THEME.Light]: 'theme-light',
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
    saveThemeToStorage(THEME.Dark);
    switchToTheme(THEME.Dark);
  };
  const lightOn = () => {
    saveThemeToStorage(THEME.Light);
    switchToTheme(THEME.Light);
  };

  // save theme to storage for first connect to page
  useEffect(() => {
    if (theme === THEME.Light) {
      lightOn();
    } else {
      darkOn();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className={s.themeSwitcher}>
      <button
        className={cn(s.themeSwitcher__btn, { 'is-active': theme === THEME.Light })}
        onClick={lightOn}
        title={theme === THEME.Dark ? 'Switch to light theme' : undefined}
        data-test="light-theme"
      >
        <Icon name="g2-sun" size={24} />
      </button>
      <button
        className={cn(s.themeSwitcher__btn, { 'is-active': theme === THEME.Dark })}
        onClick={darkOn}
        title={theme === THEME.Light ? 'Switch to dark theme' : undefined}
        data-test="dark-theme"
      >
        <Icon name="g2-moon" size={24} />
      </button>
    </div>
  );
};

export default ThemeSwitcher;
