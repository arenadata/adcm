import type React from 'react';
import { Button } from '@uikit';
import { useDispatch } from '@hooks';
import { openUserCreateDialog } from '@store/adcm/users/usersActionsSlice';

const AccessManagerUsersCreateButton: React.FC = () => {
  const dispatch = useDispatch();

  const handleOpenDialog = () => {
    dispatch(openUserCreateDialog());
  };

  return <Button onClick={handleOpenDialog}>Create user</Button>;
};

export default AccessManagerUsersCreateButton;
