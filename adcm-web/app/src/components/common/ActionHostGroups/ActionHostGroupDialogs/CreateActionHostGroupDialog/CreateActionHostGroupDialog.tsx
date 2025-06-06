import { DialogV2 } from '@uikit';
import ActionHostGroupDialogForm from '../ActionHostGroupDialogForm/ActionHostGroupDialogForm';
import {
  type AdcmActionHostGroupFormData,
  useActionHostGroupDialogForm,
} from '../ActionHostGroupDialogForm/useActionHostGroupDialogForm';
import s from '../ActionHostGroupDialogForm/ActionHostGroupDialogForm.module.scss';
import type { AdcmActionHostGroupHost } from '@models/adcm';
import { useEffect } from 'react';

export interface CreateActionHostGroupDialogProps {
  isOpen: boolean;
  hostCandidates: AdcmActionHostGroupHost[];
  onCreate: (formData: AdcmActionHostGroupFormData) => void;
  onClose: () => void;
}

const CreateActionHostGroupDialog = ({
  isOpen,
  hostCandidates,
  onCreate,
  onClose,
}: CreateActionHostGroupDialogProps) => {
  const { isValid, formData, errors, onChangeFormData, resetFormData } = useActionHostGroupDialogForm();

  useEffect(() => {
    if (!isOpen) {
      resetFormData();
    }
  }, [isOpen, resetFormData]);

  const handleAction = () => {
    onCreate(formData);
  };

  if (!isOpen) return null;

  return (
    <DialogV2
      title="Create action host group"
      actionButtonLabel="Create"
      onAction={handleAction}
      onCancel={onClose}
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
        isCreateNew={true}
      />
    </DialogV2>
  );
};

export default CreateActionHostGroupDialog;
