import { useParams } from 'react-router-dom';
import { useActionHostGroups } from '@commonComponents/ActionHostGroups/useActionHostGroups';
import { useMemo } from 'react';
import { useStore } from '@hooks';

export const useClusterActionHostGroups = () => {
  const { clusterId: clusterIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);

  const entityArgs = useMemo(() => ({ clusterId }), [clusterId]);

  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);
  const props = useActionHostGroups('cluster', entityArgs, cluster?.concerns);
  return props;
};
