import React from 'react';
import { useDispatch, useStore } from '@hooks';

import { Dialog } from '@uikit';
import { useParams } from 'react-router-dom';
import {
  closeMaintenanceModeDialog,
  toggleMaintenanceModeWithUpdate,
} from '@store/adcm/cluster/services/serviceComponents/serviceComponent/serviceComponentActionsSlice';
import { AdcmMaintenanceMode } from '@models/adcm';

const MaintenanceModeDialog: React.FC = () => {
  const dispatch = useDispatch();
  const { clusterId: clusterIdFromUrl, serviceId: serviceIdFromUrl, componentId: componentIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);
  const serviceId = Number(serviceIdFromUrl);
  const componentId = Number(componentIdFromUrl);

  const component = useStore(({ adcm }) => adcm.serviceComponent.serviceComponent);
  const maintenanceModeDialogId = useStore(({ adcm }) => adcm.serviceComponentActions.maintenanceModeDialog.id);
  const componentName = component?.displayName;
  const statusLabel = component?.maintenanceMode === AdcmMaintenanceMode.Off ? 'Enable' : 'Disable';
  const maintenanceMode =
    component?.maintenanceMode === AdcmMaintenanceMode.Off ? AdcmMaintenanceMode.On : AdcmMaintenanceMode.Off;

  const isOpen = maintenanceModeDialogId !== null;

  const handleCloseConfirm = () => {
    dispatch(closeMaintenanceModeDialog());
  };

  const handleConfirmDialog = () => {
    if (maintenanceModeDialogId === null) return;

    dispatch(toggleMaintenanceModeWithUpdate({ clusterId, serviceId, componentId, maintenanceMode }));
  };

  return (
    <>
      <Dialog
        //
        isOpen={isOpen}
        onOpenChange={handleCloseConfirm}
        title={`${statusLabel} maintenance mode`}
        onAction={handleConfirmDialog}
        actionButtonLabel={statusLabel}
      >
        The maintenance mode will be turned {maintenanceMode} on {componentName}
      </Dialog>
    </>
  );
};

export default MaintenanceModeDialog;
