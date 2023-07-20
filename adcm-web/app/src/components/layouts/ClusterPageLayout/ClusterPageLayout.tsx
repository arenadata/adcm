import React from 'react';
import { Outlet } from 'react-router-dom';
import ClusterHeader from '@layouts/ClusterPageLayout/ClusterHeader/ClusterHeader';

const ClusterPageLayout: React.FC = () => {
  return (
    <div>
      <ClusterHeader />
      <Outlet />
    </div>
  );
};
export default ClusterPageLayout;
