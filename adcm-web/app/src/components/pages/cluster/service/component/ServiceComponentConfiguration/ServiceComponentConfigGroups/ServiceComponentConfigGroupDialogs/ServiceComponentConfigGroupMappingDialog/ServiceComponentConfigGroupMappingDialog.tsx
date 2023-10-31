import React, { useEffect } from 'react';
import { useDispatch, useStore } from '@hooks';
import {
  closeMappingDialog,
  getServiceComponentConfigGroupHostsCandidates,
  saveServiceComponentConfigGroupMappedHosts,
} from '@store/adcm/cluster/services/serviceComponents/serviceComponent/configGroups/serviceComponentConfigGroupsActionsSlice';
import ConfigGroupMappingDialog from '@commonComponents/configGroups/ConfigGroupMappingDialog/ConfigGroupMappingDialog';

const ServiceComponentConfigGroupMappingDialog: React.FC = () => {
  const dispatch = useDispatch();
  const clusterId = useStore((s) => s.adcm.cluster.cluster?.id);
  const serviceId = useStore((s) => s.adcm.service.service?.id);
  const componentId = useStore((s) => s.adcm.serviceComponent.serviceComponent?.id);
  const configGroup = useStore((s) => s.adcm.serviceComponentConfigGroupsActions.mappingDialog.configGroup);
  const isSaveMapping = useStore((s) => s.adcm.serviceComponentConfigGroupsActions.mappingDialog.isSaveMapping);
  const candidatesHosts = useStore((s) => s.adcm.serviceComponentConfigGroupsActions.relatedData.candidatesHosts);

  const handleSubmit = (configGroupId: number, mappedHostsIds: number[]) => {
    if (clusterId && serviceId && componentId) {
      dispatch(
        saveServiceComponentConfigGroupMappedHosts({
          clusterId,
          serviceId,
          componentId,
          configGroupId,
          mappedHostsIds,
        }),
      );
    }
  };

  const handleClose = () => {
    dispatch(closeMappingDialog());
  };

  useEffect(() => {
    if (clusterId && serviceId && componentId && configGroup) {
      dispatch(
        getServiceComponentConfigGroupHostsCandidates({
          clusterId,
          serviceId,
          componentId,
          configGroupId: configGroup.id,
        }),
      );
    }
  }, [clusterId, serviceId, componentId, configGroup, dispatch]);

  console.info('configGroup', configGroup);

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
export default ServiceComponentConfigGroupMappingDialog;
