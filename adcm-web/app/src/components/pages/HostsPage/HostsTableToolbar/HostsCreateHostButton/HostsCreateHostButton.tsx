import type React from 'react';
import { Button } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import { openCreateDialog } from '@store/adcm/hosts/hostsActionsSlice';

const HostsCreateHostButton: React.FC = () => {
  const dispatch = useDispatch();

  const isCreating = useStore(({ adcm }) => adcm.hostsActions.isActionInProgress);

  const handleClick = () => {
    dispatch(openCreateDialog());
  };

  return (
    <>
      <Button
        onClick={handleClick}
        disabled={isCreating}
        iconLeft={isCreating ? { name: 'g1-load', className: 'spin' } : undefined}
      >
        Create host
      </Button>
    </>
  );
};

export default HostsCreateHostButton;
