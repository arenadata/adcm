import React from 'react';
import { useDispatch, useStore } from '@hooks';
import { useNavigate } from 'react-router-dom';
import ConfigGroupCreateDialog from '@commonComponents/configGroups/ConfigGroupCreateDialog/ConfigGroupCreateDialog';
import ConfigGroupDeleteDialog from '@commonComponents/configGroups/ConfigGroupDeleteDialog/ConfigGroupDeleteDialog';
import {
  closeCreateDialog,
  closeDeleteDialog,
  createHostProviderConfigGroup,
  deleteHostProviderConfigGroupWithUpdate,
} from '@store/adcm/hostProvider/configurationGroups/hostProviderConfigGroupActionsSlice';
import { AdcmHostProviderConfigGroupCreateData } from '@api/adcm/hostProviderGroupConfig';

const HostProviderConfigGroupDialogs: React.FC = () => {
  const navigate = useNavigate();

  const dispatch = useDispatch();

  const hostProviderId = useStore((s) => s.adcm.hostProvider.hostProvider?.id);
  const isOpenCreateDialog = useStore((s) => s.adcm.hostProviderConfigGroupActions.createDialog.isOpen);
  const isCreating = useStore((s) => s.adcm.hostProviderConfigGroupActions.createDialog.isCreating);
  const deletableConfigGroup = useStore((s) => s.adcm.hostProviderConfigGroupActions.deleteDialog.configGroup);

  const handleCloseCreateDialog = () => {
    dispatch(closeCreateDialog());
  };

  const handleCloseDeleteDialog = () => {
    dispatch(closeDeleteDialog());
  };

  const handleCreateConfigGroup = (data: AdcmHostProviderConfigGroupCreateData) => {
    if (hostProviderId) {
      dispatch(createHostProviderConfigGroup({ hostProviderId, data }))
        .unwrap()
        .then((configGroup) => {
          navigate(`/hostproviders/${hostProviderId}/configuration-groups/${configGroup.id}/`);
        });
    }
  };

  const handleDeleteConfigGroup = (configGroupId: number) => {
    if (hostProviderId) {
      dispatch(deleteHostProviderConfigGroupWithUpdate({ hostProviderId, configGroupId }));
    }
  };

  return (
    <>
      <ConfigGroupCreateDialog
        isCreating={isCreating}
        isOpen={isOpenCreateDialog}
        onClose={handleCloseCreateDialog}
        onSubmit={handleCreateConfigGroup}
      />

      <ConfigGroupDeleteDialog
        configGroup={deletableConfigGroup}
        onSubmit={handleDeleteConfigGroup}
        onClose={handleCloseDeleteDialog}
      />
    </>
  );
};

export default HostProviderConfigGroupDialogs;
