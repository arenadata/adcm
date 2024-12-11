import type React from 'react';

import s from './MainHeader.module.scss';
import CurrentDate from '../CurrentDate/CurrentDate';
import ThemeSwitcher from '../ThemeSwitcher/ThemeSwitcher';

const MainHeader: React.FC<React.PropsWithChildren> = ({ children }) => {
  return (
    <header className={s.mainHeader} data-test="header-container">
      <CurrentDate data-test="header-date" />
      <div data-test="header-additional">{children}</div>
      <ThemeSwitcher data-test="header-theme" />
    </header>
  );
};

export default MainHeader;
