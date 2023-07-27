import { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useDispatch, useRequestTimer, useDebounce } from '@hooks';
import { getCluster } from '@store/adcm/clusters/clusterSlice';
import { defaultDebounceDelay } from '@constants';
import { cleanupBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';

export const useRequestCluster = () => {
  const dispatch = useDispatch();
  const { clusterId: clusterIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);

  useEffect(() => {
    return () => {
      dispatch(cleanupBreadcrumbs());
    };
  }, [dispatch]);

  const debounceGetCluster = useDebounce(() => {
    if (clusterId) {
      dispatch(getCluster(clusterId));
    }
  }, defaultDebounceDelay);

  // eslint-disable-next-line @typescript-eslint/no-empty-function
  useRequestTimer(debounceGetCluster, () => {}, 0, [clusterId]);
};
