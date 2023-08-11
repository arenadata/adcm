import React from 'react';
import { useDispatch } from '@hooks';
import { Button } from '@uikit';

const ClusterHostsAddHostsButton: React.FC = () => {
  const dispatch = useDispatch();

  const handleClick = () => {
    console.info('add hosts');
    // dispatch(openAddDialog());
  };

  return (
    <>
      <Button onClick={handleClick}>Create host</Button>
    </>
  );
};

export default ClusterHostsAddHostsButton;
