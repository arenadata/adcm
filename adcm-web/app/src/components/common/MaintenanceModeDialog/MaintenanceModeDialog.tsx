import React from 'react';
import { Dialog } from '@uikit';
import { AdcmMaintenanceMode } from '@models/adcm';
import { EntityWithMaintenanceModeType, getRevertedMaintenanceModeStatus } from './MaintenanceModeDialog.utils';

interface MaintenanceModeDialogProps {
  entity: EntityWithMaintenanceModeType;
  onCloseDialog: () => void;
  onConfirmDialog: () => void;
}

const statusLabels: {
  [key in Exclude<AdcmMaintenanceMode, AdcmMaintenanceMode.Pending | AdcmMaintenanceMode.Changing>]: string;
} = {
  [AdcmMaintenanceMode.On]: 'Enable',
  [AdcmMaintenanceMode.Off]: 'Disable',
};

const MaintenanceModeDialog: React.FC<MaintenanceModeDialogProps> = ({ entity, onCloseDialog, onConfirmDialog }) => {
  const newMaintenanceMode = getRevertedMaintenanceModeStatus(entity);

  return (
    <>
      <Dialog
        //
        isOpen={true}
        onOpenChange={onCloseDialog}
        title={`${statusLabels[newMaintenanceMode]} maintenance mode`}
        onAction={onConfirmDialog}
        actionButtonLabel={statusLabels[newMaintenanceMode]}
      >
        The maintenance mode will be turned {newMaintenanceMode} on {entity?.name}
      </Dialog>
    </>
  );
};

export default MaintenanceModeDialog;
