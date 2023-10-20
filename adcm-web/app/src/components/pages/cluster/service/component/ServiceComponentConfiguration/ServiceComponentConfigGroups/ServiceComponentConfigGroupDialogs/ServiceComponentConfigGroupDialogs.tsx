import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useDispatch, useStore } from '@hooks';
import {
  closeCreateDialog,
  closeDeleteDialog,
  createServiceComponentConfigGroup,
  deleteServiceComponentConfigGroupWithUpdate,
} from '@store/adcm/cluster/services/serviceComponents/serviceComponent/configGroups/serviceComponentConfigGroupsActionsSlice';
import ConfigGroupDeleteDialog from '@commonComponents/configGroups/ConfigGroupDeleteDialog/ConfigGroupDeleteDialog';
import ConfigGroupCreateDialog from '@commonComponents/configGroups/ConfigGroupCreateDialog/ConfigGroupCreateDialog';
import ServiceComponentConfigGroupMappingDialog from './ServiceComponentConfigGroupMappingDialog/ServiceComponentConfigGroupMappingDialog';
import { AdcmServiceComponentConfigGroupCreateData } from '@api/adcm/serviceComponentGroupConfigs';

const ServiceComponentConfigGroupDialogs: React.FC = () => {
  const navigate = useNavigate();

  const dispatch = useDispatch();

  const clusterId = useStore((s) => s.adcm.cluster.cluster?.id);
  const serviceId = useStore((s) => s.adcm.service.service?.id);
  const componentId = useStore((s) => s.adcm.serviceComponent.serviceComponent?.id);
  const isOpenCreateDialog = useStore((s) => s.adcm.serviceComponentConfigGroupsActions.createDialog.isOpen);
  const isCreating = useStore((s) => s.adcm.serviceComponentConfigGroupsActions.createDialog.isCreating);
  const deletableConfigGroup = useStore((s) => s.adcm.serviceComponentConfigGroupsActions.deleteDialog.configGroup);

  const handleCloseCreateDialog = () => {
    dispatch(closeCreateDialog());
  };

  const handleCloseDeleteDialog = () => {
    dispatch(closeDeleteDialog());
  };

  const handleCreateConfigGroup = (data: AdcmServiceComponentConfigGroupCreateData) => {
    if (clusterId && serviceId && componentId) {
      dispatch(createServiceComponentConfigGroup({ clusterId, serviceId, componentId, data }))
        .unwrap()
        .then((configGroup) => {
          navigate(
            `/clusters/${clusterId}/services/${serviceId}/components/${componentId}/configuration-groups/${configGroup.id}/`,
          );
        });
    }
  };

  const handleDeleteConfigGroup = (configGroupId: number) => {
    if (clusterId && serviceId && componentId) {
      dispatch(deleteServiceComponentConfigGroupWithUpdate({ clusterId, serviceId, componentId, configGroupId }));
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

      <ServiceComponentConfigGroupMappingDialog />
    </>
  );
};

export default ServiceComponentConfigGroupDialogs;
