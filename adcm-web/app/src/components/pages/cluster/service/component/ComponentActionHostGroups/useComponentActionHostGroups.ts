import { useParams } from 'react-router-dom';
import { useActionHostGroups } from '@commonComponents/ActionHostGroups/useActionHostGroups';
import { useMemo } from 'react';
import { useStore } from '@hooks';

export const useComponentActionHostGroups = () => {
  const { clusterId: clusterIdFromUrl, serviceId: serviceIdFromUrl, componentId: componentIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);
  const serviceId = Number(serviceIdFromUrl);
  const componentId = Number(componentIdFromUrl);

  const entityArgs = useMemo(() => ({ clusterId, serviceId, componentId }), [clusterId, serviceId, componentId]);

  const component = useStore(({ adcm }) => adcm.serviceComponent.serviceComponent);
  const props = useActionHostGroups('component', entityArgs, component?.concerns);

  return props;
};
