import React from 'react';
import { Dialog } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import { closeUnlinkDialog, unlinkHostWithUpdate } from '@store/adcm/cluster/hosts/hostsActionsSlice';

const UnlinkClusterHostsDialog: React.FC = () => {
  const dispatch = useDispatch();

  const clusterHost = useStore(({ adcm }) => adcm.clusterHostsActions.unlinkDialog.clusterHost);

  const isOpenUnlink = !!clusterHost;

  const handleCloseDialog = () => {
    dispatch(closeUnlinkDialog());
  };

  const handleConfirmDialog = () => {
    const { id: hostId, cluster } = clusterHost ?? {};
    if (hostId && cluster?.id) {
      dispatch(unlinkHostWithUpdate({ hostId, clusterId: cluster.id }));
    }
  };

  return (
    <>
      <Dialog
        isOpen={isOpenUnlink}
        onOpenChange={handleCloseDialog}
        title="Unlink host"
        onAction={handleConfirmDialog}
        actionButtonLabel="Unlink"
      >
        The host will be unlinked from the cluster
      </Dialog>
    </>
  );
};

export default UnlinkClusterHostsDialog;
