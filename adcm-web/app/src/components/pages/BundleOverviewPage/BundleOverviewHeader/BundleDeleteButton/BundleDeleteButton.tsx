import { useDispatch, useStore } from '@hooks';
import { deleteBundle } from '@store/adcm/bundle/bundleSlice';
import { Button, Dialog } from '@uikit';
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

const BundleDeleteButton = () => {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const bundle = useStore(({ adcm }) => adcm.bundle.bundle);

  const [isOpenDeleteConfirm, setIsOpenDeleteConfirm] = useState(false);

  const handleCloseDialog = () => {
    setIsOpenDeleteConfirm(false);
  };

  const handleConfirmDialog = () => {
    if (bundle) {
      setIsOpenDeleteConfirm(false);
      dispatch(deleteBundle(bundle.id))
        .unwrap()
        .then(() => {
          navigate('/bundles/');
        });
    }
  };

  const handleClick = () => {
    setIsOpenDeleteConfirm(true);
  };

  return (
    <>
      <Button variant="secondary" iconLeft={'g1-delete'} onClick={handleClick}>
        Delete
      </Button>
      <Dialog
        isOpen={isOpenDeleteConfirm}
        onOpenChange={handleCloseDialog}
        title="Delete bundle"
        onAction={handleConfirmDialog}
        actionButtonLabel="Delete"
      >
        The "{bundle?.name}" bundle will be deleted.
      </Dialog>
    </>
  );
};

export default BundleDeleteButton;
