import { useDispatch, useStore } from '@hooks';
import { deleteClusterWithUpdate, openClusterDeleteDialog } from '@store/adcm/clusters/clustersActionsSlice';
import { Dialog } from '@uikit';
import React from 'react';

const DeleteClusterDialog: React.FC = () => {
  const dispatch = useDispatch();

  const deletableId = useStore(({ adcm }) => adcm.clustersActions.deletableId.id);
  const clusters = useStore(({ adcm }) => adcm.clusters.clusters);

  const isOpen = deletableId !== null;
  const clusterName = clusters.find(({ id }) => id === deletableId)?.name;

  const handleCloseConfirm = () => {
    dispatch(openClusterDeleteDialog(null));
  };

  const handleConfirmDialog = () => {
    if (deletableId === null) return;

    dispatch(deleteClusterWithUpdate(deletableId));
  };

  return (
    <>
      <Dialog
        //
        isOpen={isOpen}
        onOpenChange={handleCloseConfirm}
        title={`Delete "${clusterName}" cluster`}
        onAction={handleConfirmDialog}
        actionButtonLabel="Delete"
      >
        All cluster information will be deleted, linked hosts will be unlinked
      </Dialog>
    </>
  );
};

export default DeleteClusterDialog;
