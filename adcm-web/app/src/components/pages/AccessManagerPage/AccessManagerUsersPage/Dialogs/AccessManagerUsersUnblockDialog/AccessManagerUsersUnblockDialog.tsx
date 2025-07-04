import { useDispatch, useStore } from '@hooks';
import { closeUnblockDialog, unblockUsers } from '@store/adcm/users/usersActionsSlice';
import { DialogV2 } from '@uikit';
import type React from 'react';

const AccessManagerUsersUnblockDialog: React.FC = () => {
  const dispatch = useDispatch();

  const userToUnblock = useStore((s) => s.adcm.usersActions.unblockDialog.user);

  if (!userToUnblock) return null;

  const handleCloseConfirm = () => {
    dispatch(closeUnblockDialog());
  };

  const handleConfirmDialog = () => {
    if (!userToUnblock) return;

    dispatch(unblockUsers([userToUnblock.id]));
  };

  return (
    <>
      <DialogV2
        title="Unblock user"
        onAction={handleConfirmDialog}
        onCancel={handleCloseConfirm}
        actionButtonLabel="Unblock"
      >
        Selected user will be unblocked and able to access their account
      </DialogV2>
    </>
  );
};

export default AccessManagerUsersUnblockDialog;
