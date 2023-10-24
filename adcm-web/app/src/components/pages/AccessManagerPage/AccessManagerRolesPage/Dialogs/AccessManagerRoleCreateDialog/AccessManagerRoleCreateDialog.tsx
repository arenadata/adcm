import { Dialog } from '@uikit';
import { useAccessManagerRoleCreateDialog } from './useAccessManagerRoleCreateDialog';
import AccessManagerRoleDialogForm from '../AccessManagerRoleDialogForm/AccessManagerRoleDialogForm';

const AccessManagerRoleCreateDialog = () => {
  const { isOpen, isValid, formData, onCreate, onClose, onChangeFormData, errors } = useAccessManagerRoleCreateDialog();

  return (
    <Dialog
      title="Create role"
      actionButtonLabel="Create"
      isOpen={isOpen}
      onOpenChange={onClose}
      onAction={onCreate}
      isActionDisabled={!isValid}
      isDialogControlsOnTop
      width="100%"
      height="100%"
    >
      <AccessManagerRoleDialogForm onChangeFormData={onChangeFormData} formData={formData} errors={errors} />
    </Dialog>
  );
};

export default AccessManagerRoleCreateDialog;
