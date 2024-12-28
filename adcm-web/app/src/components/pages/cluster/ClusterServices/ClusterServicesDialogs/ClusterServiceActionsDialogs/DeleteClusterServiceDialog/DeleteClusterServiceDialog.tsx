import { useDispatch, useStore } from '@hooks';
import { Dialog } from '@uikit';
import type React from 'react';
import { deleteService, closeDeleteDialog } from '@store/adcm/cluster/services/servicesActionsSlice';

const DeleteClusterServiceDialog: React.FC = () => {
  const dispatch = useDispatch();

  const clusterService = useStore(({ adcm }) => adcm.servicesActions.deleteDialog.service);

  const isOpenDeleteDialog = !!clusterService;

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
    <Dialog
      isOpen={isOpenDeleteDialog}
      onOpenChange={handleCloseDialog}
      title={`Delete "${clusterService?.displayName}" service`}
      onAction={handleConfirmDialog}
      actionButtonLabel="Delete"
    >
      All service information will be deleted
    </Dialog>
  );
};
export default DeleteClusterServiceDialog;
