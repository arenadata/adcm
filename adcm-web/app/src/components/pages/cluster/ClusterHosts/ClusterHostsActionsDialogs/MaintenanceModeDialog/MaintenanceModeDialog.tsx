import { Dialog } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import React from 'react';
import { closeMaintenanceModeDialog } from '@store/adcm/cluster/hosts/hostsActionsSlice';

const MaintenanceModeDialog: React.FC = () => {
  const dispatch = useDispatch();
  const isOpenMaintenanceMode = useStore((s) => s.adcm.clusterHostsActions.maintenanceModeDialog.isOpen);
  const host = useStore((s) => s.adcm.clusterHostsActions.maintenanceModeDialog.host);

  const action = host?.maintenanceMode === 'on' ? 'Disable' : 'Enable';
  const status = host?.maintenanceMode === 'on' ? 'off' : 'on';

  const handleCloseDialog = () => {
    dispatch(closeMaintenanceModeDialog());
  };

  const handleConfirmDialog = () => {
    // dispatch(maintenanceModeToggle());
  };

  return (
    <>
      <Dialog
        isOpen={isOpenMaintenanceMode}
        onOpenChange={handleCloseDialog}
        title={`${action} maintenance mode`}
        onAction={handleConfirmDialog}
        actionButtonLabel={action}
      >
        <div>
          The maintenance mode will be turned {status} on "{host?.name}".
        </div>
      </Dialog>
    </>
  );
};

export default MaintenanceModeDialog;
