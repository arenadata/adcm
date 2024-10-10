import { useDispatch, useStore } from '@hooks';
import { closeDeleteDialog, deleteRoleWithUpdate } from '@store/adcm/roles/rolesActionsSlice';
import { Dialog } from '@uikit';
import React from 'react';

const AccessManagerRolesDeleteDialog: React.FC = () => {
  const dispatch = useDispatch();

  const role = useStore(({ adcm }) => adcm.rolesActions.deleteDialog.role);

  const isOpenDeleteDialog = !!role;

  const handleCloseConfirm = () => {
    dispatch(closeDeleteDialog());
  };

  const handleConfirmDialog = () => {
    if (!role) return;

    dispatch(deleteRoleWithUpdate(role));
  };

  return (
    <>
      <Dialog
        isOpen={isOpenDeleteDialog}
        onOpenChange={handleCloseConfirm}
        title={`Delete role "${role?.name}"`}
        onAction={handleConfirmDialog}
        actionButtonLabel="Delete"
      >
        Role will be deleted.
      </Dialog>
    </>
  );
};

export default AccessManagerRolesDeleteDialog;
