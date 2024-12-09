import type React from 'react';
import { Button } from '@uikit';
import { useDispatch } from '@hooks';
import { openCreateDialog } from '@store/adcm/roles/rolesActionsSlice';

const AccessManagerRolesCreateButton: React.FC = () => {
  const dispatch = useDispatch();

  const handleOpenDialog = () => {
    dispatch(openCreateDialog());
  };

  return <Button onClick={handleOpenDialog}>Create role</Button>;
};

export default AccessManagerRolesCreateButton;
