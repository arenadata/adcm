import { useDispatch, useStore } from '@hooks';
import { deleteGroupsWithUpdate, setDeletableId } from '@store/adcm/groups/groupsSlice';
import { Dialog } from '@uikit';
import React from 'react';

const AccessManagerGroupsDeleteDialog: React.FC = () => {
  const dispatch = useDispatch();

  const deletableId = useStore(({ adcm }) => adcm.groups.itemsForActions.deletableId);
  const groups = useStore(({ adcm }) => adcm.groups.groups);

  const isOpen = deletableId !== null;
  const name = groups.find(({ id }) => id === deletableId)?.name;

  const handleCloseConfirm = () => {
    dispatch(setDeletableId(null));
  };

  const handleConfirmDialog = () => {
    if (deletableId === null) return;

    dispatch(deleteGroupsWithUpdate([deletableId]));
  };

  return (
    <>
      <Dialog
        isOpen={isOpen}
        onOpenChange={handleCloseConfirm}
        title={`Delete group "${name}"`}
        onAction={handleConfirmDialog}
        actionButtonLabel="Delete"
      >
        Group will be deleted.
      </Dialog>
    </>
  );
};

export default AccessManagerGroupsDeleteDialog;
