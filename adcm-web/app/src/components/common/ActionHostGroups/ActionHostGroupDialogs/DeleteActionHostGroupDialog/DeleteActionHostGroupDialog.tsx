import { DialogV2 } from '@uikit';
import type { AdcmActionHostGroup } from '@models/adcm';

export interface DeleteActionHostGroupDialogProps {
  isOpen: boolean;
  actionHostGroup: AdcmActionHostGroup;
  onDelete: () => void;
  onClose: () => void;
}

const DeleteActionHostGroupDialog = ({
  isOpen,
  actionHostGroup,
  onDelete,
  onClose,
}: DeleteActionHostGroupDialogProps) => {
  if (!isOpen) return null;

  return (
    <DialogV2
      actionButtonLabel="Delete"
      title={`Delete action host group ${actionHostGroup.name}`}
      onAction={onDelete}
      onCancel={onClose}
    >
      Action host group {actionHostGroup.name} will be deleted
    </DialogV2>
  );
};

export default DeleteActionHostGroupDialog;
