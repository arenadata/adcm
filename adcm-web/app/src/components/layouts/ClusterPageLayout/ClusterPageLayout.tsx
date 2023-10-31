import React from 'react';
import { Outlet } from 'react-router-dom';
import ClusterHeader from '@layouts/ClusterPageLayout/ClusterHeader/ClusterHeader';
import { useRequestCluster } from '@layouts/ClusterPageLayout/useRequestCluster';
import ClusterDynamicActionDialog from '@pages/ClustersPage/Dialogs/ClusterDynamicActionDialog/ClusterDynamicActionDialog';

const ClusterPageLayout: React.FC = () => {
  useRequestCluster();

  return (
    <div>
      <ClusterHeader />
      <Outlet />
      <ClusterDynamicActionDialog />
    </div>
  );
};
export default ClusterPageLayout;
