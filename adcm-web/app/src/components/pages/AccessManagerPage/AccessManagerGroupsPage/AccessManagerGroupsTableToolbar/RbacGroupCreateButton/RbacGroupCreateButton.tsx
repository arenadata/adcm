import React from 'react';
import { Button } from '@uikit';
import { useDispatch } from '@hooks';
import { openCreateDialog } from '@store/adcm/groups/groupsActionsSlice';

const RbacGroupCreateButton: React.FC = () => {
  const dispatch = useDispatch();

  const handleClick = () => {
    dispatch(openCreateDialog());
  };

  return (
    <>
      <Button onClick={handleClick}>Create group</Button>
    </>
  );
};

export default RbacGroupCreateButton;
