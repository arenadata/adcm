import React from 'react';
import { useDispatch, useStore } from '@hooks';
import ConfigGroupsHeader from '@commonComponents/configGroups/ConfigGroupsHeader/ConfigGroupsHeader';
import ConfigGroupsTable from '@commonComponents/configGroups/ConfigGroupsTable/ConfigGroupsTable';
import { useRequestClusterConfigGroups } from './useRequestClusterConfigGroups';
import ClusterConfigGroupTableFooter from './ClusterConfigGroupTableFooter/ClusterConfigGroupTableFooter';
import { SortParams } from '@uikit/types/list.types';
import { setSortParams } from '@store/adcm/cluster/configGroups/clusterConfigGroupsTableSlice';
import ClusterConfigGroupDialogs from './ClusterConfigGroupDialogs/ClusterConfigGroupDialogs';
import {
  openCreateDialog,
  openDeleteDialog,
  openMappingDialog,
} from '@store/adcm/cluster/configGroups/clusterConfigGroupActionsSlice';
import { useParams } from 'react-router-dom';
import { AdcmConfigGroup } from '@models/adcm';

const ClusterConfigGroups: React.FC = () => {
  const dispatch = useDispatch();

  const { clusterId: clusterIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);

  const { clusterConfigGroups, isLoading } = useStore((s) => s.adcm.clusterConfigGroups);
  const sortParams = useStore((s) => s.adcm.clusterConfigGroupsTable.sortParams);
  useRequestClusterConfigGroups();

  const handleSorting = (sortParams: SortParams) => {
    dispatch(setSortParams(sortParams));
  };

  const handleCreateConfigGroup = () => {
    dispatch(openCreateDialog());
  };
  const handleDeleteConfigGroup = (configGroup: AdcmConfigGroup) => {
    dispatch(openDeleteDialog(configGroup));
  };

  const handleMappingConfigGroup = (configGroup: AdcmConfigGroup) => {
    dispatch(openMappingDialog(configGroup));
  };

  return (
    <div>
      <ConfigGroupsHeader onCreate={handleCreateConfigGroup} />
      <ConfigGroupsTable
        configGroups={clusterConfigGroups}
        isLoading={isLoading}
        sortParams={sortParams}
        onSorting={handleSorting}
        onMapping={handleMappingConfigGroup}
        editUrlPattern={`/clusters/${clusterId}/configuration/config-groups/:configGroupId`}
        onDelete={handleDeleteConfigGroup}
      />
      <ClusterConfigGroupTableFooter />

      <ClusterConfigGroupDialogs />
    </div>
  );
};

export default ClusterConfigGroups;
