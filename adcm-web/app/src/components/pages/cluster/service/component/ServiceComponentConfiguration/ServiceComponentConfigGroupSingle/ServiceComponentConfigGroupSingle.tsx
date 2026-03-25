import type React from 'react';
import { useEffect } from 'react';
import { useDispatch, useStore } from '@hooks';
import { useServiceComponentParams } from '@pages/cluster/service/component/useServiceComponentParams';
import { useServiceComponentConfigGroupSingle } from './useServiceComponentConfigGroupSingle';
import ConfigGroupSingleHeader from '@commonComponents/configGroups/ConfigGroupSingleHeader/ConfigGroupSingleHeader';
import ServiceComponentConfigGroupConfiguration from '@pages/cluster/service/component/ServiceComponentConfiguration/ServiceComponentConfigGroupSingle/ServiceComponentConfigGroupConfiguration/ServiceComponentConfigGroupConfiguration';
import EditConfigGroupDescriptionDialog from '@commonComponents/configGroups/EditConfigGroupDescriptionDialog/EditConfigGroupDescriptionDialog';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';

const ServiceComponentConfigGroupSingle: React.FC = () => {
  const dispatch = useDispatch();
  const { clusterId, serviceId, componentId } = useServiceComponentParams();

  const cluster = useStore((s) => s.adcm.cluster.cluster);
  const service = useStore((s) => s.adcm.service.service);
  const component = useStore((s) => s.adcm.serviceComponent.serviceComponent);
  const serviceComponentConfigGroup = useStore(
    (s) => s.adcm.serviceComponentConfigGroupSingle.serviceComponentConfigGroup,
  );

  useServiceComponentConfigGroupSingle();

  useEffect(() => {
    if (cluster && service && component && serviceComponentConfigGroup) {
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
          {
            href: `/clusters/${cluster.id}/services/${service.id}/components/${component.id}/configuration-groups`,
            label: 'Configuration groups',
          },
          {
            href: `/clusters/${cluster.id}/services/${service.id}/components/${component.id}/configuration-groups/${serviceComponentConfigGroup.id}`,
            label: serviceComponentConfigGroup.name,
          },
          { label: 'Configuration' },
        ]),
      );
    }
  }, [cluster, service, component, serviceComponentConfigGroup, dispatch]);

  return (
    <>
      <ConfigGroupSingleHeader
        configGroup={serviceComponentConfigGroup}
        returnUrl={`/clusters/${clusterId}/services/${serviceId}/components/${componentId}/configuration-groups`}
        entityType="component"
        entityArgs={{ clusterId, serviceId, componentId }}
      />
      <EditConfigGroupDescriptionDialog />

      <ServiceComponentConfigGroupConfiguration />
    </>
  );
};

export default ServiceComponentConfigGroupSingle;
