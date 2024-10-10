import { useDispatch, useStore } from '@hooks';
import { deleteGroupsWithUpdate, closeDeleteDialog } from '@store/adcm/groups/groupsActionsSlice';
import { Dialog } from '@uikit';
import React from 'react';

const AccessManagerGroupsDeleteDialog: React.FC = () => {
  const dispatch = useDispatch();

  const group = useStore(({ adcm }) => adcm.groupsActions.deleteDialog.group);

  const isOpen = group !== null;

  const handleCloseConfirm = () => {
    dispatch(closeDeleteDialog());
  };

  const handleConfirmDialog = () => {
    if (group === null) return;

    dispatch(deleteGroupsWithUpdate([group.id]));
  };

  return (
    <>
      <Dialog
        isOpen={isOpen}
        onOpenChange={handleCloseConfirm}
        title={`Delete group "${group?.displayName}"`}
        onAction={handleConfirmDialog}
        actionButtonLabel="Delete"
      >
        Group will be deleted.
      </Dialog>
    </>
  );
};

export default AccessManagerGroupsDeleteDialog;
