import React from 'react';
import Statusable from '@uikit/Statusable/Statusable';
import { AdcmService } from '@models/adcm';
import { servicesStatusesMap } from '@pages/cluster/ClusterServices/ClusterServicesTable/ClusterServicesTable.constants';

interface ServiceNameProps {
  service: AdcmService;
}

const ServiceName: React.FC<ServiceNameProps> = ({ service }) => {
  return (
    <Statusable status={servicesStatusesMap[service.status]} size="medium">
      {service.displayName}
    </Statusable>
  );
};

export default ServiceName;
