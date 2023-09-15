import { useStore } from '@hooks';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';
import React, { useEffect } from 'react';
import { useDispatch } from 'react-redux';
import ClusterOverviewInfo from './ClusterOverviewInfo/ClusterOverviewInfo';
import ClusterOverviewServices from './ClusterOverviewServices/ClusterOverviewServices';
import ClusterOverviewHosts from './ClusterOverviewHosts/ClusterOverviewHosts';
import { useRequestClusterHostsOverview } from '@pages/cluster/ClusterOverview/useRequestClusterHostsOverview';
import { useRequestClusterServicesOverview } from '@pages/cluster/ClusterOverview/useRequestClusterServicesOverview';

const ClusterOverview: React.FC = () => {
  const dispatch = useDispatch();
  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);

  useRequestClusterHostsOverview();
  useRequestClusterServicesOverview();

  useEffect(() => {
    if (cluster) {
      dispatch(
        setBreadcrumbs([
          { href: '/clusters', label: 'Clusters' },
          { href: `/clusters/${cluster.id}`, label: cluster.name },
          { label: 'Overview' },
        ]),
      );
    }
  }, [cluster, dispatch]);

  return (
    <div>
      <p>Cluster description</p>
      <ClusterOverviewInfo />
      <ClusterOverviewServices />
      <ClusterOverviewHosts />
    </div>
  );
};

export default ClusterOverview;
