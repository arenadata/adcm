import React, { useState } from 'react';
import { Button, Dialog } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import { deleteGroupsWithUpdate } from '@store/adcm/groups/groupsSlice';

const AccessManagerGroupsDeleteButton: React.FC = () => {
  const dispatch = useDispatch();

  const selectedItemsIds = useStore(({ adcm }) => adcm.groups.selectedItemsIds);
  const isSelectedSomeRows = selectedItemsIds.length > 0;

  const [isOpenDeleteConfirm, setIsOpenDeleteConfirm] = useState(false);

  const handleCloseDialog = () => {
    setIsOpenDeleteConfirm(false);
  };

  const handleConfirmDialog = () => {
    setIsOpenDeleteConfirm(false);
    dispatch(deleteGroupsWithUpdate(selectedItemsIds));
  };

  const handleClick = () => {
    setIsOpenDeleteConfirm(true);
  };

  return (
    <>
      <Button variant="secondary" disabled={!isSelectedSomeRows} onClick={handleClick}>
        Delete
      </Button>
      <Dialog
        isOpen={isOpenDeleteConfirm}
        onOpenChange={handleCloseDialog}
        title="Delete groups"
        onAction={handleConfirmDialog}
        actionButtonLabel="Delete"
      >
        All selected groups will be deleted. Are you sure?
      </Dialog>
    </>
  );
};

export default AccessManagerGroupsDeleteButton;
