import React from 'react';
import { Button } from '@uikit';
import { useDispatch } from '@hooks';
import { open } from '@store/adcm/users/dialogs/createUserDialogSlice';

const AccessManagerUsersCreateButton: React.FC = () => {
  const dispatch = useDispatch();

  const handleOpenDialog = () => {
    dispatch(open());
  };

  return <Button onClick={handleOpenDialog}>Create user</Button>;
};

export default AccessManagerUsersCreateButton;
