import { useParams } from 'react-router-dom';
import { useActionHostGroups } from '@commonComponents/ActionHostGroups/useActionHostGroups';
import { useMemo } from 'react';

export const useClusterActionHostGroups = () => {
  const { clusterId: clusterIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);

  const entityArgs = useMemo(() => ({ clusterId }), [clusterId]);

  const props = useActionHostGroups('cluster', entityArgs);
  return props;
};
