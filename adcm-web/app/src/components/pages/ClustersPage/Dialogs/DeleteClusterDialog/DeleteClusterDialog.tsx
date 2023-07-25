import { useDispatch, useStore } from '@hooks';
import { deleteClusterWithUpdate, setDeletableId } from '@store/adcm/clusters/clustersSlice';
import { Dialog } from '@uikit';
import React from 'react';

const DeleteClusterDialog: React.FC = () => {
  const dispatch = useDispatch();

  const deletableId = useStore(({ adcm }) => adcm.clusters.itemsForActions.deletableId);
  const clusters = useStore(({ adcm }) => adcm.clusters.clusters);

  const isOpen = deletableId !== null;
  const clusterName = clusters.find(({ id }) => id === deletableId)?.name;

  const handleCloseConfirm = () => {
    dispatch(setDeletableId(null));
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
