import { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useDispatch } from '@hooks';
import { cleanupClustersMetrics, loadClustersMetrics } from '@store/adcm/clusters/clustersMetricsSlice';

export const useRequestClusterOverviewMetrics = () => {
  const dispatch = useDispatch();
  const { clusterId: clusterIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);

  useEffect(() => {
    if (!clusterId) {
      return;
    }

    dispatch(loadClustersMetrics([clusterId]));
  }, [clusterId, dispatch]);

  useEffect(() => {
    return () => {
      dispatch(cleanupClustersMetrics());
    };
  }, [dispatch]);
};
