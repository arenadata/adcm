import React from 'react';
import { useDispatch, useStore } from '@hooks';
import ConfigGroupsHeader from '@commonComponents/configGroups/ConfigGroupsHeader/ConfigGroupsHeader';
import ConfigGroupsTable from '@commonComponents/configGroups/ConfigGroupsTable/ConfigGroupsTable';
import { useRequestServiceConfigGroups } from './useRequestServiceConfigGroups';
import ServiceConfigGroupTableFooter from './ServiceConfigGroupTableFooter/ServiceConfigGroupTableFooterConfigGroupTableFooter';
import { SortParams } from '@uikit/types/list.types';
import { setSortParams } from '@store/adcm/cluster/services/configGroups/serviceConfigGroupsTableSlice';
import {
  openCreateDialog,
  openDeleteDialog,
  openMappingDialog,
} from '@store/adcm/cluster/services/configGroups/serviceConfigGroupsActionsSlice';
import { useParams } from 'react-router-dom';
import { AdcmConfigGroup } from '@models/adcm';
import ServiceConfigGroupDialogs from './ServiceConfigGroupDialogs/ServiceConfigGroupDialogs';

const ServiceConfigurationGroups: React.FC = () => {
  const dispatch = useDispatch();

  const { clusterId: clusterIdFromUrl, serviceId: serviceIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);
  const serviceId = Number(serviceIdFromUrl);

  const { clusterServiceConfigGroups, isLoading } = useStore((s) => s.adcm.serviceConfigGroups);
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
    <div>
      <ConfigGroupsHeader onCreate={handleCreateConfigGroup} />
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

      <ServiceConfigGroupDialogs />
    </div>
  );
};

export default ServiceConfigurationGroups;
