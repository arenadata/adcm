import React from 'react';
import { useDispatch } from '@hooks';
import { Button } from '@uikit';
import { openAddDialog } from '@store/adcm/cluster/hosts/hostsActionsSlice';

const ClusterHostsAddHostsButton: React.FC = () => {
  const dispatch = useDispatch();

  const handleClick = () => {
    dispatch(openAddDialog());
  };

  return (
    <>
      <Button onClick={handleClick}>Create host</Button>
    </>
  );
};

export default ClusterHostsAddHostsButton;
