import React from 'react';

import s from './MainHeader.module.scss';
import CurrentDate from '../CurrentDate/CurrentDate';
import ThemeSwitcher from '../ThemeSwitcher/ThemeSwitcher';

const MainHeader: React.FC<React.PropsWithChildren> = ({ children }) => {
  return (
    <header className={s.mainHeader}>
      <CurrentDate />
      {children}
      <ThemeSwitcher />
    </header>
  );
};

export default MainHeader;
