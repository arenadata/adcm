import { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useDispatch, useRequestTimer, useDebounce, useStore } from '@hooks';
import { cleanupCluster, getCluster } from '@store/adcm/clusters/clusterSlice';
import { defaultDebounceDelay } from '@constants';
import { cleanupBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';
import {
  cleanupClusterDynamicActions,
  loadClustersDynamicActions,
} from '@store/adcm/clusters/clustersDynamicActionsSlice';
import { isBlockingConcernPresent } from '@utils/concernUtils';

export const useRequestCluster = () => {
  const dispatch = useDispatch();
  const { clusterId: clusterIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);
  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);

  useEffect(() => {
    return () => {
      dispatch(cleanupBreadcrumbs());
      dispatch(cleanupCluster());
      dispatch(cleanupClusterDynamicActions());
    };
  }, [dispatch]);

  useEffect(() => {
    if (!Number.isNaN(clusterId) && !isBlockingConcernPresent(cluster?.concerns ?? [])) {
      dispatch(loadClustersDynamicActions([clusterId]));
    }
  }, [dispatch, clusterId, cluster?.concerns]);

  const debounceGetCluster = useDebounce(() => {
    if (clusterId) {
      dispatch(getCluster(clusterId));
    }
  }, defaultDebounceDelay);

  // eslint-disable-next-line @typescript-eslint/no-empty-function
  useRequestTimer(debounceGetCluster, () => {}, 0, [clusterId]);
};
