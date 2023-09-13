import React from 'react';
import UnlinkClusterHostsDialog from '@pages/cluster/ClusterHosts/ClusterHostsActionsDialogs/UnlinkClusterHostsDialog/UnlinkClusterHostsDialog';
import AddClusterHostsDialog from '@pages/cluster/ClusterHosts/ClusterHostsActionsDialogs/AddClusterHostsDialog/AddClusterHostsDialog';
import ClusterHostsMaintenanceModeDialog from './ClusterHostsMaintenanceModeDialog/ClusterHostsMaintenanceModeDialog';

const ClusterHostsActionsDialogs: React.FC = () => {
  return (
    <>
      <AddClusterHostsDialog />
      <UnlinkClusterHostsDialog />
      <ClusterHostsMaintenanceModeDialog />
    </>
  );
};

export default ClusterHostsActionsDialogs;
