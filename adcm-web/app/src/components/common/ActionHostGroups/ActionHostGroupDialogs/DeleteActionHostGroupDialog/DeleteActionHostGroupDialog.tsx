import { Dialog } from '@uikit';
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
}: DeleteActionHostGroupDialogProps) => (
  <Dialog
    isOpen={isOpen}
    actionButtonLabel="Delete"
    title={`Delete action host group ${actionHostGroup.name}`}
    onAction={onDelete}
    onOpenChange={onClose}
  >
    Action host group {actionHostGroup.name} will be deleted
  </Dialog>
);

export default DeleteActionHostGroupDialog;
