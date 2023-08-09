import React, { useState } from 'react';
import { Button, Dialog } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import { deleteUsersWithUpdate } from '@store/adcm/users/usersActionsSlice';

const AccessManagerUsersDeleteButton: React.FC = () => {
  const dispatch = useDispatch();

  const selectedItemsIds = useStore(({ adcm }) => adcm.usersActions.selectedItemsIds);
  const isSelectedSomeRows = selectedItemsIds.length > 0;

  const [isOpenDeleteConfirm, setIsOpenDeleteConfirm] = useState(false);

  const handleCloseDialog = () => {
    setIsOpenDeleteConfirm(false);
  };

  const handleConfirmDialog = () => {
    setIsOpenDeleteConfirm(false);
    dispatch(deleteUsersWithUpdate(selectedItemsIds));
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
        title="Delete users"
        onAction={handleConfirmDialog}
        actionButtonLabel="Delete"
      >
        All selected users will be deleted. Are you sure?
      </Dialog>
    </>
  );
};

export default AccessManagerUsersDeleteButton;
