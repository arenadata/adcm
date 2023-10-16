import React from 'react';
import ConfigGroupSingleHeader from '@commonComponents/configGroups/ConfigGroupSingleHeader/ConfigGroupSingleHeader ';
import { useStore } from '@hooks';
import { useServiceConfigGroupSingle } from './useServiceConfigGroupSingle';

const ServiceConfigGroupSingle: React.FC = () => {
  useServiceConfigGroupSingle();
  const cluster = useStore((s) => s.adcm.cluster.cluster);
  const service = useStore((s) => s.adcm.service.service);
  const serviceConfigGroup = useStore((s) => s.adcm.serviceConfigGroup.serviceConfigGroup);

  return (
    <>
      <ConfigGroupSingleHeader
        configGroup={serviceConfigGroup}
        returnUrl={`/clusters/${cluster?.id}/services/${service?.id}/configuration-groups`}
      />
    </>
  );
};

export default ServiceConfigGroupSingle;
