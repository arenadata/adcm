import type React from 'react';
import { DialogV2 } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import { closeUnlinkDialog, unlinkHostWithUpdate } from '@store/adcm/hosts/hostsActionsSlice';

const UnlinkHostDialog: React.FC = () => {
  const dispatch = useDispatch();

  const host = useStore(({ adcm }) => adcm.hostsActions.unlinkDialog.host);

  if (!host) return null;

  const handleCloseDialog = () => {
    dispatch(closeUnlinkDialog());
  };

  const handleConfirmDialog = () => {
    const { id: hostId, cluster } = host ?? {};
    if (hostId && cluster?.id) {
      dispatch(unlinkHostWithUpdate({ hostId, clusterId: cluster.id }));
    }
  };

  return (
    <DialogV2
      title="Unlink host"
      onAction={handleConfirmDialog}
      onCancel={handleCloseDialog}
      actionButtonLabel="Unlink"
    >
      The host will be unlinked from the cluster
    </DialogV2>
  );
};

export default UnlinkHostDialog;
