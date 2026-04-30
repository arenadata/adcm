import type React from 'react';
import { useEffect } from 'react';
import ConfigGroupSingleHeader from '@commonComponents/configGroups/ConfigGroupSingleHeader/ConfigGroupSingleHeader';
import { useDispatch, useStore } from '@hooks';
import { useServiceConfigGroupSingle } from './useServiceConfigGroupSingle';
import ServiceConfigGroupSingleConfiguration from './ServiceConfigGroupSingleConfiguration/ServiceConfigGroupSingleConfiguration';
import EditConfigGroupDescriptionDialog from '@commonComponents/configGroups/EditConfigGroupDescriptionDialog/EditConfigGroupDescriptionDialog';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';
import { useServiceComponentParams } from '@pages/cluster/service/component/useServiceComponentParams.ts';

const ServiceConfigGroupSingle: React.FC = () => {
  const dispatch = useDispatch();
  const { clusterId, serviceId } = useServiceComponentParams();
  const cluster = useStore((s) => s.adcm.cluster.cluster);
  const service = useStore((s) => s.adcm.service.service);
  const serviceConfigGroup = useStore((s) => s.adcm.serviceConfigGroup.serviceConfigGroup);

  useServiceConfigGroupSingle();

  useEffect(() => {
    if (cluster && service && serviceConfigGroup) {
      dispatch(
        setBreadcrumbs([
          { href: '/clusters', label: 'Clusters' },
          { href: `/clusters/${cluster.id}`, label: cluster.name },
          { href: `/clusters/${cluster.id}/services`, label: 'Services' },
          { href: `/clusters/${cluster.id}/services/${service.id}`, label: service.displayName },
          { href: `/clusters/${cluster.id}/services/${service.id}/configuration-groups`, label: 'Config groups' },
          {
            href: `/clusters/${cluster.id}/services/${service.id}/configuration-groups/${serviceConfigGroup.id}`,
            label: serviceConfigGroup.name,
          },
        ]),
      );
    }
  }, [cluster, service, serviceConfigGroup, dispatch]);

  return (
    <>
      <ConfigGroupSingleHeader
        configGroup={serviceConfigGroup}
        returnUrl={`/clusters/${clusterId}/services/${serviceId}/configuration-groups`}
        entityType="service"
        entityArgs={{ clusterId, serviceId }}
      />
      <ServiceConfigGroupSingleConfiguration />
      <EditConfigGroupDescriptionDialog />
    </>
  );
};

export default ServiceConfigGroupSingle;
