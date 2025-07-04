import { useDispatch, useStore } from '@hooks';
import { DialogV2 } from '@uikit';
import type React from 'react';
import { deleteHostWithUpdate, closeDeleteDialog } from '@store/adcm/hosts/hostsActionsSlice';

const HostDeleteDialog: React.FC = () => {
  const dispatch = useDispatch();

  const host = useStore(({ adcm }) => adcm.hostsActions.deleteDialog.host);

  if (!host) return null;

  const handleCloseDialog = () => {
    dispatch(closeDeleteDialog());
  };

  const handleConfirmDialog = () => {
    const { id } = host ?? {};
    if (id) {
      dispatch(deleteHostWithUpdate(id));
    }
  };

  return (
    <DialogV2
      title={`Delete "${host?.name}" host`}
      onAction={handleConfirmDialog}
      onCancel={handleCloseDialog}
      actionButtonLabel="Delete"
    >
      All host information will be deleted
    </DialogV2>
  );
};
export default HostDeleteDialog;
