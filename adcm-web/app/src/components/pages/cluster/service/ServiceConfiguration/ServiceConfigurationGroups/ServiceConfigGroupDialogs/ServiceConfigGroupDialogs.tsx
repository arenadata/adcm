import type React from 'react';
import { useNavigate } from 'react-router-dom';
import { useDispatch, useStore } from '@hooks';
import {
  closeCreateDialog,
  closeDeleteDialog,
  createClusterServiceConfigGroup,
  deleteClusterServiceConfigGroupWithUpdate,
} from '@store/adcm/cluster/services/configGroups/serviceConfigGroupsActionsSlice';
import type { AdcmClusterServiceConfigGroupCreateData } from '@api/adcm/clusterServiceGroupConfigs';
import ConfigGroupDeleteDialog from '@commonComponents/configGroups/ConfigGroupDeleteDialog/ConfigGroupDeleteDialog';
import ConfigGroupCreateDialog from '@commonComponents/configGroups/ConfigGroupCreateDialog/ConfigGroupCreateDialog';
import ClusterConfigGroupMappingDialog from './ServiceConfigGroupMappingDialog/ServiceConfigGroupMappingDialog';

const ServiceConfigGroupDialogs: React.FC = () => {
  const navigate = useNavigate();

  const dispatch = useDispatch();

  const clusterId = useStore((s) => s.adcm.cluster.cluster?.id);
  const serviceId = useStore((s) => s.adcm.service.service?.id);
  const isOpenCreateDialog = useStore((s) => s.adcm.serviceConfigGroupsActions.createDialog.isOpen);
  const isCreating = useStore((s) => s.adcm.serviceConfigGroupsActions.createDialog.isCreating);
  const deletableConfigGroup = useStore((s) => s.adcm.serviceConfigGroupsActions.deleteDialog.configGroup);

  const handleCloseCreateDialog = () => {
    dispatch(closeCreateDialog());
  };

  const handleCloseDeleteDialog = () => {
    dispatch(closeDeleteDialog());
  };

  const handleCreateConfigGroup = (data: AdcmClusterServiceConfigGroupCreateData) => {
    if (clusterId && serviceId) {
      dispatch(createClusterServiceConfigGroup({ clusterId, serviceId, data }))
        .unwrap()
        .then((configGroup) => {
          navigate(`/clusters/${clusterId}/services/${serviceId}/configuration-groups/${configGroup.id}`);
        });
    }
  };

  const handleDeleteConfigGroup = (configGroupId: number) => {
    if (clusterId && serviceId) {
      dispatch(deleteClusterServiceConfigGroupWithUpdate({ clusterId, serviceId, configGroupId }));
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

      <ClusterConfigGroupMappingDialog />
    </>
  );
};

export default ServiceConfigGroupDialogs;
