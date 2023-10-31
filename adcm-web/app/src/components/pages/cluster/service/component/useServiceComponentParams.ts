import { useParams } from 'react-router-dom';

export const useServiceComponentParams = () => {
  const { clusterId: clusterIdFromUrl, serviceId: serviceIdFromUrl, componentId: componentIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);
  const serviceId = Number(serviceIdFromUrl);
  const componentId = Number(componentIdFromUrl);

  return {
    clusterId,
    serviceId,
    componentId,
  };
};
