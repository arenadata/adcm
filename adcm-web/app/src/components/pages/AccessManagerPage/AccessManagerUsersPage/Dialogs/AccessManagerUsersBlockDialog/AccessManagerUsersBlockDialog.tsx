import { useDispatch, useStore } from '@hooks';
import { closeBlockDialog, blockUsers } from '@store/adcm/users/usersActionsSlice';
import { Dialog } from '@uikit';
import React, { useMemo } from 'react';

const AccessManagerUsersBlockDialog: React.FC = () => {
  const dispatch = useDispatch();

  const users = useStore((s) => s.adcm.users.users);
  const blockUsersList = useStore((s) => s.adcm.usersActions.blockDialog.blockUsersList);
  const selectedUsersToBlock = useMemo(
    () => users.filter((user) => blockUsersList.includes(user)),
    [users, blockUsersList],
  );

  const isOpenDialog = !!selectedUsersToBlock?.length;

  const handleCloseConfirm = () => {
    dispatch(closeBlockDialog());
  };

  const handleConfirmDialog = () => {
    if (!selectedUsersToBlock?.length) return;

    dispatch(blockUsers(selectedUsersToBlock));
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
