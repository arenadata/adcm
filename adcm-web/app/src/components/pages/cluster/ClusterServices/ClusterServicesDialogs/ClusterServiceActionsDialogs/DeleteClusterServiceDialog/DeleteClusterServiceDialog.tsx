import { useDispatch, useStore } from '@hooks';
import { DialogV2 } from '@uikit';
import type React from 'react';
import { deleteService, closeDeleteDialog } from '@store/adcm/cluster/services/servicesActionsSlice';

const DeleteClusterServiceDialog: React.FC = () => {
  const dispatch = useDispatch();

  const clusterService = useStore(({ adcm }) => adcm.servicesActions.deleteDialog.service);

  if (!clusterService) return null;

  const handleCloseDialog = () => {
    dispatch(closeDeleteDialog());
  };

  const handleConfirmDialog = () => {
    const { id } = clusterService ?? {};
    if (id && clusterService?.cluster.id) {
      dispatch(deleteService({ clusterId: clusterService?.cluster.id, serviceId: id }));
    }
  };

  return (
    <DialogV2
      title={`Delete "${clusterService?.displayName}" service`}
      onAction={handleConfirmDialog}
      onCancel={handleCloseDialog}
      actionButtonLabel="Delete"
    >
      All service information will be deleted
    </DialogV2>
  );
};
export default DeleteClusterServiceDialog;
