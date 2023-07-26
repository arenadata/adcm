import { useDispatch, useStore } from '@hooks';
import { deleteWithUpdateHosts, setDeletableId } from '@store/adcm/hosts/hostsSlice.tsx';
import { Dialog } from '@uikit';
import React from 'react';

const HostItemDeleteDialog: React.FC = () => {
  const dispatch = useDispatch();

  const hosts = useStore(({ adcm }) => adcm.hosts.hosts);
  const deletableId = useStore(({ adcm }) => adcm.hosts.itemsForActions.deletableId);

  const isOpen = deletableId !== null;

  const handleCloseDialog = () => {
    dispatch(setDeletableId(null));
  };

  const handleConfirmDialog = () => {
    if (deletableId === null) return;

    dispatch(deleteWithUpdateHosts([deletableId]));
  };

  const deletableHostName = hosts.find(({ id }) => id === deletableId)?.name || '';

  return (
    <Dialog
      //
      isOpen={isOpen}
      onOpenChange={handleCloseDialog}
      title={`Delete "${deletableHostName}" host`}
      onAction={handleConfirmDialog}
      actionButtonLabel="Delete"
    >
      Are you sure?
    </Dialog>
  );
};
export default HostItemDeleteDialog;
