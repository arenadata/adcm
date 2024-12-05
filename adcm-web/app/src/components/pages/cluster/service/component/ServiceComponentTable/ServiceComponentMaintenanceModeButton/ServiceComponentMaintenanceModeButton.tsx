import type React from 'react';
import { useState } from 'react';
import { useDispatch, useStore } from '@hooks';
import MaintenanceModeDialog from '@commonComponents/MaintenanceModeDialog/MaintenanceModeDialog';
import { getRevertedMaintenanceModeStatus } from '@commonComponents/MaintenanceModeDialog/MaintenanceModeDialog.utils';
import { useParams } from 'react-router-dom';
import { toggleMaintenanceMode } from '@store/adcm/cluster/services/serviceComponents/serviceComponent/serviceComponentSlice';
import MaintenanceModeButton from '@commonComponents/MaintenanceModeButton/MaintenanceModeButton';

const ServiceComponentMaintenanceModeButton: React.FC = () => {
  const [isDialogOpened, setIsDialogOpened] = useState(false);

  const dispatch = useDispatch();

  const { clusterId: clusterIdFromUrl, serviceId: serviceIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);
  const serviceId = Number(serviceIdFromUrl);

  const serviceComponent = useStore(({ adcm }) => adcm.serviceComponent.serviceComponent ?? null);

  const onOpenDialog = () => {
    if (serviceComponent?.isMaintenanceModeAvailable) {
      setIsDialogOpened(true);
    }
  };

  const onCloseDialog = () => {
    setIsDialogOpened(false);
  };

  const onConfirmDialog = () => {
    if (serviceComponent) {
      const newMaintenanceMode = getRevertedMaintenanceModeStatus(serviceComponent);
      dispatch(
        toggleMaintenanceMode({
          clusterId,
          serviceId,
          componentId: serviceComponent.id,
          maintenanceMode: newMaintenanceMode,
        }),
      );
      onCloseDialog();
    }
  };

  return (
    serviceComponent && (
      <>
        <MaintenanceModeButton
          isMaintenanceModeAvailable={serviceComponent.isMaintenanceModeAvailable}
          maintenanceModeStatus={serviceComponent.maintenanceMode}
          onClick={onOpenDialog}
        />
        {isDialogOpened && (
          <MaintenanceModeDialog
            entity={serviceComponent}
            onCloseDialog={onCloseDialog}
            onConfirmDialog={onConfirmDialog}
          />
        )}
      </>
    )
  );
};

export default ServiceComponentMaintenanceModeButton;
