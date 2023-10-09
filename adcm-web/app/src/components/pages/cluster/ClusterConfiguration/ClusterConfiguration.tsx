import React from 'react';
import { Outlet } from 'react-router-dom';
import ClusterConfigurationsNavigation from './ClusterConfigurationsNavigation/ClusterConfigurationsNavigation';

const ClusterConfiguration: React.FC = () => {
  return (
    <div>
      <ClusterConfigurationsNavigation />
      <Outlet />
    </div>
  );
};

export default ClusterConfiguration;
