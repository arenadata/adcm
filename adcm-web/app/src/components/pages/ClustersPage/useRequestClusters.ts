import { useEffect } from 'react';
import { useStore, useDispatch, useRequestTimer, useDebounce } from '@hooks';
import { getClusters, refreshClusters, cleanupClusters } from '@store/adcm/clusters/clustersSlice';
import { loadRelatedData, cleanupRelatedData } from '@store/adcm/clusters/clustersTableSlice';
import { defaultDebounceDelay } from '@constants';
import { loadClustersDynamicActions } from '@store/adcm/clusters/clustersDynamicActionsSlice';

export const useRequestClusters = () => {
  const dispatch = useDispatch();
  const filter = useStore((s) => s.adcm.clustersTable.filter);
  const sortParams = useStore((s) => s.adcm.clustersTable.sortParams);
  const paginationParams = useStore((s) => s.adcm.clustersTable.paginationParams);
  const clusters = useStore((s) => s.adcm.clusters.clusters);

  useEffect(() => {
    dispatch(loadRelatedData());

    return () => {
      dispatch(cleanupClusters());
      dispatch(cleanupRelatedData());
    };
  }, [dispatch]);

  useEffect(() => {
    if (clusters.length) {
      const clustersIds = clusters.map(({ id }) => id);
      dispatch(loadClustersDynamicActions(clustersIds));
    }
  }, [dispatch, clusters]);

  const debounceGetClusters = useDebounce(() => {
    dispatch(getClusters());
  }, defaultDebounceDelay);

  const debounceRefreshClusters = useDebounce(() => {
    dispatch(refreshClusters());
  }, defaultDebounceDelay);

  useRequestTimer(debounceGetClusters, debounceRefreshClusters, 0, [filter, sortParams, paginationParams]);
};
