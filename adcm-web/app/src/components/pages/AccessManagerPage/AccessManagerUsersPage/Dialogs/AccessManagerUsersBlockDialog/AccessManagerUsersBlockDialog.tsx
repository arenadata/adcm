import { useDispatch, useStore } from '@hooks';
import { closeBlockDialog, blockUsers } from '@store/adcm/users/usersActionsSlice';
import { Dialog } from '@uikit';
import React from 'react';

const AccessManagerUsersBlockDialog: React.FC = () => {
  const dispatch = useDispatch();

  const userToBlock = useStore(({ adcm }) => adcm.usersActions.blockDialog?.user);

  const isOpenDialog = !!userToBlock;

  const handleCloseConfirm = () => {
    dispatch(closeBlockDialog());
  };

  const handleConfirmDialog = () => {
    if (!userToBlock?.id) return;

    dispatch(blockUsers([userToBlock.id]));
  };

  return (
    <>
      <Dialog
        isOpen={isOpenDialog}
        onOpenChange={handleCloseConfirm}
        title="Block user"
        onAction={handleConfirmDialog}
        actionButtonLabel="Block"
      >
        Selected user will be blocked and unable to access their account.
      </Dialog>
    </>
  );
};

export default AccessManagerUsersBlockDialog;
