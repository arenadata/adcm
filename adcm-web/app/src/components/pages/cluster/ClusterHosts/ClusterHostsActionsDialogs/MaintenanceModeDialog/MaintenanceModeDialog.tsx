import { Dialog } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import React from 'react';
import {
  closeMaintenanceModeDialog,
  toggleMaintenanceModeWithUpdate,
} from '@store/adcm/cluster/hosts/hostsActionsSlice';
import { useParams } from 'react-router-dom';
import { AdcmMaintenanceMode } from '@models/adcm';

const MaintenanceModeDialog: React.FC = () => {
  const dispatch = useDispatch();
  const { clusterId: clusterIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);
  const isOpenMaintenanceMode = useStore((s) => s.adcm.clusterHostsActions.maintenanceModeDialog.isOpen);
  const host = useStore((s) => s.adcm.clusterHostsActions.maintenanceModeDialog.host);
  const hostId = host?.id;

  const action = host?.maintenanceMode === AdcmMaintenanceMode.On ? 'Disable' : 'Enable';
  const status = host?.maintenanceMode === AdcmMaintenanceMode.On ? AdcmMaintenanceMode.Off : AdcmMaintenanceMode.On;

  const handleCloseDialog = () => {
    dispatch(closeMaintenanceModeDialog());
  };

  const handleConfirmDialog = () => {
    if (hostId) {
      dispatch(toggleMaintenanceModeWithUpdate({ clusterId, hostId, maintenanceMode: status }));
    }
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
