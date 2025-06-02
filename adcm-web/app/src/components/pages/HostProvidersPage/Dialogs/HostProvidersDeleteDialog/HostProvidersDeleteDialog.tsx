import { useDispatch, useStore } from '@hooks';
import { deleteHostProvider, closeDeleteDialog } from '@store/adcm/hostProviders/hostProvidersActionsSlice';
import { DialogV2 } from '@uikit';

const HostProvidersDeleteDialog = () => {
  const dispatch = useDispatch();

  const hostProvider = useStore(({ adcm }) => adcm.hostProvidersActions.deleteDialog.hostprovider);

  if (!hostProvider) return null;

  const handleCloseDialog = () => {
    dispatch(closeDeleteDialog());
  };

  const handleConfirmDialog = () => {
    if (!hostProvider?.id) return;

    dispatch(deleteHostProvider(hostProvider.id));
  };

  const hostProviderName = hostProvider?.name;

  return (
    <DialogV2
      //
      title={`Delete "${hostProviderName}" hostprovider`}
      onAction={handleConfirmDialog}
      onCancel={handleCloseDialog}
      actionButtonLabel="Delete"
    >
      All hostprovider information will be deleted
    </DialogV2>
  );
};
export default HostProvidersDeleteDialog;
