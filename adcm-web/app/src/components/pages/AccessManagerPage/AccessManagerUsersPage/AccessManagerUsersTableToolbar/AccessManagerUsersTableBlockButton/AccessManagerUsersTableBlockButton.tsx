import type React from 'react';
import { useMemo, useState } from 'react';
import { Button, Dialog } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import { blockUsers } from '@store/adcm/users/usersActionsSlice';
import { AdcmUserStatus } from '@models/adcm';

const AccessManagerUsersTableBlockButton: React.FC = () => {
  const [isBlockDialogOpen, setIsBlockDialogOpen] = useState(false);
  const dispatch = useDispatch();

  const users = useStore((s) => s.adcm.users.users);
  const selectedUsersIds = useStore(({ adcm }) => adcm.usersActions.selectedUsersIds);
  const areSomeActiveUsersSelected = useMemo(
    () =>
      users.some(
        (user) => selectedUsersIds.includes(user.id) && user.status === AdcmUserStatus.Active && !user.isSuperUser,
      ),
    [users, selectedUsersIds],
  );

  const handleBlockClick = () => {
    setIsBlockDialogOpen(true);
  };

  const handleCloseConfirm = () => {
    setIsBlockDialogOpen(false);
  };

  const handleConfirmDialog = () => {
    dispatch(blockUsers(selectedUsersIds));
    handleCloseConfirm();
  };

  return (
    <>
      <Button variant="secondary" disabled={!areSomeActiveUsersSelected} onClick={handleBlockClick}>
        Block
      </Button>
      <Dialog
        isOpen={isBlockDialogOpen}
        onOpenChange={handleCloseConfirm}
        title="Block users"
        onAction={handleConfirmDialog}
        actionButtonLabel="Block"
      >
        All selected users will be blocked and unable to access their account.
      </Dialog>
    </>
  );
};

export default AccessManagerUsersTableBlockButton;
