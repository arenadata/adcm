import { useDispatch, useStore } from '@hooks';
import { closeDeleteDialog, deleteUsersWithUpdate } from '@store/adcm/users/usersActionsSlice';
import { DialogV2 } from '@uikit';
import type React from 'react';

const AccessManagerUsersDeleteDialog: React.FC = () => {
  const dispatch = useDispatch();

  const user = useStore(({ adcm }) => adcm.usersActions.deleteDialog.user);

  if (!user) return null;

  const handleCloseConfirm = () => {
    dispatch(closeDeleteDialog());
  };

  const handleConfirmDialog = () => {
    if (!user) return;

    dispatch(deleteUsersWithUpdate([user.id]));
  };

  return (
    <DialogV2
      title="Delete user"
      onAction={handleConfirmDialog}
      onCancel={handleCloseConfirm}
      actionButtonLabel="Delete"
    >
      Selected user will be deleted
    </DialogV2>
  );
};

export default AccessManagerUsersDeleteDialog;
