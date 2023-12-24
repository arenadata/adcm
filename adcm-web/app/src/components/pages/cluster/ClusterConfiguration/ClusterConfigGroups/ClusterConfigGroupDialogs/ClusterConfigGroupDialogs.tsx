import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useDispatch, useStore } from '@hooks';
import {
  closeCreateDialog,
  closeDeleteDialog,
  createClusterConfigGroup,
  deleteClusterConfigGroupWithUpdate,
} from '@store/adcm/cluster/configGroups/clusterConfigGroupActionsSlice';
import { AdcmClusterConfigGroupCreateData } from '@api/adcm/clusterGroupConfig';
import ConfigGroupDeleteDialog from '@commonComponents/configGroups/ConfigGroupDeleteDialog/ConfigGroupDeleteDialog';
import ConfigGroupCreateDialog from '@commonComponents/configGroups/ConfigGroupCreateDialog/ConfigGroupCreateDialog';
import ClusterConfigGroupMappingDialog from './ClusterConfigGroupMappingDialog/ClusterConfigGroupMappingDialog';

const ClusterConfigGroupDialogs: React.FC = () => {
  const navigate = useNavigate();

  const dispatch = useDispatch();

  const clusterId = useStore((s) => s.adcm.cluster.cluster?.id);
  const isOpenCreateDialog = useStore((s) => s.adcm.clusterConfigGroupActions.createDialog.isOpen);
  const isCreating = useStore((s) => s.adcm.clusterConfigGroupActions.createDialog.isCreating);
  const deletableConfigGroup = useStore((s) => s.adcm.clusterConfigGroupActions.deleteDialog.configGroup);

  const handleCloseCreateDialog = () => {
    dispatch(closeCreateDialog());
  };

  const handleCloseDeleteDialog = () => {
    dispatch(closeDeleteDialog());
  };

  const handleCreateConfigGroup = (data: AdcmClusterConfigGroupCreateData) => {
    if (clusterId) {
      dispatch(createClusterConfigGroup({ clusterId, data }))
        .unwrap()
        .then((configGroup) => {
          navigate(`/clusters/${clusterId}/configuration/config-groups/${configGroup.id}`);
        });
    }
  };

  const handleDeleteConfigGroup = (configGroupId: number) => {
    if (clusterId) {
      dispatch(deleteClusterConfigGroupWithUpdate({ clusterId, configGroupId }));
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

export default ClusterConfigGroupDialogs;
