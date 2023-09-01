import React from 'react';
import { useDispatch, useStore } from '@hooks';
import { Dialog } from '@uikit';
import { AdcmMaintenanceMode } from '@models/adcm';
import { closeMaintenanceModeDialog, toggleMaintenanceModeWithUpdate } from '@store/adcm/hosts/hostsActionsSlice';

const statusLabels: { [key in Exclude<AdcmMaintenanceMode, AdcmMaintenanceMode.Pending>]: string } = {
  [AdcmMaintenanceMode.On]: 'Enable',
  [AdcmMaintenanceMode.Off]: 'Disable',
};

const MaintenanceModeDialog: React.FC = () => {
  const dispatch = useDispatch();

  const host = useStore(({ adcm }) => {
    return adcm.hosts.hosts.find(({ id }) => id === adcm.hostsActions.maintenanceModeDialog.id) ?? null;
  });
  const hostId = host?.id;
  const newMaintenanceMode =
    host?.maintenanceMode === AdcmMaintenanceMode.Off ? AdcmMaintenanceMode.On : AdcmMaintenanceMode.Off;

  const isOpen = !!hostId;

  const handleCloseConfirm = () => {
    dispatch(closeMaintenanceModeDialog());
  };

  const handleConfirmDialog = () => {
    if (hostId) {
      dispatch(toggleMaintenanceModeWithUpdate({ hostId, maintenanceMode: newMaintenanceMode }));
    }
  };

  return (
    <>
      <Dialog
        //
        isOpen={isOpen}
        onOpenChange={handleCloseConfirm}
        title={`${statusLabels[newMaintenanceMode]} maintenance mode`}
        onAction={handleConfirmDialog}
        actionButtonLabel={statusLabels[newMaintenanceMode]}
      >
        The maintenance mode will be turned {newMaintenanceMode} on {host?.name}
      </Dialog>
    </>
  );
};

export default MaintenanceModeDialog;
