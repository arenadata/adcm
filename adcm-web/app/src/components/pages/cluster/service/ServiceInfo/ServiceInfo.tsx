import type React from 'react';
import { useStore } from '@hooks';
import MainInfoPanel from '@commonComponents/MainInfoPanel/MainInfoPanel';

const ServiceInfo: React.FC = () => {
  const service = useStore(({ adcm }) => adcm.service.service);

  return <MainInfoPanel mainInfo={service?.mainInfo} />;
};

export default ServiceInfo;
