import React from 'react';
import { Button } from '@uikit';
import { useDispatch } from '@hooks';
import { openCreateDialog } from '@store/adcm/hostProviders/hostProvidersActionsSlice';

const HostProviderCreateButton = () => {
  const dispatch = useDispatch();

  const createHostProviderHandler = () => {
    dispatch(openCreateDialog());
  };

  return <Button onClick={createHostProviderHandler}>Create hostprovider</Button>;
};

export default HostProviderCreateButton;
