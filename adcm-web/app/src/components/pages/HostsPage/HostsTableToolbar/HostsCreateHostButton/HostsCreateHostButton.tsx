import React from 'react';
import { Button } from '@uikit';
import { useDispatch } from '@hooks';
import { openCreateDialog } from '@store/adcm/hosts/hostsActionsSlice';

const HostsCreateHostButton: React.FC = () => {
  const dispatch = useDispatch();

  const handleClick = () => {
    dispatch(openCreateDialog());
  };

  return (
    <>
      <Button onClick={handleClick}>Create host</Button>
    </>
  );
};

export default HostsCreateHostButton;
