import type React from 'react';
import { useMemo, useState } from 'react';
import { Button, Dialog } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import { unblockUsers } from '@store/adcm/users/usersActionsSlice';
import { AdcmUserStatus } from '@models/adcm';

const AccessManagerUsersUnblockButton: React.FC = () => {
  const [isUnblockDialogOpen, setIsUnblockDialogOpen] = useState(false);
  const dispatch = useDispatch();

  const users = useStore((s) => s.adcm.users.users);
  const selectedUsersIds = useStore(({ adcm }) => adcm.usersActions.selectedUsersIds);
  const areSomeBlockedUsersSelected = useMemo(
    () => users.some((user) => selectedUsersIds.includes(user.id) && user.status === AdcmUserStatus.Blocked),
    [users, selectedUsersIds],
  );

  const handleUnblockClick = () => {
    setIsUnblockDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setIsUnblockDialogOpen(false);
  };

  const handleConfirmDialog = () => {
    dispatch(unblockUsers(selectedUsersIds));
    handleCloseDialog();
  };

  return (
    <>
      <Button variant="secondary" disabled={!areSomeBlockedUsersSelected} onClick={handleUnblockClick}>
        Unblock
      </Button>
      <Dialog
        isOpen={isUnblockDialogOpen}
        onOpenChange={handleCloseDialog}
        title="Unblock users"
        onAction={handleConfirmDialog}
        actionButtonLabel="Unblock"
      >
        All selected users will be unblocked and able to access their account.
      </Dialog>
    </>
  );
};

export default AccessManagerUsersUnblockButton;
