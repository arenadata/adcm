import type React from 'react';
import { useDispatch, useStore } from '@hooks';
import MaintenanceModeDialog from '@commonComponents/MaintenanceModeDialog/MaintenanceModeDialog';
import { getRevertedMaintenanceModeStatus } from '@commonComponents/MaintenanceModeDialog/MaintenanceModeDialog.utils';
import { useParams } from 'react-router-dom';
import {
  closeMaintenanceModeDialog,
  toggleMaintenanceMode,
} from '@store/adcm/cluster/services/serviceComponents/serviceComponentsActionsSlice';

const ServiceComponentsMaintenanceModeDialog: React.FC = () => {
  const dispatch = useDispatch();

  const { clusterId: clusterIdFromUrl, serviceId: serviceIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);
  const serviceId = Number(serviceIdFromUrl);

  const serviceComponent = useStore(({ adcm }) => {
    return (
      adcm.serviceComponents.serviceComponents.find(
        ({ id }) => id === adcm.serviceComponentsActions.maintenanceModeDialog.id,
      ) ?? null
    );
  });

  const componentId = serviceComponent?.id;

  const onCloseDialog = () => {
    dispatch(closeMaintenanceModeDialog());
  };

  const onConfirmDialog = () => {
    if (componentId) {
      const newMaintenanceMode = getRevertedMaintenanceModeStatus(serviceComponent);
      dispatch(toggleMaintenanceMode({ clusterId, serviceId, componentId, maintenanceMode: newMaintenanceMode }));
    }
  };

  return (
    serviceComponent && (
      <MaintenanceModeDialog
        entity={serviceComponent}
        onCloseDialog={onCloseDialog}
        onConfirmDialog={onConfirmDialog}
      />
    )
  );
};

export default ServiceComponentsMaintenanceModeDialog;
