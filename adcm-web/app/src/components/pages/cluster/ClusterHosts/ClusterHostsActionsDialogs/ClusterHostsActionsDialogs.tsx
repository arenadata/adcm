import type React from 'react';
import UnlinkClusterHostsDialog from '@pages/cluster/ClusterHosts/ClusterHostsActionsDialogs/UnlinkClusterHostsDialog/UnlinkClusterHostsDialog';
import AddClusterHostsDialog from '@pages/cluster/ClusterHosts/ClusterHostsActionsDialogs/AddClusterHostsDialog/AddClusterHostsDialog';
import ClusterHostsMaintenanceModeDialog from './ClusterHostsMaintenanceModeDialog/ClusterHostsMaintenanceModeDialog';
import ClusterHostsDynamicActionDialog from './ClusterHostsDynamicActionDialog/ClusterHostsDynamicActionDialog';

const ClusterHostsActionsDialogs: React.FC = () => {
  return (
    <>
      <AddClusterHostsDialog />
      <UnlinkClusterHostsDialog />
      <ClusterHostsMaintenanceModeDialog />
      <ClusterHostsDynamicActionDialog />
    </>
  );
};

export default ClusterHostsActionsDialogs;
