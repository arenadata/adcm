import { useDispatch, useStore } from '@hooks';
import { closeUnblockDialog, unblockUsers } from '@store/adcm/users/usersActionsSlice';
import { Dialog } from '@uikit';
import React, { useMemo } from 'react';

const AccessManagerUsersUnblockDialog: React.FC = () => {
  const dispatch = useDispatch();

  const users = useStore((s) => s.adcm.users.users);
  const unblockUsersList = useStore((s) => s.adcm.usersActions.unblockDialog.unblockUsersList);
  const selectedUsersToUnblock = useMemo(
    () => users.filter((user) => unblockUsersList.includes(user)),
    [users, unblockUsersList],
  );

  const isOpenDialog = !!selectedUsersToUnblock?.length;

  const handleCloseConfirm = () => {
    dispatch(closeUnblockDialog());
  };

  const handleConfirmDialog = () => {
    if (!selectedUsersToUnblock?.length) return;

    dispatch(unblockUsers(selectedUsersToUnblock));
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
