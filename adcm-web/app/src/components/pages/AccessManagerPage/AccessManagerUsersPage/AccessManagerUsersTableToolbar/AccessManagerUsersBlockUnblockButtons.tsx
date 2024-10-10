import React, { useMemo } from 'react';
import { Button } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import { openBlockDialog, openUnblockDialog } from '@store/adcm/users/usersActionsSlice';
import { AdcmUserStatus } from '@models/adcm';

const AccessManagerUsersBlockUnblockButtons: React.FC = () => {
  const dispatch = useDispatch();

  const users = useStore((s) => s.adcm.users.users);
  const selectedUsers = useStore(({ adcm }) => adcm.usersActions.selectedUsers);
  const selectedUsersIds = useMemo(() => selectedUsers.map(({ id }) => id), [selectedUsers]);
  const isSelectedSomeBlockedUsers = users.some(
    (user) => selectedUsersIds.includes(user.id) && user.status === AdcmUserStatus.Blocked,
  );
  const isSelectedSomeActiveUsers = users.some(
    (user) => selectedUsersIds.includes(user.id) && user.status === AdcmUserStatus.Active && !user.isSuperUser,
  );

  const handleBlockClick = () => {
    dispatch(openBlockDialog(selectedUsers));
  };

  const handleUnblockClick = () => {
    dispatch(openUnblockDialog(selectedUsers));
  };

  return (
    <>
      <Button variant="secondary" disabled={!isSelectedSomeActiveUsers} onClick={handleBlockClick}>
        Block
      </Button>
      <Button variant="secondary" disabled={!isSelectedSomeBlockedUsers} onClick={handleUnblockClick}>
        Unblock
      </Button>
    </>
  );
};

export default AccessManagerUsersBlockUnblockButtons;
