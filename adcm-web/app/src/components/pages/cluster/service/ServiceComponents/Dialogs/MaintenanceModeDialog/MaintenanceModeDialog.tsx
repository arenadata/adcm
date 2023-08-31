import React from 'react';
import { useDispatch, useStore } from '@hooks';
import {
  closeMaintenanceModeDialog,
  toggleMaintenanceModeWithUpdate,
} from '@store/adcm/cluster/services/serviceComponents/serviceComponentsActionsSlice';
import { Dialog } from '@uikit';
import { useParams } from 'react-router-dom';
import { AdcmMaintenanceMode } from '@models/adcm';

const MaintenanceModeDialog: React.FC = () => {
  const dispatch = useDispatch();
  const { clusterId: clusterIdFromUrl, serviceId: serviceIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);
  const serviceId = Number(serviceIdFromUrl);

  const componentId = useStore(({ adcm }) => adcm.serviceComponentsActions.maintenanceModeDialog.id);
  const components = useStore(({ adcm }) => adcm.serviceComponents.serviceComponents);
  const component = components.find(({ id }) => id === componentId);
  const componentName = component?.displayName;
  const statusLabel = component?.maintenanceMode === AdcmMaintenanceMode.Off ? 'Enable' : 'Disable';
  const maintenanceMode =
    component?.maintenanceMode === AdcmMaintenanceMode.Off ? AdcmMaintenanceMode.On : AdcmMaintenanceMode.Off;

  const isOpen = componentId !== null;

  const handleCloseConfirm = () => {
    dispatch(closeMaintenanceModeDialog());
  };

  const handleConfirmDialog = () => {
    if (componentId === null) return;

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
