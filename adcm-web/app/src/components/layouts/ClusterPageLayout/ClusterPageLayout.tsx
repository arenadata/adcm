import React from 'react';
import { Outlet } from 'react-router-dom';
import ClusterHeader from '@layouts/ClusterPageLayout/ClusterHeader/ClusterHeader';
import { useRequestCluster } from '@layouts/ClusterPageLayout/useRequestCluster';

const ClusterPageLayout: React.FC = () => {
  useRequestCluster();
  return (
    <div>
      <ClusterHeader />
      <Outlet />
    </div>
  );
};
export default ClusterPageLayout;
