import { useParams } from 'react-router-dom';
import { defaultDebounceDelay } from '@constants';
import { useDebounce, useDispatch, useRequestTimer, useStore } from '@hooks';
import {
  getClusterHostsStatuses,
  refreshClusterHostsStatuses,
  cleanupClusterHostsStatuses,
} from '@store/adcm/cluster/overview/overviewHostsSlice';
import { useEffect } from 'react';

export const useRequestClusterHostsOverview = () => {
  const dispatch = useDispatch();
  const { clusterId: clusterIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);

  const { filter, paginationParams } = useStore((s) => s.adcm.clusterOverviewHostsTable);

  useEffect(() => {
    return () => {
      dispatch(cleanupClusterHostsStatuses());
    };
  }, [dispatch]);

  const debounceGetClusterHosts = useDebounce(() => {
    dispatch(getClusterHostsStatuses(clusterId));
  }, defaultDebounceDelay);

  const debounceRefreshClusterHosts = useDebounce(() => {
    dispatch(refreshClusterHostsStatuses(clusterId));
  }, defaultDebounceDelay);

  useRequestTimer(debounceGetClusterHosts, debounceRefreshClusterHosts, 0, [filter, paginationParams]);
};
