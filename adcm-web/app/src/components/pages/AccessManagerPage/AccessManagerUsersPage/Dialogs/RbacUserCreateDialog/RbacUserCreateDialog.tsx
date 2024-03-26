import React from 'react';
import { Dialog } from '@uikit';
import { useRbacUserCreateDialog } from './useRbacUserCreateDialog';
import RbacUserForm from '@pages/AccessManagerPage/AccessManagerUsersPage/RbacUserForm/RbacUserForm';

const RbacUserCreateDialog: React.FC = () => {
  const {
    //
    isOpen,
    isValid,
    onClose,
    formData,
    onChangeFormData,
    onSubmit,
    groups,
    errors,
    isCurrentUserSuperUser,
  } = useRbacUserCreateDialog();

  return (
    <Dialog
      title="Create new user"
      isOpen={isOpen}
      onOpenChange={onClose}
      onAction={onSubmit}
      onCancel={onClose}
      actionButtonLabel="Create"
      isActionDisabled={!isValid}
    >
      <form>
        <RbacUserForm
          onChangeFormData={onChangeFormData}
          isCurrentUserSuperUser={isCurrentUserSuperUser}
          formData={formData}
          groups={groups}
          errors={errors}
          isCreate={true}
        />
      </form>
    </Dialog>
  );
};
export default RbacUserCreateDialog;
