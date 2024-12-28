import type React from 'react';
import { useDispatch } from '@hooks';
import { Button } from '@uikit';
import { openCreateDialog } from '@store/adcm/cluster/hosts/hostsActionsSlice';

const ClusterHostsAddHostsButton: React.FC = () => {
  const dispatch = useDispatch();

  const handleClick = () => {
    dispatch(openCreateDialog());
  };

  return <Button onClick={handleClick}>Add hosts</Button>;
};

export default ClusterHostsAddHostsButton;
