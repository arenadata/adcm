import React from 'react';
import { Outlet } from 'react-router-dom';
import ClusterServiceHeader from './ClusterServiceHeader/ClusterServiceHeader';
import { useRequestService } from './useRequestService';
import ClusterServiceNavigation from '@layouts/ClusterServiceLayout/ClusterServiceNavigation/ClusterServiceNavigation';
import ClusterServiceDynamicActionDialog from '@pages/cluster/ClusterServices/ClusterServicesDialogs/ClusterServiceDynamicActionDialog/ClusterServiceDynamicActionDialog';

const ClusterServiceLayout: React.FC = () => {
  useRequestService();

  return (
    <div>
      <ClusterServiceHeader />
      <ClusterServiceNavigation />
      <Outlet />
      <ClusterServiceDynamicActionDialog />
    </div>
  );
};

export default ClusterServiceLayout;
