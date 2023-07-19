import React from 'react';
import Dialog from '@uikit/Dialog/Dialog';
import { useDispatch, useStore } from '@hooks';
import { deleteWithUpdateBundles } from '@store/adcm/bundles/bundlesSlice';
import { setDeletableId } from '@store/adcm/bundles/bundlesTableSlice';

const BundleItemDeleteDialog: React.FC = () => {
  const dispatch = useDispatch();

  const bundles = useStore(({ adcm }) => adcm.bundles.bundles);
  const deletableId = useStore(({ adcm }) => adcm.bundlesTable.itemsForActions.deletableId);

  const isOpen = deletableId !== null;

  const handleCloseDialog = () => {
    dispatch(setDeletableId(null));
  };

  const handleConfirmDialog = () => {
    if (deletableId === null) return;

    dispatch(deleteWithUpdateBundles([deletableId]));
  };

  const deletableBundleName = bundles.find(({ id }) => id === deletableId)?.name || '';

  return (
    <Dialog
      //
      isOpen={isOpen}
      onOpenChange={handleCloseDialog}
      title={`Delete "${deletableBundleName}" bundle`}
      onAction={handleConfirmDialog}
      actionButtonLabel="Delete"
    >
      Are you sure?
    </Dialog>
  );
};
export default BundleItemDeleteDialog;
