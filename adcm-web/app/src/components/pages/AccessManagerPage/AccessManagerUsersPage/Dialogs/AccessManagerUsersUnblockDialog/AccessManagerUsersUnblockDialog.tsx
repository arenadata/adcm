import { useDispatch, useStore } from '@hooks';
import { closeUnblockDialog, unblockUsers } from '@store/adcm/users/usersActionsSlice';
import { Dialog } from '@uikit';
import React from 'react';

const AccessManagerUsersUnblockDialog: React.FC = () => {
  const dispatch = useDispatch();

  const selectedUsers = useStore(
    ({
      adcm: {
        users: { users },
        usersActions: {
          unblockDialog: { ids: selectedIds },
        },
      },
    }) => {
      if (!selectedIds) return null;
      return users.filter(({ id }) => selectedIds.includes(id)) ?? null;
    },
  );

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
