import React from 'react';
import UnlinkClusterHostsDialog from '@pages/cluster/ClusterHosts/ClusterHostsActionsDialogs/UnlinkClusterHostsDialog/UnlinkClusterHostsDialog';
import AddClusterHostsDialog from '@pages/cluster/ClusterHosts/ClusterHostsActionsDialogs/AddClusterHostsDialog/AddClusterHostsDialog';
import MaintenanceModeDialog from '@pages/cluster/ClusterHosts/ClusterHostsActionsDialogs/MaintenanceModeDialog/MaintenanceModeDialog';

const ClusterHostsActionsDialogs: React.FC = () => {
  return (
    <>
      <AddClusterHostsDialog />
      <UnlinkClusterHostsDialog />
      <MaintenanceModeDialog />
    </>
  );
};

export default ClusterHostsActionsDialogs;
