import { useDispatch, useStore } from '@hooks';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';
import React, { useEffect } from 'react';

const ClusterConfiguration: React.FC = () => {
  const dispatch = useDispatch();
  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);

  useEffect(() => {
    if (cluster) {
      dispatch(
        setBreadcrumbs([
          { href: '/clusters', label: 'Clusters' },
          { href: `/clusters/${cluster.id}`, label: cluster.name },
          { label: 'Configuration' },
        ]),
      );
    }
  }, [cluster, dispatch]);

  return (
    <div>
      <h1>Cluster Configuration</h1>
    </div>
  );
};

export default ClusterConfiguration;
