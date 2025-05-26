import { useDispatch, useStore } from '@hooks';
import { closeDeleteDialog, deleteRoleWithUpdate } from '@store/adcm/roles/rolesActionsSlice';
import { DialogV2 } from '@uikit';
import type React from 'react';

const AccessManagerRolesDeleteDialog: React.FC = () => {
  const dispatch = useDispatch();

  const role = useStore(({ adcm }) => adcm.rolesActions.deleteDialog.role);

  if (!role) return null;

  const handleCloseConfirm = () => {
    dispatch(closeDeleteDialog());
  };

  const handleConfirmDialog = () => {
    if (!role) return;

    dispatch(deleteRoleWithUpdate(role));
  };

  return (
    <DialogV2
      title={`Delete role "${role?.name}"`}
      onAction={handleConfirmDialog}
      onCancel={handleCloseConfirm}
      actionButtonLabel="Delete"
    >
      Role will be deleted.
    </DialogV2>
  );
};

export default AccessManagerRolesDeleteDialog;
