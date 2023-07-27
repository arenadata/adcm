import React from 'react';
import Statusable from '@uikit/Statusable/Statusable';
import { AdcmService } from '@models/adcm';
import { serviceStatusesMap } from '@commonComponents/service/ServiceName/ServiceName.constants';

interface ServiceNameProps {
  service: AdcmService;
}

const ServiceName: React.FC<ServiceNameProps> = ({ service }) => {
  return (
    <Statusable status={serviceStatusesMap[service.status]} size="medium">
      {service.displayName}
    </Statusable>
  );
};

export default ServiceName;
