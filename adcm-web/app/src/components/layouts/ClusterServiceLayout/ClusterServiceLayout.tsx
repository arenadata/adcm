import React from 'react';
import { Outlet } from 'react-router-dom';
import ClusterServiceHeader from './ClusterServiceHeader/ClusterServiceHeader';
import { useRequestService } from './useRequestService';
import ClusterServiceNavigation from '@layouts/ClusterServiceLayout/ClusterServiceNavigation/ClusterServiceNavigation';
import ClusterServiceDynamicActionDialog from '@pages/cluster/ClusterServices/ClusterServicesDialogs/ClusterServiceDynamicActionDialog/ClusterServiceDynamicActionDialog';
import PermissionsChecker from '@commonComponents/PermissionsChecker/PermissionsChecker';

const ClusterServiceLayout: React.FC = () => {
  const { accessCheckStatus } = useRequestService();

  return (
    <div>
      <PermissionsChecker requestState={accessCheckStatus}>
        <ClusterServiceHeader />
        <ClusterServiceNavigation />
        <Outlet />
        <ClusterServiceDynamicActionDialog />
      </PermissionsChecker>
    </div>
  );
};

export default ClusterServiceLayout;
