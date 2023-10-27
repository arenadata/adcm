import { useDispatch, useStore } from '@hooks';
import { closeDeleteDialog, deleteUsersWithUpdate } from '@store/adcm/users/usersActionsSlice';
import { Dialog } from '@uikit';
import React from 'react';

const AccessManagerUsersDeleteDialog: React.FC = () => {
  const dispatch = useDispatch();

  const deletableUser = useStore(
    ({
      adcm: {
        users: { users },
        usersActions: {
          deleteDialog: { id: deletableId },
        },
      },
    }) => {
      if (!deletableId) return null;
      return users.find(({ id }) => id === deletableId) ?? null;
    },
  );

  const isOpenDeleteDialog = !!deletableUser;

  const handleCloseConfirm = () => {
    dispatch(closeDeleteDialog());
  };

  const handleConfirmDialog = () => {
    if (!deletableUser?.id) return;

    dispatch(deleteUsersWithUpdate([deletableUser.id]));
  };

  return (
    <>
      <Dialog
        isOpen={isOpenDeleteDialog}
        onOpenChange={handleCloseConfirm}
        title="Delete user"
        onAction={handleConfirmDialog}
        actionButtonLabel="Delete"
      >
        Selected user will be deleted
      </Dialog>
    </>
  );
};

export default AccessManagerUsersDeleteDialog;
