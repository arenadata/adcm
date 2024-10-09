import { useDispatch, useStore } from '@hooks';
import { closeDeleteDialog, deleteRoleWithUpdate } from '@store/adcm/roles/rolesActionsSlice';
import { Dialog } from '@uikit';
import React from 'react';

const AccessManagerRolesDeleteDialog: React.FC = () => {
  const dispatch = useDispatch();

  const deletableRole = useStore(
    ({
      adcm: {
        roles: { roles },
        rolesActions: {
          deleteDialog: { role: deletableId },
        },
      },
    }) => {
      if (!deletableId) return null;
      return roles.find(({ id }) => id === deletableId) ?? null;
    },
  );

  const isOpenDeleteDialog = !!deletableRole;
  const name = deletableRole?.name;

  const handleCloseConfirm = () => {
    dispatch(closeDeleteDialog());
  };

  const handleConfirmDialog = () => {
    if (!deletableRole?.id) return;

    dispatch(deleteRoleWithUpdate(deletableRole.id));
  };

  return (
    <>
      <Dialog
        isOpen={isOpenDeleteDialog}
        onOpenChange={handleCloseConfirm}
        title={`Delete role "${name}"`}
        onAction={handleConfirmDialog}
        actionButtonLabel="Delete"
      >
        Role will be deleted.
      </Dialog>
    </>
  );
};

export default AccessManagerRolesDeleteDialog;
