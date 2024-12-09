import type React from 'react';
import { useEffect } from 'react';
import s from './ThemeSwitcher.module.scss';
import { useLocalStorage } from '@hooks';
import Icon from '@uikit/Icon/Icon';
import cn from 'classnames';
import { ConditionalWrapper, Tooltip } from '@uikit';

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
      <ConditionalWrapper Component={Tooltip} isWrap={theme === THEME.Dark} label="Switch to light theme">
        <button
          className={cn(s.themeSwitcher__btn, { 'is-active': theme === THEME.Light })}
          onClick={lightOn}
          data-test="light-theme"
        >
          <Icon name="g2-sun" size={24} />
        </button>
      </ConditionalWrapper>
      <ConditionalWrapper Component={Tooltip} isWrap={theme === THEME.Light} label="Switch to dark theme">
        <button
          className={cn(s.themeSwitcher__btn, { 'is-active': theme === THEME.Dark })}
          onClick={darkOn}
          data-test="dark-theme"
        >
          <Icon name="g2-moon" size={24} />
        </button>
      </ConditionalWrapper>
    </div>
  );
};

export default ThemeSwitcher;
