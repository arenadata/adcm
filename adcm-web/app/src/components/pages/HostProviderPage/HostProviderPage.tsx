import type React from 'react';
import { Outlet } from 'react-router-dom';
import s from './HostProviderPage.module.scss';
import HostProviderNavigation from './HostProviderNavigation/HostProviderNavigation';
import HostProviderHeader from './HostProviderHeader/HostProviderHeader';
import { useRequestHostProviderPage } from './useRequestHostProviderPage';
import HostProviderDialogs from './HostProviderDialogs/HostProviderDialogs';
import PermissionsChecker from '@commonComponents/PermissionsChecker/PermissionsChecker';
import EntityContractVersionWarning from '@commonComponents/EntityContractVersionWarning/EntityContractVersionWarning';

const HostProviderPage: React.FC = () => {
  const { accessCheckStatus, hostProvider } = useRequestHostProviderPage();

  return (
    <div className={s.hostProviderPage}>
      <PermissionsChecker requestState={accessCheckStatus}>
        <HostProviderHeader />
        <EntityContractVersionWarning
          entity={hostProvider}
          entityType="hostprovider"
          className={s.hostProviderPage__warning}
        />
        <HostProviderNavigation />
        <Outlet />
        <HostProviderDialogs />
      </PermissionsChecker>
    </div>
  );
};

export default HostProviderPage;
