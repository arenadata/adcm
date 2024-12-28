import { useDispatch, useStore } from '@hooks';
import { closeDeleteDialog, deleteUsersWithUpdate } from '@store/adcm/users/usersActionsSlice';
import { Dialog } from '@uikit';
import type React from 'react';

const AccessManagerUsersDeleteDialog: React.FC = () => {
  const dispatch = useDispatch();

  const user = useStore(({ adcm }) => adcm.usersActions.deleteDialog.user);

  const isOpenDeleteDialog = !!user;

  const handleCloseConfirm = () => {
    dispatch(closeDeleteDialog());
  };

  const handleConfirmDialog = () => {
    if (!user) return;

    dispatch(deleteUsersWithUpdate([user.id]));
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
