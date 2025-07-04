import { useDispatch, useStore } from '@hooks';
import { deleteGroupsWithUpdate, closeDeleteDialog } from '@store/adcm/groups/groupsActionsSlice';
import { DialogV2 } from '@uikit';
import type React from 'react';

const AccessManagerGroupsDeleteDialog: React.FC = () => {
  const dispatch = useDispatch();

  const group = useStore(({ adcm }) => adcm.groupsActions.deleteDialog.group);

  if (group === null) return;

  const handleCloseConfirm = () => {
    dispatch(closeDeleteDialog());
  };

  const handleConfirmDialog = () => {
    if (group === null) return;

    dispatch(deleteGroupsWithUpdate([group.id]));
  };

  return (
    <>
      <DialogV2
        title={`Delete group "${group?.displayName}"`}
        onAction={handleConfirmDialog}
        onCancel={handleCloseConfirm}
        actionButtonLabel="Delete"
      >
        Group will be deleted.
      </DialogV2>
    </>
  );
};

export default AccessManagerGroupsDeleteDialog;
