import React from 'react';
import LeftSideBar from '@layouts/partials/LeftSideBar/LeftSideBar';

import s from './MainLayout.module.scss';
import PageHeader from '@layouts/partials/PageHeader/PageHeader';
import MainHeader from '@layouts/partials/MainHeader/MainHeader';
import HeaderAdvancedInfo from '@layouts/partials/HeaderAdvancedInfo/HeaderAdvancedInfo';

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
        <PageHeader />
        {children}
      </div>
    </div>
  );
};

export default MainLayout;
