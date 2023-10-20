import { useDispatch, useStore } from '@hooks';
import { Dialog } from '@uikit';
import React from 'react';
import { deleteHostWithUpdate, closeDeleteDialog } from '@store/adcm/hosts/hostsActionsSlice';

const HostDeleteDialog: React.FC = () => {
  const dispatch = useDispatch();

  const deletableHost = useStore(
    ({
      adcm: {
        hosts: { hosts },
        hostsActions: {
          deleteDialog: { id: deletableId },
        },
      },
    }) => {
      if (!deletableId) return null;
      return hosts.find(({ id }) => id === deletableId) ?? null;
    },
  );

  const isOpenDeleteDialog = !!deletableHost;

  const handleCloseDialog = () => {
    dispatch(closeDeleteDialog());
  };

  const handleConfirmDialog = () => {
    const { id } = deletableHost ?? {};
    if (id) {
      dispatch(deleteHostWithUpdate(id));
    }
  };

  return (
    <Dialog
      isOpen={isOpenDeleteDialog}
      onOpenChange={handleCloseDialog}
      title={`Delete "${deletableHost?.name}" host`}
      onAction={handleConfirmDialog}
      actionButtonLabel="Delete"
    >
      All host information will be deleted
    </Dialog>
  );
};
export default HostDeleteDialog;
