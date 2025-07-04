import { useStore, useDispatch } from '@hooks';
import { unlinkHostWithUpdate } from '@store/adcm/host/hostSlice';
import { Button, DialogV2 } from '@uikit';
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
      {isOpen && (
        <DialogV2
          title="Unlink host"
          onAction={handleUnlinkHost}
          onCancel={handleCloseDialog}
          actionButtonLabel="Unlink"
        >
          The host will be unlinked from the cluster
        </DialogV2>
      )}
    </>
  );
};

export default HostUnlinkButton;
