import React from 'react';
import AddClusterServiceDialog from '@pages/cluster/ClusterServices/ClusterServicesDialogs/ClusterServiceActionsDialogs/AddClusterServiceDialog/AddClusterServiceDialog';
import DeleteClusterServiceDialog from './DeleteClusterServiceDialog/DeleteClusterServiceDialog';
import ClusterServiceDynamicActionDialog from '@pages/cluster/ClusterServices/ClusterServicesDialogs/ClusterServiceDynamicActionDialog/ClusterServiceDynamicActionDialog';

const ClusterServiceActionsDialogs: React.FC = () => {
  return (
    <>
      <AddClusterServiceDialog />
      <DeleteClusterServiceDialog />
      <ClusterServiceDynamicActionDialog />
    </>
  );
};

export default ClusterServiceActionsDialogs;
