import React from 'react';
import { Dialog } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import { closeUnlinkDialog, unlinkHostWithUpdate } from '@store/adcm/hosts/hostsActionsSlice';

const UnlinkHostDialog: React.FC = () => {
  const dispatch = useDispatch();

  const unlinkableHost = useStore(
    ({
      adcm: {
        hosts: { hosts },
        hostsActions: {
          unlinkDialog: { id: unlinkableId },
        },
      },
    }) => {
      if (!unlinkableId) return null;
      return hosts.find(({ id }) => id === unlinkableId) ?? null;
    },
  );

  const isOpenUnlink = !!unlinkableHost;

  const handleCloseDialog = () => {
    dispatch(closeUnlinkDialog());
  };

  const handleConfirmDialog = () => {
    const { id: hostId, cluster } = unlinkableHost ?? {};
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
        actionButtonLabel="Yes"
      >
        The host will be unlinked from the cluster
      </Dialog>
    </>
  );
};

export default UnlinkHostDialog;
