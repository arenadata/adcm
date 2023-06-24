import React from 'react';
import MainLogo from '../partials/MainLogo/MainLogo';
import MainHeader from '../partials/MainHeader/MainHeader';
import Copyright from '../partials/Copyright/Copyright';

import s from './NonAuthLayout.module.scss';

const NonAuthLayout: React.FC<React.PropsWithChildren> = ({ children }) => {
  return (
    <div className={s.nonAuthLayout}>
      <MainHeader />
      <MainLogo />
      {children}
      <Copyright />
    </div>
  );
};

export default NonAuthLayout;
