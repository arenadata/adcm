import type React from 'react';
import { DialogV2 } from '@uikit';
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
    isOpen && (
      <DialogV2
        title="Create new user"
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
      </DialogV2>
    )
  );
};
export default RbacUserCreateDialog;
