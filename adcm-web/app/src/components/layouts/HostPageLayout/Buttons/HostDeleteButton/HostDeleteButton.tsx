import { useDispatch } from '@hooks';
import { deleteHost } from '@store/adcm/hosts/hostsActionsSlice';
import { Button, DialogV2 } from '@uikit';
import type React from 'react';
import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

const HostDeleteButton: React.FC = () => {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);
  const { hostId: hostIdFromUrl } = useParams();
  const hostId = Number(hostIdFromUrl);

  const handleClick = () => {
    setIsOpen(true);
  };

  const handleCloseDialog = () => {
    setIsOpen(false);
  };

  const handleDeleteHost = () => {
    setIsOpen(false);
    dispatch(deleteHost(hostId))
      .unwrap()
      .then(() => navigate('/hosts'));
  };

  return (
    <>
      <Button variant="secondary" iconLeft={'g1-delete'} onClick={handleClick}>
        Delete
      </Button>
      {isOpen && (
        <DialogV2
          title="Delete host"
          onAction={handleDeleteHost}
          onCancel={handleCloseDialog}
          actionButtonLabel="Delete"
        >
          The host will be deleted
        </DialogV2>
      )}
    </>
  );
};

export default HostDeleteButton;
