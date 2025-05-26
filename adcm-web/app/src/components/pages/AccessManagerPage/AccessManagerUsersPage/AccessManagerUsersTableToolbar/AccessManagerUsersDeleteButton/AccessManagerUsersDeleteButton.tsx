import type React from 'react';
import { useState } from 'react';
import { Button, DialogV2 } from '@uikit';
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
      {isOpenDeleteConfirm && (
        <DialogV2
          title="Delete users"
          onAction={handleConfirmDialog}
          onCancel={handleCloseDialog}
          actionButtonLabel="Delete"
        >
          All selected users will be deleted.
        </DialogV2>
      )}
    </>
  );
};

export default AccessManagerUsersDeleteButton;
