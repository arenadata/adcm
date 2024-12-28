import type React from 'react';
import { Dialog } from '@uikit';
import { useRbacUserUpdateDialog } from './useRbacUserUpdateDialog';
import RbacUserForm from '@pages/AccessManagerPage/AccessManagerUsersPage/RbacUserForm/RbacUserForm';

const RbacUserUpdateDialog: React.FC = () => {
  const {
    isOpen,
    isValid,
    onClose,
    formData,
    onChangeFormData,
    onSubmit,
    groups,
    errors,
    isPersonalDataEditForbidden,
    isCurrentUserSuperUser,
  } = useRbacUserUpdateDialog();

  return (
    <Dialog
      title="Edit user"
      isOpen={isOpen}
      onOpenChange={onClose}
      onAction={onSubmit}
      onCancel={onClose}
      isActionDisabled={!isValid}
      actionButtonLabel="Save"
    >
      <RbacUserForm
        isPersonalDataEditForbidden={isPersonalDataEditForbidden}
        isCurrentUserSuperUser={isCurrentUserSuperUser}
        onChangeFormData={onChangeFormData}
        formData={formData}
        groups={groups}
        errors={errors}
      />
    </Dialog>
  );
};
export default RbacUserUpdateDialog;
