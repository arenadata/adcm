import { useDispatch, useStore } from '@hooks';
import { closeBlockDialog, blockUsers } from '@store/adcm/users/usersActionsSlice';
import { Dialog } from '@uikit';
import React, { useMemo } from 'react';

const AccessManagerUsersBlockDialog: React.FC = () => {
  const dispatch = useDispatch();

  const users = useStore((s) => s.adcm.users.users);
  const selectedIds = useStore((s) => s.adcm.usersActions.blockDialog.ids);
  const selectedUsers = useMemo(() => users.filter(({ id }) => selectedIds.includes(id)), [users, selectedIds]);

  const isOpenDialog = !!selectedUsers?.length;

  const handleCloseConfirm = () => {
    dispatch(closeBlockDialog());
  };

  const handleConfirmDialog = () => {
    if (!selectedUsers?.length) return;

    dispatch(blockUsers(selectedUsers.map((user) => user.id)));
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
