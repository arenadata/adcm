import type React from 'react';
import { useCallback } from 'react';
import { useDispatch, useStore } from '@hooks';
import { DialogV2 } from '@uikit';
import { closeDeleteDialog, deleteHostsWithUpdate } from '@store/adcm/hosts/hostsActionsSlice';

const HostDeleteDialog: React.FC = () => {
  const dispatch = useDispatch();
  const hosts = useStore(({ adcm }) => adcm.hostsActions.deleteDialog.hosts);

  const handleCloseDialog = useCallback(() => {
    dispatch(closeDeleteDialog());
  }, [dispatch]);

  const handleConfirmDialog = useCallback(() => {
    dispatch(deleteHostsWithUpdate(hosts.map(({ id }) => id)));
  }, [dispatch, hosts]);

  if (hosts.length === 0) {
    return null;
  }

  return (
    <DialogV2
      title={hosts.length === 1 ? `Delete "${hosts[0].name}" host` : 'Delete hosts'}
      onAction={handleConfirmDialog}
      onCancel={handleCloseDialog}
      actionButtonLabel="Delete"
    >
      {hosts.length === 1 ? 'All host information will be deleted' : 'All selected hosts will be deleted.'}
    </DialogV2>
  );
};

export default HostDeleteDialog;
