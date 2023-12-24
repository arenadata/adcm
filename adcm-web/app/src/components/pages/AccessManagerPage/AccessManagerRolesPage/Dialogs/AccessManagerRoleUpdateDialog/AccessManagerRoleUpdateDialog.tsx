import { Dialog } from '@uikit';
import { useAccessManagerRoleUpdateDialog } from './useAccessManagerRoleUpdateDialog';
import AccessManagerRoleDialogForm from '../AccessManagerRoleDialogForm/AccessManagerRoleDialogForm';
import s from '../AccessManagerRoleDialogForm/AccessManagerRoleDialogForm.module.scss';

const AccessManagerRoleUpdateDialog = () => {
  const { isOpen, isValid, formData, onUpdate, onClose, onChangeFormData, errors } = useAccessManagerRoleUpdateDialog();

  return (
    <Dialog
      title="Edit role"
      actionButtonLabel="Save"
      isOpen={isOpen}
      onOpenChange={onClose}
      onAction={onUpdate}
      isActionDisabled={!isValid}
      isDialogControlsOnTop
      width="100%"
      height="100%"
      className={s.roleDialog}
    >
      <AccessManagerRoleDialogForm onChangeFormData={onChangeFormData} formData={formData} errors={errors} />
    </Dialog>
  );
};

export default AccessManagerRoleUpdateDialog;
