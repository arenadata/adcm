import React from 'react';
import { useDispatch, useStore } from '@hooks';
import MaintenanceModeDialog from '@commonComponents/MaintenanceModeDialog/MaintenanceModeDialog';
import { getRevertedMaintenanceModeStatus } from '@commonComponents/MaintenanceModeDialog/MaintenanceModeDialog.utils';
import {
  closeMaintenanceModeDialog,
  toggleMaintenanceModeWithUpdate,
} from '@store/adcm/cluster/hosts/hostsActionsSlice';

const ClusterHostsMaintenanceModeDialog: React.FC = () => {
  const dispatch = useDispatch();

  const clusterHost = useStore(({ adcm }) => {
    return (
      adcm.clusterHosts.hosts.find(({ id }) => id === adcm.clusterHostsActions.maintenanceModeDialog.host?.id) ?? null
    );
  });

  const clusterId = clusterHost?.cluster.id;

  const clusterHostId = clusterHost?.id;

  const onCloseDialog = () => {
    dispatch(closeMaintenanceModeDialog());
  };

  const onConfirmDialog = () => {
    if (clusterHostId && clusterId) {
      const newMaintenanceMode = getRevertedMaintenanceModeStatus(clusterHost);
      dispatch(
        toggleMaintenanceModeWithUpdate({ clusterId, hostId: clusterHostId, maintenanceMode: newMaintenanceMode }),
      );
    }
  };

  return (
    clusterHost && (
      <MaintenanceModeDialog entity={clusterHost} onCloseDialog={onCloseDialog} onConfirmDialog={onConfirmDialog} />
    )
  );
};

export default ClusterHostsMaintenanceModeDialog;
