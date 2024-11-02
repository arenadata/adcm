import React from 'react';
import { useDispatch, useStore } from '@hooks';
import { closeMaintenanceModeDialog, toggleMaintenanceMode } from '@store/adcm/hosts/hostsActionsSlice';
import MaintenanceModeDialog from '@commonComponents/MaintenanceModeDialog/MaintenanceModeDialog';
import { getRevertedMaintenanceModeStatus } from '@commonComponents/MaintenanceModeDialog/MaintenanceModeDialog.utils';

const HostsMaintenanceModeDialog: React.FC = () => {
  const dispatch = useDispatch();

  const host = useStore(({ adcm }) => adcm.hostsActions.maintenanceModeDialog.host);

  const hostId = host?.id;

  const onCloseDialog = () => {
    dispatch(closeMaintenanceModeDialog());
  };

  const onConfirmDialog = () => {
    if (hostId) {
      const newMaintenanceMode = getRevertedMaintenanceModeStatus(host);
      dispatch(toggleMaintenanceMode({ hostId, maintenanceMode: newMaintenanceMode }));
    }
  };

  return (
    host && <MaintenanceModeDialog entity={host} onCloseDialog={onCloseDialog} onConfirmDialog={onConfirmDialog} />
  );
};

export default HostsMaintenanceModeDialog;
