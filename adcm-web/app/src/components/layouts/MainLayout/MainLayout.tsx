import React from 'react';
import MainHeader from '@layouts/partials/MainHeader/MainHeader';
import LeftSideBar from '@layouts/partials/LeftSideBar/LeftSideBar';
import HeaderAdvancedInfo from '@layouts/partials/HeaderAdvancedInfo/HeaderAdvancedInfo';

import s from './MainLayout.module.scss';

const MainLayout: React.FC<React.PropsWithChildren> = ({ children }) => {
  return (
    <div className={s.mainLayout}>
      <aside className={s.mainLayout__leftSidebarWrap}>
        <LeftSideBar className={s.mainLayout__leftSidebar} />
      </aside>
      <div className={s.mainLayout__mainContent}>
        <MainHeader>
          <HeaderAdvancedInfo />
        </MainHeader>
        {children}
      </div>
    </div>
  );
};

export default MainLayout;
