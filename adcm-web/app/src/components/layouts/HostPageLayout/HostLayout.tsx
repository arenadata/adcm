import type React from 'react';
import { Outlet } from 'react-router-dom';
import HostHeader from './HostHeader/HostHeader';
import HostNavigation from './HostNavigation/HostNavigation';
import { useRequestHost } from './useRequestHost';
import HostDynamicActionDialog from '@pages/HostsPage/HostsActionsDialogs/HostDynamicActionDialog/HostDynamicActionDialog';

const HostLayout: React.FC = () => {
  useRequestHost();

  return (
    <div>
      <HostHeader />
      <HostNavigation />
      <Outlet />
      <HostDynamicActionDialog />
    </div>
  );
};

export default HostLayout;
