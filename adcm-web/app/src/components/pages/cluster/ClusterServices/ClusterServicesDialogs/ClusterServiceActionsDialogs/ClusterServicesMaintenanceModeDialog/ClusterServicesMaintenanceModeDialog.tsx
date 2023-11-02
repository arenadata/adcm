import React from 'react';
import { useDispatch, useStore } from '@hooks';
import { getRevertedMaintenanceModeStatus } from '@commonComponents/MaintenanceModeDialog/MaintenanceModeDialog.utils';
import MaintenanceModeDialog from '@commonComponents/MaintenanceModeDialog/MaintenanceModeDialog';
import { toggleMaintenanceMode, closeMaintenanceModeDialog } from '@store/adcm/cluster/services/servicesActionsSlice';

const ClusterServicesMaintenanceModeDialog: React.FC = () => {
  const dispatch = useDispatch();

  const clusterService = useStore(({ adcm }) => {
    return (
      adcm.services.services.find(({ id }) => id === adcm.servicesActions.maintenanceModeDialog.service?.id) ?? null
    );
  });

  const clusterId = clusterService?.cluster.id;
  const clusterServiceId = clusterService?.id;

  const onCloseDialog = () => {
    dispatch(closeMaintenanceModeDialog());
  };

  const onConfirmDialog = () => {
    if (clusterServiceId && clusterId) {
      const newMaintenanceMode = getRevertedMaintenanceModeStatus(clusterService);
      dispatch(
        toggleMaintenanceMode({
          clusterId,
          serviceId: clusterServiceId,
          maintenanceMode: newMaintenanceMode,
        }),
      );
    }
  };

  return (
    clusterService && (
      <MaintenanceModeDialog entity={clusterService} onCloseDialog={onCloseDialog} onConfirmDialog={onConfirmDialog} />
    )
  );
};

export default ClusterServicesMaintenanceModeDialog;
