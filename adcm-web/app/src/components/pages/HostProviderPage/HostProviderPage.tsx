import React from 'react';
import { Outlet } from 'react-router-dom';
import s from './HostProviderPage.module.scss';
import HostProviderNavigation from './HostProviderNavigation/HostProviderNavigation';
import HostProviderHeader from './HostProviderHeader/HostProviderHeader';
import { useRequestHostProviderPage } from './useRequestHostProviderPage';
import HostProviderDialogs from './HostProviderDialogs/HostProviderDialogs';
import PermissionsChecker from '@commonComponents/PermissionsChecker/PermissionsChecker';

const HostProviderPage: React.FC = () => {
  const { accessCheckStatus } = useRequestHostProviderPage();

  return (
    <div className={s.hostProviderPage}>
      <PermissionsChecker requestState={accessCheckStatus}>
        <HostProviderHeader />
        <HostProviderNavigation />
        <Outlet />
        <HostProviderDialogs />
      </PermissionsChecker>
    </div>
  );
};

export default HostProviderPage;
