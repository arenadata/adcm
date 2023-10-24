import React from 'react';
import { Outlet } from 'react-router-dom';
import ClusterHostHeader from './ClusterHostHeader/ClusterHostHeader';
import ClusterHostNavigation from './ClusterHostNavigation/ClusterHostNavigation';
import { useRequestClusterHost } from './useRequestHost';
import ClusterHostsDynamicActionDialog from '@pages/cluster/ClusterHosts/ClusterHostsActionsDialogs/ClusterHostsDynamicActionDialog/ClusterHostsDynamicActionDialog';

const ClusterHostLayout: React.FC = () => {
  useRequestClusterHost();

  return (
    <div>
      <ClusterHostHeader />
      <ClusterHostNavigation />
      <Outlet />
      <ClusterHostsDynamicActionDialog />
    </div>
  );
};

export default ClusterHostLayout;
