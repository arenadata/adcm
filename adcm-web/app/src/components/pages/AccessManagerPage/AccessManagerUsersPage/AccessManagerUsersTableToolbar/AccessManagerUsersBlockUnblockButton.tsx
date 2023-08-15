import React from 'react';
import { Button } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import { blockUsers, unblockUsers } from '@store/adcm/users/usersActionsSlice';
import { AdcmUserStatus } from '@models/adcm';

const AccessManagerUsersBlockUnblockButtons: React.FC = () => {
  const dispatch = useDispatch();

  const users = useStore((s) => s.adcm.users.users);
  const selectedItemsIds = useStore(({ adcm }) => adcm.usersActions.selectedItemsIds);
  const isSelectedSomeActiveUsers = users.some(
    (user) => selectedItemsIds.includes(user.id) && user.status === AdcmUserStatus.Active,
  );
  const isSelectedSomeBlockedUsers = users.some(
    (user) => selectedItemsIds.includes(user.id) && user.status === AdcmUserStatus.Blocked,
  );

  const handleBlockClick = () => () => {
    dispatch(blockUsers(selectedItemsIds));
  };

  const handleUnblockClick = () => () => {
    dispatch(unblockUsers(selectedItemsIds));
  };

  return (
    <>
      <Button variant="secondary" disabled={!isSelectedSomeActiveUsers} onClick={handleBlockClick()}>
        Block
      </Button>
      <Button variant="secondary" disabled={!isSelectedSomeBlockedUsers} onClick={handleUnblockClick()}>
        Unblock
      </Button>
    </>
  );
};

export default AccessManagerUsersBlockUnblockButtons;
