import React from 'react';
import Dialog from '@uikit/Dialog/Dialog';
import { useDispatch, useStore } from '@hooks';
import { deleteWithUpdateHostProviders, setDeletableId } from '@store/adcm/hostProviders/hostProvidersSlice';

const HostProvidersDeleteDialog = () => {
  const dispatch = useDispatch();

  const providers = useStore(({ adcm }) => adcm.hostProviders.hostProviders);
  const deletableId = useStore(({ adcm }) => adcm.hostProviders.itemsForActions.deletableId);

  const isOpen = deletableId !== null;

  const handleCloseDialog = () => {
    dispatch(setDeletableId(null));
  };

  const handleConfirmDialog = () => {
    if (deletableId === null) return;

    dispatch(deleteWithUpdateHostProviders(deletableId));
  };

  const hostProviderName = providers.find(({ id }) => id === deletableId)?.name || '';

  return (
    <Dialog
      //
      isOpen={isOpen}
      onOpenChange={handleCloseDialog}
      title={`Delete "${hostProviderName}" hostprovider`}
      onAction={handleConfirmDialog}
      actionButtonLabel="Delete"
    >
      Are you sure?
    </Dialog>
  );
};
export default HostProvidersDeleteDialog;
