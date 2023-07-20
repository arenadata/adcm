import React, { useState } from 'react';
import { Button, Dialog } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import { deleteWithUpdateBundles } from '@store/adcm/bundles/bundlesSlice';

const BundlesDeleteButton: React.FC = () => {
  const dispatch = useDispatch();
  const selectedItemsIds = useStore(({ adcm }) => adcm.bundles.selectedItemsIds);

  const isSelectedSomeRows = selectedItemsIds.length > 0;
  const [isOpenDeleteConfirm, setIsOpenDeleteConfirm] = useState(false);

  const handleCloseDialog = () => {
    setIsOpenDeleteConfirm(false);
  };

  const handleConfirmDialog = () => {
    setIsOpenDeleteConfirm(false);
    dispatch(deleteWithUpdateBundles(selectedItemsIds));
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
        title="Delete bundles"
        onAction={handleConfirmDialog}
        actionButtonLabel="Delete"
      >
        All selected bundles will be deleted. Are you sure?
      </Dialog>
    </>
  );
};

export default BundlesDeleteButton;
