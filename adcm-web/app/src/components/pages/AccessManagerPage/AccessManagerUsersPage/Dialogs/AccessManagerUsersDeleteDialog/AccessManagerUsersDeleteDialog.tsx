import { useDispatch, useStore } from '@hooks';
import { deleteUserWithUpdate, setDeletableId } from '@store/adcm/users/usersSlice';
import { Dialog } from '@uikit';
import React from 'react';

const AccessManagerUsersDeleteDialog: React.FC = () => {
  const dispatch = useDispatch();

  const deletableId = useStore(({ adcm }) => adcm.users.itemsForActions.deletableId);
  const users = useStore(({ adcm }) => adcm.users.users);

  const isOpen = deletableId !== null;
  const userName = users.find(({ id }) => id === deletableId)?.username;

  const handleCloseConfirm = () => {
    dispatch(setDeletableId(null));
  };

  const handleConfirmDialog = () => {
    if (deletableId === null) return;

    dispatch(deleteUserWithUpdate(deletableId));
  };

  return (
    <>
      <Dialog
        isOpen={isOpen}
        onOpenChange={handleCloseConfirm}
        title={`Delete user "${userName}"`}
        onAction={handleConfirmDialog}
        actionButtonLabel="Delete"
      >
        User will be deleted. Are you sure?
      </Dialog>
    </>
  );
};

export default AccessManagerUsersDeleteDialog;
