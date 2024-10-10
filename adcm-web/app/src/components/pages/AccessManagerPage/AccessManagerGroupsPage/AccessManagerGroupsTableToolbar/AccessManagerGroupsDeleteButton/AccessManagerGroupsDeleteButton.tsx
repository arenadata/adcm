import React, { useState } from 'react';
import { Button, Dialog } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import { deleteGroupsWithUpdate } from '@store/adcm/groups/groupsActionsSlice';

const AccessManagerGroupsDeleteButton: React.FC = () => {
  const dispatch = useDispatch();

  const selectedGroups = useStore(({ adcm }) => adcm.groupsActions.selectedGroups);
  const areSomeRowsSelected = selectedGroups.length > 0;

  const [isOpenDeleteConfirm, setIsOpenDeleteConfirm] = useState(false);

  const handleCloseDialog = () => {
    setIsOpenDeleteConfirm(false);
  };

  const handleConfirmDialog = () => {
    setIsOpenDeleteConfirm(false);
    dispatch(deleteGroupsWithUpdate(selectedGroups));
  };

  const handleClick = () => {
    setIsOpenDeleteConfirm(true);
  };

  return (
    <>
      <Button variant="secondary" disabled={!areSomeRowsSelected} onClick={handleClick}>
        Delete
      </Button>
      <Dialog
        isOpen={isOpenDeleteConfirm}
        onOpenChange={handleCloseDialog}
        title="Delete groups"
        onAction={handleConfirmDialog}
        actionButtonLabel="Delete"
      >
        All selected groups will be deleted.
      </Dialog>
    </>
  );
};

export default AccessManagerGroupsDeleteButton;
