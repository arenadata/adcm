import { useStore, useDispatch } from '@hooks';
import { unlinkHostWithUpdate } from '@store/adcm/host/hostSlice';
import { Button, Dialog } from '@uikit';
import type React from 'react';
import { useState } from 'react';
import { useParams } from 'react-router-dom';

const HostUnlinkButton: React.FC = () => {
  const host = useStore(({ adcm }) => adcm.host.host);
  const dispatch = useDispatch();
  const [isOpen, setIsOpen] = useState(false);
  const { hostId: hostIdFromUrl } = useParams();
  const hostId = Number(hostIdFromUrl);

  const handleClick = () => {
    setIsOpen(true);
  };

  const handleCloseDialog = () => {
    setIsOpen(false);
  };

  const handleUnlinkHost = () => {
    setIsOpen(false);
    if (host?.cluster) {
      dispatch(unlinkHostWithUpdate({ hostId, clusterId: host.cluster.id }));
    }
  };

  return (
    <>
      <Button variant="secondary" iconLeft={'g1-unlink'} onClick={handleClick}>
        Unlink
      </Button>
      <Dialog
        isOpen={isOpen}
        onOpenChange={handleCloseDialog}
        title="Unlink host"
        onAction={handleUnlinkHost}
        actionButtonLabel="Unlink"
      >
        The host will be unlinked from the cluster
      </Dialog>
    </>
  );
};

export default HostUnlinkButton;
