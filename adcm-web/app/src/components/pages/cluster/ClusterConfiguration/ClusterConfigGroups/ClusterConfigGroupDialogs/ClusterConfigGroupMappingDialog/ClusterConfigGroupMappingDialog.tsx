import type React from 'react';
import { useEffect } from 'react';
import { useDispatch, useStore } from '@hooks';
import {
  closeMappingDialog,
  getClusterConfigGroupHostsCandidates,
  saveClusterConfigGroupMappedHosts,
} from '@store/adcm/cluster/configGroups/clusterConfigGroupActionsSlice';
import ConfigGroupMappingDialog from '@commonComponents/configGroups/ConfigGroupMappingDialog/ConfigGroupMappingDialog';

const ClusterConfigGroupMappingDialog: React.FC = () => {
  const dispatch = useDispatch();
  const clusterId = useStore((s) => s.adcm.cluster.cluster?.id);
  const configGroup = useStore((s) => s.adcm.clusterConfigGroupActions.mappingDialog.configGroup);
  const isSaveMapping = useStore((s) => s.adcm.clusterConfigGroupActions.mappingDialog.isSaveMapping);
  const candidatesHosts = useStore((s) => s.adcm.clusterConfigGroupActions.relatedData.candidatesHosts);

  const handleSubmit = (configGroupId: number, mappedHostsIds: number[]) => {
    if (clusterId) {
      dispatch(saveClusterConfigGroupMappedHosts({ clusterId, configGroupId, mappedHostsIds }));
    }
  };

  const handleClose = () => {
    dispatch(closeMappingDialog());
  };

  useEffect(() => {
    if (clusterId && configGroup) {
      dispatch(getClusterConfigGroupHostsCandidates({ clusterId, configGroupId: configGroup.id }));
    }
  }, [clusterId, configGroup, dispatch]);

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
export default ClusterConfigGroupMappingDialog;
