import { useDispatch, useStore } from '@hooks';
import { unlinkClusterHost } from '@store/adcm/cluster/hosts/host/clusterHostSlice';
import { Button, DialogV2 } from '@uikit';
import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

const ClusterHostUnlinkButton = () => {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { clusterId: clusterIdFromUrl, hostId: hostIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);
  const hostId = Number(hostIdFromUrl);
  const clusterHost = useStore(({ adcm }) => adcm.clusterHost.clusterHost);

  const [isOpenUnlinkConfirm, setIsOpenUnlinkConfirm] = useState(false);

  const handleCloseDialog = () => {
    setIsOpenUnlinkConfirm(false);
  };

  const handleConfirmDialog = () => {
    setIsOpenUnlinkConfirm(false);
    dispatch(unlinkClusterHost({ clusterId, hostId }))
      .unwrap()
      .then(() => {
        navigate(`/clusters/${clusterId}/hosts`);
      });
  };

  const handleClick = () => {
    setIsOpenUnlinkConfirm(true);
  };

  return (
    <>
      <Button variant="secondary" iconLeft={'g1-unlink'} onClick={handleClick}>
        Unlink
      </Button>
      {isOpenUnlinkConfirm && (
        <DialogV2
          title="Unlink host"
          onAction={handleConfirmDialog}
          onCancel={handleCloseDialog}
          actionButtonLabel="Unlink"
        >
          The {clusterHost?.name} will be unlinked.
        </DialogV2>
      )}
    </>
  );
};

export default ClusterHostUnlinkButton;
