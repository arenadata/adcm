import { useDispatch, useStore } from '@hooks';
import { closeUnblockDialog, unblockUsers } from '@store/adcm/users/usersActionsSlice';
import { Dialog } from '@uikit';
import React, { useMemo } from 'react';

const AccessManagerUsersUnblockDialog: React.FC = () => {
  const dispatch = useDispatch();

  const users = useStore((s) => s.adcm.users.users);
  const selectedIds = useStore((s) => s.adcm.usersActions.unblockDialog.ids);
  const selectedUsers = useMemo(() => users.filter(({ id }) => selectedIds.includes(id)), [users, selectedIds]);

  const isOpenDialog = !!selectedUsers?.length;

  const handleCloseConfirm = () => {
    dispatch(closeUnblockDialog());
  };

  const handleConfirmDialog = () => {
    if (!selectedUsers?.length) return;

    dispatch(unblockUsers(selectedUsers.map((user) => user.id)));
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
        User will be unblocked and able to access their account. All failure login attempts will be reset to 0
      </Dialog>
    </>
  );
};

export default AccessManagerUsersUnblockDialog;
