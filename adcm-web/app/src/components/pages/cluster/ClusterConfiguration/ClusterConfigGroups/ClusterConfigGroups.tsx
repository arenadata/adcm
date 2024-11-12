import React, { useEffect } from 'react';
import { useDispatch, useStore } from '@hooks';
import ConfigGroupsHeader from '@commonComponents/configGroups/ConfigGroupsHeader/ConfigGroupsHeader';
import ConfigGroupsTable from '@commonComponents/configGroups/ConfigGroupsTable/ConfigGroupsTable';
import { useRequestClusterConfigGroups } from './useRequestClusterConfigGroups';
import ClusterConfigGroupTableFooter from './ClusterConfigGroupTableFooter/ClusterConfigGroupTableFooter';
import type { SortParams } from '@uikit/types/list.types';
import { setSortParams } from '@store/adcm/cluster/configGroups/clusterConfigGroupsTableSlice';
import ClusterConfigGroupDialogs from './ClusterConfigGroupDialogs/ClusterConfigGroupDialogs';
import {
  openCreateDialog,
  openDeleteDialog,
  openMappingDialog,
} from '@store/adcm/cluster/configGroups/clusterConfigGroupActionsSlice';
import { useParams } from 'react-router-dom';
import type { AdcmConfigGroup } from '@models/adcm';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';
import PermissionsChecker from '@commonComponents/PermissionsChecker/PermissionsChecker';

const ClusterConfigGroups: React.FC = () => {
  const dispatch = useDispatch();

  const { clusterId: clusterIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);

  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);

  const { clusterConfigGroups, isLoading } = useStore((s) => s.adcm.clusterConfigGroups);
  const accessCheckStatus = useStore((s) => s.adcm.clusterConfigGroups.accessCheckStatus);
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

  useEffect(() => {
    if (cluster) {
      dispatch(
        setBreadcrumbs([
          { href: '/clusters', label: 'Clusters' },
          { href: `/clusters/${cluster.id}`, label: cluster.name },
          { label: 'Configuration' },
          { label: 'Configuration groups' },
        ]),
      );
    }
  }, [cluster, dispatch]);

  return (
    <PermissionsChecker requestState={accessCheckStatus}>
      <div>
        <ConfigGroupsHeader onCreate={handleCreateConfigGroup} />
        {clusterConfigGroups.length > 0 && (
          <>
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
          </>
        )}
        <ClusterConfigGroupDialogs />
      </div>
    </PermissionsChecker>
  );
};

export default ClusterConfigGroups;
