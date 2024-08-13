import { useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { useActionHostGroups } from '@commonComponents/ActionHostGroups/useActionHostGroups';

export const useServiceActionHostGroups = () => {
  const { clusterId: clusterIdFromUrl, serviceId: serviceIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);
  const serviceId = Number(serviceIdFromUrl);

  const entityArgs = useMemo(() => ({ clusterId, serviceId }), [clusterId, serviceId]);

  const props = useActionHostGroups('service', entityArgs);

  return props;
};
