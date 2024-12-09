import type React from 'react';
import AddClusterServiceDialog from '@pages/cluster/ClusterServices/ClusterServicesDialogs/ClusterServiceActionsDialogs/AddClusterServiceDialog/AddClusterServiceDialog';
import DeleteClusterServiceDialog from './DeleteClusterServiceDialog/DeleteClusterServiceDialog';
import ClusterServiceDynamicActionDialog from '@pages/cluster/ClusterServices/ClusterServicesDialogs/ClusterServiceDynamicActionDialog/ClusterServiceDynamicActionDialog';
import ClusterServicesMaintenanceModeDialog from '@pages/cluster/ClusterServices/ClusterServicesDialogs/ClusterServiceActionsDialogs/ClusterServicesMaintenanceModeDialog/ClusterServicesMaintenanceModeDialog';

const ClusterServiceActionsDialogs: React.FC = () => {
  return (
    <>
      <AddClusterServiceDialog />
      <DeleteClusterServiceDialog />
      <ClusterServicesMaintenanceModeDialog />
      <ClusterServiceDynamicActionDialog />
    </>
  );
};

export default ClusterServiceActionsDialogs;
