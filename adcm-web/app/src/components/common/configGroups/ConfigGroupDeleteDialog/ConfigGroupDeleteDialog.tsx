import React from 'react';
import { Dialog } from '@uikit';
import type { AdcmConfigGroup } from '@models/adcm';

interface ConfigGroupDeleteDialogProps {
  configGroup: AdcmConfigGroup | null;
  onSubmit: (configGroupId: number) => void;
  onClose: () => void;
}

const ConfigGroupDeleteDialog: React.FC<ConfigGroupDeleteDialogProps> = ({ configGroup, onSubmit, onClose }) => {
  const isOpen = configGroup !== null;

  const handleSubmit = () => {
    configGroup && onSubmit(configGroup.id);
  };

  return (
    <Dialog
      isOpen={isOpen}
      onOpenChange={onClose}
      title={`Delete "${configGroup?.name}" config-group`}
      onAction={handleSubmit}
      actionButtonLabel="Delete"
    >
      All config group information will be deleted
    </Dialog>
  );
};
export default ConfigGroupDeleteDialog;
