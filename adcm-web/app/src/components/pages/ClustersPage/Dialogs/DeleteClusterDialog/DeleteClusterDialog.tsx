import { useDispatch, useStore } from '@hooks';
import { deleteClusterWithUpdate, closeDeleteDialog } from '@store/adcm/clusters/clustersActionsSlice';
import { Dialog } from '@uikit';
import React from 'react';

const DeleteClusterDialog: React.FC = () => {
  const dispatch = useDispatch();

  const cluster = useStore(({ adcm }) => adcm.clustersActions.deleteDialog.cluster);

  const isOpen = cluster !== null;

  const handleCloseConfirm = () => {
    dispatch(closeDeleteDialog());
  };

  const handleConfirmDialog = () => {
    if (cluster === null) return;

    dispatch(deleteClusterWithUpdate(cluster.id));
  };

  return (
    <>
      <Dialog
        //
        isOpen={isOpen}
        onOpenChange={handleCloseConfirm}
        title={`Delete "${cluster?.name}" cluster`}
        onAction={handleConfirmDialog}
        actionButtonLabel="Delete"
      >
        All cluster information will be deleted, linked hosts will be unlinked
      </Dialog>
    </>
  );
};

export default DeleteClusterDialog;
