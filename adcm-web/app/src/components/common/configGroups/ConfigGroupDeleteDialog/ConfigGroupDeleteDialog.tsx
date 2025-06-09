import type React from 'react';
import { DialogV2 } from '@uikit';
import type { AdcmConfigGroup } from '@models/adcm';

interface ConfigGroupDeleteDialogProps {
  configGroup: AdcmConfigGroup | null;
  onSubmit: (configGroupId: number) => void;
  onClose: () => void;
}

const ConfigGroupDeleteDialog: React.FC<ConfigGroupDeleteDialogProps> = ({ configGroup, onSubmit, onClose }) => {
  if (configGroup === null) return;

  const handleSubmit = () => {
    configGroup && onSubmit(configGroup.id);
  };

  return (
    <DialogV2
      title={`Delete "${configGroup?.name}" config-group`}
      onAction={handleSubmit}
      onCancel={onClose}
      actionButtonLabel="Delete"
    >
      All config group information will be deleted
    </DialogV2>
  );
};
export default ConfigGroupDeleteDialog;
