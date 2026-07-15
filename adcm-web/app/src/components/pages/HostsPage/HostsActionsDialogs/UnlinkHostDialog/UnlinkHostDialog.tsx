import type React from 'react';
import { useCallback } from 'react';
import { DialogV2 } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import { closeUnlinkDialog, unlinkHostsWithUpdate } from '@store/adcm/hosts/hostsActionsSlice';

const UnlinkHostDialog: React.FC = () => {
  const dispatch = useDispatch();
  const hosts = useStore(({ adcm }) => adcm.hostsActions.unlinkDialog.hosts);

  const handleCloseDialog = useCallback(() => {
    dispatch(closeUnlinkDialog());
  }, [dispatch]);

  const handleConfirmDialog = useCallback(() => {
    dispatch(unlinkHostsWithUpdate(hosts));
  }, [dispatch, hosts]);

  if (hosts.length === 0) {
    return null;
  }

  return (
    <DialogV2
      title={hosts.length === 1 ? 'Unlink host' : 'Unlink hosts'}
      onAction={handleConfirmDialog}
      onCancel={handleCloseDialog}
      actionButtonLabel="Unlink"
    >
      {hosts.length === 1
        ? 'The host will be unlinked from the cluster'
        : 'All selected hosts will be unlinked from their clusters.'}
    </DialogV2>
  );
};

export default UnlinkHostDialog;
