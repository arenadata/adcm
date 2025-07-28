import { useStore, useDispatch } from '@hooks';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';
import type React from 'react';
import { useEffect } from 'react';
import ClusterOverviewInfo from './ClusterOverviewInfo/ClusterOverviewInfo';
import ClusterOverviewServices from './ClusterOverviewServices/ClusterOverviewServices';
import ClusterOverviewHosts from './ClusterOverviewHosts/ClusterOverviewHosts';
import { useRequestClusterHostsOverview } from '@pages/cluster/ClusterOverview/useRequestClusterHostsOverview';
import { useRequestClusterServicesOverview } from '@pages/cluster/ClusterOverview/useRequestClusterServicesOverview';
import ClusterOverviewDescription from '@pages/cluster/ClusterOverview/ClusterOverviewDescription/ClusterOverviewDescription';
import EditClusterDescriptionDialog from '@pages/ClustersPage/Dialogs/EditClusterDescriptionDialog/EditClusterDescriptionDialog';

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
    <div style={{ marginTop: 'var(--base-margin-v)' }}>
      <ClusterOverviewDescription />
      <ClusterOverviewInfo />
      <ClusterOverviewServices />
      <ClusterOverviewHosts />
      <EditClusterDescriptionDialog />
    </div>
  );
};

export default ClusterOverview;
