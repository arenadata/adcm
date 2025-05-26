import type React from 'react';
import { useState } from 'react';
import { Button, DialogV2 } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import { deleteWithUpdateBundles } from '@store/adcm/bundles/bundlesActionsSlice';

const BundlesDeleteButton: React.FC = () => {
  const dispatch = useDispatch();
  const selectedItemsIds = useStore(({ adcm }) => adcm.bundlesActions.selectedItemsIds);

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
      {isOpenDeleteConfirm && (
        <DialogV2
          title="Delete bundles"
          onAction={handleConfirmDialog}
          onCancel={handleCloseDialog}
          actionButtonLabel="Delete"
        >
          All selected bundles will be deleted.
        </DialogV2>
      )}
    </>
  );
};

export default BundlesDeleteButton;
