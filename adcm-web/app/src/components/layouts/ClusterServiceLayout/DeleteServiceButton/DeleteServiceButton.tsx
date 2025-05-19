import type React from 'react';
import { useState } from 'react';
import { Button, DialogV2 } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import { deleteService } from '@store/adcm/services/serviceSlice';
import { useNavigate } from 'react-router-dom';

const DeleteServiceButton: React.FC = () => {
  const dispatch = useDispatch();
  const navigate = useNavigate();

  const service = useStore(({ adcm }) => adcm.service.service);
  const clusterId = service?.cluster.id;

  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);

  const handleCloseDialog = () => {
    setIsDeleteDialogOpen(false);
  };

  const handleConfirmDialog = () => {
    setIsDeleteDialogOpen(false);
    if (service) {
      dispatch(
        deleteService({
          clusterId: service.cluster.id,
          serviceId: service.id,
        }),
      )
        .unwrap()
        .then(() => {
          navigate(`/clusters/${clusterId}`);
        });
    }
  };

  const handleClick = () => {
    setIsDeleteDialogOpen(true);
  };

  return (
    <>
      <Button iconLeft="g1-delete" variant="secondary" onClick={handleClick}>
        Delete
      </Button>
      {isDeleteDialogOpen && (
        <DialogV2
          title={`Delete ${service?.displayName} service`}
          onAction={handleConfirmDialog}
          onCancel={handleCloseDialog}
          actionButtonLabel="Delete"
        >
          All service information will be deleted
        </DialogV2>
      )}
    </>
  );
};
export default DeleteServiceButton;
