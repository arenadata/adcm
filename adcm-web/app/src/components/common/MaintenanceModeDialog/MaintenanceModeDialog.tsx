import type React from 'react';
import { DialogV2 } from '@uikit';
import { AdcmMaintenanceMode } from '@models/adcm';
import type { EntityWithMaintenanceModeType } from './MaintenanceModeDialog.utils';
import { getEntityDisplayName, getRevertedMaintenanceModeStatus } from './MaintenanceModeDialog.utils';

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
  const entityDisplayName = getEntityDisplayName(entity);

  return (
    <>
      <DialogV2
        //
        title={`${statusLabels[newMaintenanceMode]} maintenance mode`}
        onCancel={onCloseDialog}
        onAction={onConfirmDialog}
        actionButtonLabel={statusLabels[newMaintenanceMode]}
      >
        The maintenance mode will be turned {newMaintenanceMode} on {entityDisplayName}
      </DialogV2>
    </>
  );
};

export default MaintenanceModeDialog;
