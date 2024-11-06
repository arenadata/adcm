import { useDispatch, useStore } from '@hooks';
import { Dialog } from '@uikit';
import React from 'react';
import { deleteHostWithUpdate, closeDeleteDialog } from '@store/adcm/hosts/hostsActionsSlice';

const HostDeleteDialog: React.FC = () => {
  const dispatch = useDispatch();

  const host = useStore(({ adcm }) => adcm.hostsActions.deleteDialog.host);

  const isOpenDeleteDialog = !!host;

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
    <Dialog
      isOpen={isOpenDeleteDialog}
      onOpenChange={handleCloseDialog}
      title={`Delete "${host?.name}" host`}
      onAction={handleConfirmDialog}
      actionButtonLabel="Delete"
    >
      All host information will be deleted
    </Dialog>
  );
};
export default HostDeleteDialog;
