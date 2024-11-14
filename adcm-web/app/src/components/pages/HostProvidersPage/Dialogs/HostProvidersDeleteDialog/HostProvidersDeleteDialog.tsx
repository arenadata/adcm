import Dialog from '@uikit/Dialog/Dialog';
import { useDispatch, useStore } from '@hooks';
import { deleteHostProvider, closeDeleteDialog } from '@store/adcm/hostProviders/hostProvidersActionsSlice';

const HostProvidersDeleteDialog = () => {
  const dispatch = useDispatch();

  const hostProvider = useStore(({ adcm }) => adcm.hostProvidersActions.deleteDialog.hostprovider);

  const isOpenDeleteDialog = !!hostProvider;

  const handleCloseDialog = () => {
    dispatch(closeDeleteDialog());
  };

  const handleConfirmDialog = () => {
    if (!hostProvider?.id) return;

    dispatch(deleteHostProvider(hostProvider.id));
  };

  const hostProviderName = hostProvider?.name;

  return (
    <Dialog
      //
      isOpen={isOpenDeleteDialog}
      onOpenChange={handleCloseDialog}
      title={`Delete "${hostProviderName}" hostprovider`}
      onAction={handleConfirmDialog}
      actionButtonLabel="Delete"
    >
      All hostprovider information will be deleted
    </Dialog>
  );
};
export default HostProvidersDeleteDialog;
