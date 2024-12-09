import type React from 'react';
import { useDispatch, useStore } from '@hooks';
import ConfigGroupsHeader from '@commonComponents/configGroups/ConfigGroupsHeader/ConfigGroupsHeader';
import ConfigGroupsTable from '@commonComponents/configGroups/ConfigGroupsTable/ConfigGroupsTable';
import { useRequestServiceConfigGroups } from './useRequestServiceConfigGroups';
import ServiceConfigGroupTableFooter from './ServiceConfigGroupTableFooter/ServiceConfigGroupTableFooterConfigGroupTableFooter';
import type { SortParams } from '@uikit/types/list.types';
import { setSortParams } from '@store/adcm/cluster/services/configGroups/serviceConfigGroupsTableSlice';
import {
  openCreateDialog,
  openDeleteDialog,
  openMappingDialog,
} from '@store/adcm/cluster/services/configGroups/serviceConfigGroupsActionsSlice';
import { useParams } from 'react-router-dom';
import type { AdcmConfigGroup } from '@models/adcm';
import ServiceConfigGroupDialogs from './ServiceConfigGroupDialogs/ServiceConfigGroupDialogs';
import PermissionsChecker from '@commonComponents/PermissionsChecker/PermissionsChecker';

const ServiceConfigurationGroups: React.FC = () => {
  const dispatch = useDispatch();

  const { clusterId: clusterIdFromUrl, serviceId: serviceIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);
  const serviceId = Number(serviceIdFromUrl);

  const { clusterServiceConfigGroups, isLoading } = useStore((s) => s.adcm.serviceConfigGroups);
  const accessCheckStatus = useStore((s) => s.adcm.serviceConfigGroups.accessCheckStatus);
  const sortParams = useStore((s) => s.adcm.serviceConfigGroupsTable.sortParams);
  useRequestServiceConfigGroups();

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
    <PermissionsChecker requestState={accessCheckStatus}>
      <ConfigGroupsHeader onCreate={handleCreateConfigGroup} />
      {clusterServiceConfigGroups.length > 0 && (
        <>
          <ConfigGroupsTable
            configGroups={clusterServiceConfigGroups}
            isLoading={isLoading}
            sortParams={sortParams}
            onSorting={handleSorting}
            onMapping={handleMappingConfigGroup}
            editUrlPattern={`/clusters/${clusterId}/services/${serviceId}/configuration-groups/:configGroupId`}
            onDelete={handleDeleteConfigGroup}
          />
          <ServiceConfigGroupTableFooter />
        </>
      )}

      <ServiceConfigGroupDialogs />
    </PermissionsChecker>
  );
};

export default ServiceConfigurationGroups;
