import React, { useEffect } from 'react';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';
import { useDispatch, useStore } from '@hooks';

const ClusterServices: React.FC = () => {
  const dispatch = useDispatch();
  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);

  useEffect(() => {
    if (cluster) {
      dispatch(
        setBreadcrumbs([
          { href: '/clusters', label: 'Clusters' },
          { href: `/clusters/${cluster.id}`, label: cluster.name },
          { label: 'Services' },
        ]),
      );
    }
  }, [cluster, dispatch]);

  return (
    <div>
      <h1>Cluster Services</h1>
    </div>
  );
};

export default ClusterServices;
