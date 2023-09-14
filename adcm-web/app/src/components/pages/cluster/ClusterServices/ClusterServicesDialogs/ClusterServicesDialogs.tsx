import React from 'react';
import ClusterServiceActionsDialogs from './ClusterServiceActionsDialogs/ClusterServiceActionsDialogs';
import ClusterServiceDynamicActionDialog from './ClusterServiceDynamicActionDialog/ClusterServiceDynamicActionDialog';

const ClusterServicesDialogs: React.FC = () => {
  return (
    <>
      <ClusterServiceActionsDialogs />
      <ClusterServiceDynamicActionDialog />
    </>
  );
};
export default ClusterServicesDialogs;
