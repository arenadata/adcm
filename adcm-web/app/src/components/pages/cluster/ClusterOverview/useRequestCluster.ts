import { useDispatch, useRequestTimer, useDebounce, usePageRouteInfo } from '@hooks';
import { getCluster } from '@store/adcm/clusters/clusterSlice';
import { defaultDebounceDelay } from '@constants';
import { useEffect } from 'react';
import { cleanupBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';

export const useRequestCluster = () => {
  const dispatch = useDispatch();
  const { currentRoute } = usePageRouteInfo();

  useEffect(() => {
    return () => {
      dispatch(cleanupBreadcrumbs());
    };
  }, [dispatch]);

  const debounceGetCluster = useDebounce(() => {
    if (currentRoute?.params?.clusterId) {
      dispatch(getCluster(+currentRoute?.params?.clusterId));
    }
  }, defaultDebounceDelay);

  // eslint-disable-next-line @typescript-eslint/no-empty-function
  useRequestTimer(debounceGetCluster, () => {}, 0, [currentRoute?.params?.clusterId]);
};
