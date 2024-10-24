import { useDispatch, useStore } from '@hooks';
import { closeUnblockDialog, unblockUsers } from '@store/adcm/users/usersActionsSlice';
import { Dialog } from '@uikit';
import React from 'react';

const AccessManagerUsersUnblockDialog: React.FC = () => {
  const dispatch = useDispatch();

  const userToUnblock = useStore((s) => s.adcm.usersActions.unblockDialog.user);

  const isOpenDialog = !!userToUnblock;

  const handleCloseConfirm = () => {
    dispatch(closeUnblockDialog());
  };

  const handleConfirmDialog = () => {
    if (!userToUnblock) return;

    dispatch(unblockUsers([userToUnblock.id]));
  };

  return (
    <>
      <Dialog
        isOpen={isOpenDialog}
        onOpenChange={handleCloseConfirm}
        title="Unblock user"
        onAction={handleConfirmDialog}
        actionButtonLabel="Unblock"
      >
        Selected user will be unblocked and able to access their account
      </Dialog>
    </>
  );
};

export default AccessManagerUsersUnblockDialog;
