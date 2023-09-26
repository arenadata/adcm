import React from 'react';
import { Outlet } from 'react-router-dom';
import s from './HostProviderPage.module.scss';
import HostProviderNavigation from './HostProviderNavigation/HostProviderNavigation';
import HostProviderHeader from './HostProviderHeader/HostProviderHeader';
import { useRequestHostProviderPage } from './useRequestHostProviderPage';
import HostProviderDialogs from './HostProviderDialogs/HostProviderDialogs';

const HostProviderPage: React.FC = () => {
  useRequestHostProviderPage();

  return (
    <div className={s.hostProviderPage}>
      <HostProviderHeader />
      <HostProviderNavigation />
      <Outlet />
      <HostProviderDialogs />
    </div>
  );
};

export default HostProviderPage;
