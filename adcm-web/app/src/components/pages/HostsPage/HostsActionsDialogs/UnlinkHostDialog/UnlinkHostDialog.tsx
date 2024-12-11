import type React from 'react';
import { Dialog } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import { closeUnlinkDialog, unlinkHostWithUpdate } from '@store/adcm/hosts/hostsActionsSlice';

const UnlinkHostDialog: React.FC = () => {
  const dispatch = useDispatch();

  const host = useStore(({ adcm }) => adcm.hostsActions.unlinkDialog.host);

  const isOpenUnlink = !!host;

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

export default UnlinkHostDialog;
