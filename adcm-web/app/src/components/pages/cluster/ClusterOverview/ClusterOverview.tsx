import { useStore, useDispatch } from '@hooks';
import { EMPTY_ARRAY } from '@constants';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';
import type React from 'react';
import { useEffect } from 'react';
import ClusterOverviewDescription from './ClusterOverviewDescription/ClusterOverviewDescription';
import ClusterOverviewTopGrid from './ClusterOverviewTopGrid/ClusterOverviewTopGrid';
import ClusterOverviewEntities from './ClusterOverviewEntities/ClusterOverviewEntities';
import ClusterOverviewBottomConcerns from './ClusterOverviewBottom/ClusterOverviewBottomConcerns';
import ClusterOverviewBottomBundleInfo from './ClusterOverviewBottom/ClusterOverviewBottomBundleInfo';
import { useRequestClusterOverviewMetrics } from '@pages/cluster/ClusterOverview/useRequestClusterOverviewMetrics';
import { useResetClusterOverviewState } from '@pages/cluster/ClusterOverview/useResetClusterOverviewState';
import EditClusterDescriptionDialog from '@pages/ClustersPage/Dialogs/EditClusterDescriptionDialog/EditClusterDescriptionDialog';
import s from './ClusterOverview.module.scss';

const ClusterOverview: React.FC = () => {
  const dispatch = useDispatch();
  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);

  useResetClusterOverviewState();
  useRequestClusterOverviewMetrics();

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
    <div className={s.clusterOverview} data-test="cluster-overview">
      <ClusterOverviewDescription />
      {/* warning block */}
      <ClusterOverviewTopGrid />
      <ClusterOverviewEntities />
      <div className={s.clusterOverview__bottomWrap}>
        <div className={s.clusterOverview__bottom}>
          <ClusterOverviewBottomConcerns concerns={cluster?.concerns ?? EMPTY_ARRAY} />
          <ClusterOverviewBottomBundleInfo mainInfo={cluster?.mainInfo} />
        </div>
      </div>
      <EditClusterDescriptionDialog />
    </div>
  );
};

export default ClusterOverview;
