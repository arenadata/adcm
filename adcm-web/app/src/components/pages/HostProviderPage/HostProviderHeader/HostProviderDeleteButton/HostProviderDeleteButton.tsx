import type React from 'react';
import { useState } from 'react';
import { Button, Dialog } from '@uikit';
import { useNavigate } from 'react-router-dom';
import { useDispatch, useStore } from '@hooks';
import { deleteHostProvider } from '@store/adcm/hostProviders/hostProvidersActionsSlice';

const HostProviderDeleteButton: React.FC = () => {
  const dispatch = useDispatch();
  const navigate = useNavigate();

  const hostProvider = useStore(({ adcm }) => adcm.hostProvider.hostProvider);
  const hostProviderId = hostProvider?.id;

  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);

  const handleCloseDialog = () => {
    setIsDeleteDialogOpen(false);
  };

  const handleConfirmDialog = () => {
    setIsDeleteDialogOpen(false);
    if (hostProviderId) {
      dispatch(deleteHostProvider(hostProviderId))
        .unwrap()
        .then(() => {
          navigate('/hostproviders');
        });
    }
  };

  const handleClick = () => {
    setIsDeleteDialogOpen(true);
  };

  return (
    <>
      <Button iconLeft="g1-delete" variant="secondary" onClick={handleClick}>
        Delete
      </Button>
      <Dialog
        isOpen={isDeleteDialogOpen}
        onOpenChange={handleCloseDialog}
        title={`Delete ${hostProvider?.name} hostprovider`}
        onAction={handleConfirmDialog}
        actionButtonLabel="Delete"
      >
        All hostprovider information will be deleted
      </Dialog>
    </>
  );
};
export default HostProviderDeleteButton;
