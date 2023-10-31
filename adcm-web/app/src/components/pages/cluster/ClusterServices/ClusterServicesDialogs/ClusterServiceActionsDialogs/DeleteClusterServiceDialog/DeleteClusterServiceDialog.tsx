import { useDispatch, useStore } from '@hooks';
import { Dialog } from '@uikit';
import React from 'react';
import { deleteService, closeDeleteDialog } from '@store/adcm/cluster/services/servicesActionsSlice';

const DeleteClusterServiceDialog: React.FC = () => {
  const dispatch = useDispatch();

  const deletableService = useStore(
    ({
      adcm: {
        services: { services },
        servicesActions: {
          deleteDialog: { serviceId },
        },
      },
    }) => {
      if (!serviceId) return null;
      return services.find(({ id }) => id === serviceId) ?? null;
    },
  );

  const isOpenDeleteDialog = !!deletableService;

  const handleCloseDialog = () => {
    dispatch(closeDeleteDialog());
  };

  const handleConfirmDialog = () => {
    const { id } = deletableService ?? {};
    if (id && deletableService?.cluster.id) {
      dispatch(deleteService({ clusterId: deletableService?.cluster.id, serviceId: id }));
    }
  };

  return (
    <Dialog
      isOpen={isOpenDeleteDialog}
      onOpenChange={handleCloseDialog}
      title={`Delete "${deletableService?.name}" service`}
      onAction={handleConfirmDialog}
      actionButtonLabel="Delete"
    >
      All service information will be deleted
    </Dialog>
  );
};
export default DeleteClusterServiceDialog;
