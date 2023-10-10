import React from 'react';
import Dialog from '@uikit/Dialog/Dialog';
import { useDispatch, useStore } from '@hooks';
import { deleteWithUpdateBundles, setDeletableId } from '@store/adcm/bundles/bundlesSlice';

const BundleItemDeleteDialog: React.FC = () => {
  const dispatch = useDispatch();

  const bundles = useStore(({ adcm }) => adcm.bundles.bundles);
  const deletableId = useStore(({ adcm }) => adcm.bundles.itemsForActions.deletableId);

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
      All bundle information will be deleted
    </Dialog>
  );
};
export default BundleItemDeleteDialog;
