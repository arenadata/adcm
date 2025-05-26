import { useDispatch, useStore } from '@hooks';
import { closeBlockDialog, blockUsers } from '@store/adcm/users/usersActionsSlice';
import { DialogV2 } from '@uikit';
import type React from 'react';

const AccessManagerUsersBlockDialog: React.FC = () => {
  const dispatch = useDispatch();

  const userToBlock = useStore(({ adcm }) => adcm.usersActions.blockDialog?.user);

  if (!userToBlock) return null;

  const handleCloseConfirm = () => {
    dispatch(closeBlockDialog());
  };

  const handleConfirmDialog = () => {
    if (!userToBlock?.id) return;

    dispatch(blockUsers([userToBlock.id]));
  };

  return (
    <DialogV2
      //
      title="Block user"
      onAction={handleConfirmDialog}
      onCancel={handleCloseConfirm}
      actionButtonLabel="Block"
    >
      Selected user will be blocked and unable to access their account.
    </DialogV2>
  );
};

export default AccessManagerUsersBlockDialog;
