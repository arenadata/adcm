import { DialogV2 } from '@uikit';
import { useAccessManagerRoleUpdateDialog } from './useAccessManagerRoleUpdateDialog';
import AccessManagerRoleDialogForm from '../AccessManagerRoleDialogForm/AccessManagerRoleDialogForm';
import s from '../AccessManagerRoleDialogForm/AccessManagerRoleDialogForm.module.scss';

const AccessManagerRoleUpdateDialog = () => {
  const { isOpen, isValid, formData, onUpdate, onClose, onChangeFormData, errors } = useAccessManagerRoleUpdateDialog();

  return (
    isOpen && (
      <DialogV2
        title="Edit role"
        actionButtonLabel="Save"
        onAction={onUpdate}
        onCancel={onClose}
        isActionDisabled={!isValid}
        isDialogControlsOnTop
        width="100%"
        height="100%"
        className={s.roleDialog}
      >
        <AccessManagerRoleDialogForm onChangeFormData={onChangeFormData} formData={formData} errors={errors} />
      </DialogV2>
    )
  );
};

export default AccessManagerRoleUpdateDialog;
