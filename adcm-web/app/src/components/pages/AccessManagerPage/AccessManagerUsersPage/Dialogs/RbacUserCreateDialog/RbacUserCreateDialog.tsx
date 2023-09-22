import React from 'react';
import { Dialog } from '@uikit';
import { useRbacUserCreateDialog } from './useRbacUserCreateDialog';
import RbacUserForm from '@pages/AccessManagerPage/AccessManagerUsersPage/RbacUserForm/RbacUserForm';

const RbacUserCreateDialog: React.FC = () => {
  const { isOpen, isValid, onClose, formData, onChangeFormData, onSubmit, groups, errors } = useRbacUserCreateDialog();

  return (
    <Dialog
      title="Create new user"
      isOpen={isOpen}
      onOpenChange={onClose}
      onAction={onSubmit}
      onCancel={onClose}
      isActionDisabled={!isValid}
    >
      <RbacUserForm
        onChangeFormData={onChangeFormData}
        formData={formData}
        groups={groups}
        errors={errors}
        isCreate={true}
      />
    </Dialog>
  );
};
export default RbacUserCreateDialog;
