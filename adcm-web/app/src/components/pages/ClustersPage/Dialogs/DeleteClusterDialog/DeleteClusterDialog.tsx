import { useDispatch, useStore } from '@hooks';
import { deleteClusterWithUpdate, closeDeleteDialog } from '@store/adcm/clusters/clustersActionsSlice';
import { DialogV2 } from '@uikit';
import type React from 'react';

const DeleteClusterDialog: React.FC = () => {
  const dispatch = useDispatch();

  const cluster = useStore(({ adcm }) => adcm.clustersActions.deleteDialog.cluster);

  if (!cluster) return null;

  const handleCloseConfirm = () => {
    dispatch(closeDeleteDialog());
  };

  const handleConfirmDialog = () => {
    if (cluster === null) return;

    dispatch(deleteClusterWithUpdate(cluster.id));
  };

  return (
    <DialogV2
      title={`Delete "${cluster?.name}" cluster`}
      onAction={handleConfirmDialog}
      onCancel={handleCloseConfirm}
      actionButtonLabel="Delete"
    >
      All cluster information will be deleted, linked hosts will be unlinked
    </DialogV2>
  );
};

export default DeleteClusterDialog;
