import React from 'react';
import AddClusterServiceDialog from '@pages/cluster/ClusterServices/ClusterServiceActionsDialogs/AddClusterServiceDialog/AddClusterServiceDialog';
import DeleteClusterServiceDialog from './DeleteClusterServiceDialog/DeleteClusterServiceDialog';

const ClusterServiceActionsDialogs: React.FC = () => {
  return (
    <>
      <AddClusterServiceDialog />
      <DeleteClusterServiceDialog />
    </>
  );
};

export default ClusterServiceActionsDialogs;
