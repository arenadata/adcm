import type React from 'react';
import { useEffect } from 'react';
import { useDispatch, useStore } from '@hooks';
import {
  closeMappingDialog,
  getClusterServiceConfigGroupHostsCandidates,
  saveClusterServiceConfigGroupMappedHosts,
} from '@store/adcm/cluster/services/configGroups/serviceConfigGroupsActionsSlice';
import ConfigGroupMappingDialog from '@commonComponents/configGroups/ConfigGroupMappingDialog/ConfigGroupMappingDialog';

const ServiceConfigGroupMappingDialog: React.FC = () => {
  const dispatch = useDispatch();
  const clusterId = useStore((s) => s.adcm.cluster.cluster?.id);
  const serviceId = useStore((s) => s.adcm.service.service?.id);
  const configGroup = useStore((s) => s.adcm.serviceConfigGroupsActions.mappingDialog.configGroup);
  const isSaveMapping = useStore((s) => s.adcm.serviceConfigGroupsActions.mappingDialog.isSaveMapping);
  const candidatesHosts = useStore((s) => s.adcm.serviceConfigGroupsActions.relatedData.candidatesHosts);

  const handleSubmit = (configGroupId: number, mappedHostsIds: number[]) => {
    if (clusterId && serviceId) {
      dispatch(saveClusterServiceConfigGroupMappedHosts({ clusterId, serviceId, configGroupId, mappedHostsIds }));
    }
  };

  const handleClose = () => {
    dispatch(closeMappingDialog());
  };

  useEffect(() => {
    if (clusterId && serviceId && configGroup) {
      dispatch(getClusterServiceConfigGroupHostsCandidates({ clusterId, serviceId, configGroupId: configGroup.id }));
    }
  }, [clusterId, serviceId, configGroup, dispatch]);

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
export default ServiceConfigGroupMappingDialog;
