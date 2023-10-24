import React, { useEffect } from 'react';
import { useDispatch, useStore } from '@hooks';
import ConfigGroupMappingDialog from '@commonComponents/configGroups/ConfigGroupMappingDialog/ConfigGroupMappingDialog';
import {
  closeMappingDialog,
  getHostProviderConfigGroupHostsCandidates,
  saveHostProviderConfigGroupMappedHosts,
} from '@store/adcm/hostProvider/configurationGroups/hostProviderConfigGroupActionsSlice';

const HostProviderConfigGroupMappingDialog: React.FC = () => {
  const dispatch = useDispatch();
  const hostProviderId = useStore((s) => s.adcm.hostProvider.hostProvider?.id);
  const configGroup = useStore((s) => s.adcm.hostProviderConfigGroupActions.mappingDialog.configGroup);
  const isSaveMapping = useStore((s) => s.adcm.hostProviderConfigGroupActions.mappingDialog.isSaveMapping);
  const candidatesHosts = useStore((s) => s.adcm.hostProviderConfigGroupActions.relatedData.candidatesHosts);

  const handleSubmit = (configGroupId: number, mappedHostsIds: number[]) => {
    if (hostProviderId) {
      dispatch(saveHostProviderConfigGroupMappedHosts({ hostProviderId, configGroupId, mappedHostsIds }));
    }
  };

  const handleClose = () => {
    dispatch(closeMappingDialog());
  };

  useEffect(() => {
    if (hostProviderId && configGroup) {
      dispatch(getHostProviderConfigGroupHostsCandidates({ hostProviderId, configGroupId: configGroup.id }));
    }
  }, [hostProviderId, configGroup, dispatch]);

  return (
    <ConfigGroupMappingDialog
      configGroup={configGroup}
      onSubmit={handleSubmit}
      onClose={handleClose}
      candidatesHosts={candidatesHosts}
      isSaveMapping={isSaveMapping}
    />
  );
};
export default HostProviderConfigGroupMappingDialog;
