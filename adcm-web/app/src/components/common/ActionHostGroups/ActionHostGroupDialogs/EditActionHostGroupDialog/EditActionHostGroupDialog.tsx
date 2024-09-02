import { Dialog } from '@uikit';
import ActionHostGroupDialogForm from '../ActionHostGroupDialogForm/ActionHostGroupDialogForm';
import {
  type AdcmActionHostGroupFormData,
  useActionHostGroupDialogForm,
} from '../ActionHostGroupDialogForm/useActionHostGroupDialogForm';
import type { AdcmActionHostGroup, AdcmActionHostGroupHost } from '@models/adcm';
import s from '../ActionHostGroupDialogForm/ActionHostGroupDialogForm.module.scss';

export interface EditActionHostGroupDialogProps {
  isOpen: boolean;
  actionHostGroup: AdcmActionHostGroup;
  hostCandidates: AdcmActionHostGroupHost[];
  onEdit: (formData: AdcmActionHostGroupFormData) => void;
  onClose: () => void;
}

const EditActionHostGroupDialog = ({
  isOpen,
  actionHostGroup,
  hostCandidates,
  onEdit,
  onClose,
}: EditActionHostGroupDialogProps) => {
  const { isValid, formData, onChangeFormData, errors } = useActionHostGroupDialogForm(actionHostGroup);

  const handleAction = () => {
    onEdit(formData);
  };

  return (
    <Dialog
      title="Edit action host group"
      actionButtonLabel="Save"
      isOpen={isOpen}
      onOpenChange={onClose}
      onAction={handleAction}
      isActionDisabled={!isValid}
      isDialogControlsOnTop
      width="100%"
      height="100%"
      className={s.actionHostGroupDialog}
    >
      <ActionHostGroupDialogForm
        formData={formData}
        errors={errors}
        hostCandidates={hostCandidates}
        onChangeFormData={onChangeFormData}
      />
    </Dialog>
  );
};

export default EditActionHostGroupDialog;
