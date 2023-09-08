import React from 'react';
import { Outlet } from 'react-router-dom';
import ClusterHostHeader from './ClusterHostHeader/ClusterHostHeader';
import ClusterHostNavigation from './ClusterHostNavigation/ClusterHostNavigation';
import { useRequestClusterHost } from './useRequestHost';

const ClusterHostLayout: React.FC = () => {
  useRequestClusterHost();

  return (
    <div>
      <ClusterHostHeader />
      <ClusterHostNavigation />
      <Outlet />
    </div>
  );
};

export default ClusterHostLayout;
