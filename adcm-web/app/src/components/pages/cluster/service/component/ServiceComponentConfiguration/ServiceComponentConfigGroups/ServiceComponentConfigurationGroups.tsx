import React, { useEffect } from 'react';
import { useDispatch, useStore } from '@hooks';
import ConfigGroupsHeader from '@commonComponents/configGroups/ConfigGroupsHeader/ConfigGroupsHeader';
import ConfigGroupsTable from '@commonComponents/configGroups/ConfigGroupsTable/ConfigGroupsTable';
import { useRequestServiceComponentConfigGroups } from './useRequestServiceComponentConfigGroups';
import ServiceConfigGroupTableFooter from './ServiceComponentConfigGroupTableFooter/ServiceComponentConfigGroupTableFooter';
import { SortParams } from '@uikit/types/list.types';
import { setSortParams } from '@store/adcm/cluster/services/serviceComponents/serviceComponent/configGroups/serviceComponentConfigGroupsTableSlice';
import {
  openCreateDialog,
  openDeleteDialog,
  openMappingDialog,
} from '@store/adcm/cluster/services/serviceComponents/serviceComponent/configGroups/serviceComponentConfigGroupsActionsSlice';
import { AdcmConfigGroup } from '@models/adcm';
import ServiceComponentConfigGroupDialogs from './ServiceComponentConfigGroupDialogs/ServiceComponentConfigGroupDialogs';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';
import { useServiceComponentParams } from '@pages/cluster/service/component/useServiceComponentParams';

const ServiceComponentConfigurationGroups: React.FC = () => {
  const dispatch = useDispatch();

  const { clusterId, serviceId, componentId } = useServiceComponentParams();

  const cluster = useStore((s) => s.adcm.cluster.cluster);
  const service = useStore((s) => s.adcm.service.service);
  const component = useStore((s) => s.adcm.serviceComponent.serviceComponent);

  useEffect(() => {
    if (cluster && service && component) {
      dispatch(
        setBreadcrumbs([
          { href: '/clusters', label: 'Clusters' },
          { href: `/clusters/${cluster.id}`, label: cluster.name },
          { href: `/clusters/${cluster.id}/services`, label: 'Services' },
          { href: `/clusters/${cluster.id}/services/${service.id}`, label: service.displayName },
          { href: `/clusters/${cluster.id}/services/${service.id}/components`, label: 'Components' },
          {
            href: `/clusters/${cluster.id}/services/${service.id}/components/${component.id}`,
            label: component.displayName,
          },
          { label: 'Configuration groups' },
        ]),
      );
    }
  }, [cluster, service, component, dispatch]);

  const { clusterServiceConfigGroups, isLoading } = useStore((s) => s.adcm.serviceComponentConfigGroups);
  const sortParams = useStore((s) => s.adcm.serviceComponentConfigGroupsTable.sortParams);
  useRequestServiceComponentConfigGroups();

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
        editUrlPattern={`/clusters/${clusterId}/services/${serviceId}/components/${componentId}/configuration-groups/:configGroupId`}
        onDelete={handleDeleteConfigGroup}
      />
      <ServiceConfigGroupTableFooter />

      <ServiceComponentConfigGroupDialogs />
    </div>
  );
};

export default ServiceComponentConfigurationGroups;
