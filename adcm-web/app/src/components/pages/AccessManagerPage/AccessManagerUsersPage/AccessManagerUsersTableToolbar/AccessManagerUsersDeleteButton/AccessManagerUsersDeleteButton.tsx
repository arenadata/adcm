import type React from 'react';
import { useState } from 'react';
import { Button, Dialog } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import { deleteUsersWithUpdate } from '@store/adcm/users/usersActionsSlice';

const AccessManagerUsersDeleteButton: React.FC = () => {
  const dispatch = useDispatch();

  const selectedUsersIds = useStore(({ adcm }) => adcm.usersActions.selectedUsersIds);
  const areSomeRowsSelected = selectedUsersIds.length > 0;

  const [isOpenDeleteConfirm, setIsOpenDeleteConfirm] = useState(false);

  const handleCloseDialog = () => {
    setIsOpenDeleteConfirm(false);
  };

  const handleConfirmDialog = () => {
    setIsOpenDeleteConfirm(false);
    dispatch(deleteUsersWithUpdate(selectedUsersIds));
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
        title="Delete users"
        onAction={handleConfirmDialog}
        actionButtonLabel="Delete"
      >
        All selected users will be deleted.
      </Dialog>
    </>
  );
};

export default AccessManagerUsersDeleteButton;
