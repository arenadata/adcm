import React from 'react';
import { Dialog } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import { closeUnlinkDialog, unlinkHost } from '@store/adcm/hosts/hostsActionsSlice';

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
      dispatch(unlinkHost({ hostId, clusterId: cluster.id }));
    }
  };

  return (
    <>
      <Dialog
        isOpen={isOpenUnlink}
        onOpenChange={handleCloseDialog}
        title={`Unlinking for host "${unlinkableHost?.name}"`}
        onAction={handleConfirmDialog}
        actionButtonLabel="Yes"
      >
        <div>
          This unlink host "{unlinkableHost?.name}" from cluster "{unlinkableHost?.cluster?.name}".
        </div>
        Are you sure?
      </Dialog>
    </>
  );
};

export default UnlinkHostDialog;
