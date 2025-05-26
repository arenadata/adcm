import { DialogV2 } from '@uikit';
import { useAccessManagerRoleCreateDialog } from './useAccessManagerRoleCreateDialog';
import AccessManagerRoleDialogForm from '../AccessManagerRoleDialogForm/AccessManagerRoleDialogForm';
import s from '../AccessManagerRoleDialogForm/AccessManagerRoleDialogForm.module.scss';

const AccessManagerRoleCreateDialog = () => {
  const { isOpen, isValid, formData, onCreate, onClose, onChangeFormData, errors } = useAccessManagerRoleCreateDialog();

  return (
    isOpen && (
      <DialogV2
        title="Create role"
        actionButtonLabel="Create"
        onAction={onCreate}
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

export default AccessManagerRoleCreateDialog;
