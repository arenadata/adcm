import React from 'react';
import { Button } from '@uikit';
import { useDispatch } from '@hooks';
import { open } from '@store/adcm/hostProviders/dialogs/createHostProviderDialogSlice';

const HostProviderCreateButton = () => {
  const dispatch = useDispatch();

  const createHostProviderHandler = () => {
    dispatch(open());
  };

  return (
    <>
      <Button onClick={createHostProviderHandler}>Create hostprovider</Button>
    </>
  );
};

export default HostProviderCreateButton;
