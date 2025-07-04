import type React from 'react';
import { useDispatch, useStore } from '@hooks';
import { deleteWithUpdateBundles, closeDeleteDialog } from '@store/adcm/bundles/bundlesActionsSlice';
import { DialogV2 } from '@uikit';

const BundleItemDeleteDialog: React.FC = () => {
  const dispatch = useDispatch();

  const bundles = useStore(({ adcm }) => adcm.bundles.bundles);
  const deletableId = useStore(({ adcm }) => adcm.bundlesActions.deleteDialog.id);

  if (deletableId === null) return;

  const handleCloseDialog = () => {
    dispatch(closeDeleteDialog());
  };

  const handleConfirmDialog = () => {
    if (deletableId === null) return;

    dispatch(deleteWithUpdateBundles([deletableId]));
  };

  const deletableBundleName = bundles.find(({ id }) => id === deletableId)?.name || '';

  return (
    <DialogV2
      //
      title={`Delete "${deletableBundleName}" bundle`}
      onAction={handleConfirmDialog}
      onCancel={handleCloseDialog}
      actionButtonLabel="Delete"
    >
      All bundle information will be deleted
    </DialogV2>
  );
};
export default BundleItemDeleteDialog;
