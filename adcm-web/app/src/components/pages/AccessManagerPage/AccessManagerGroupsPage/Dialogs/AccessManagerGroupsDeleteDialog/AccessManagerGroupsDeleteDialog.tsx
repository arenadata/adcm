import { useDispatch, useStore } from '@hooks';
import { deleteGroupsWithUpdate, closeDeleteDialog } from '@store/adcm/groups/groupActionsSlice';
import { Dialog } from '@uikit';
import React from 'react';

const AccessManagerGroupsDeleteDialog: React.FC = () => {
  const dispatch = useDispatch();

  const deletableId = useStore(({ adcm }) => adcm.groupsActions.deleteDialog.id);
  const groups = useStore(({ adcm }) => adcm.groups.groups);

  const isOpen = deletableId !== null;
  const name = groups.find(({ id }) => id === deletableId)?.displayName;

  const handleCloseConfirm = () => {
    dispatch(closeDeleteDialog());
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
