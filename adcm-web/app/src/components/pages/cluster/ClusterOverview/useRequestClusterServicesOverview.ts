import { useParams } from 'react-router-dom';
import { defaultDebounceDelay } from '@constants';
import { useDebounce, useDispatch, useRequestTimer, useStore } from '@hooks';
import {
  getClusterServicesStatuses,
  refreshClusterServicesStatuses,
  cleanupClusterServicesStatuses,
} from '@store/adcm/cluster/overview/overviewServicesSlice';
import { useEffect } from 'react';

export const useRequestClusterServicesOverview = () => {
  const dispatch = useDispatch();
  const { clusterId: clusterIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);
  const { filter, paginationParams } = useStore((s) => s.adcm.clusterOverviewServicesTable);

  useEffect(() => {
    return () => {
      dispatch(cleanupClusterServicesStatuses());
    };
  }, [dispatch]);

  const debounceGetClusterServices = useDebounce(() => {
    dispatch(getClusterServicesStatuses(clusterId));
  }, defaultDebounceDelay);

  const debounceRefreshClusterServices = useDebounce(() => {
    dispatch(refreshClusterServicesStatuses(clusterId));
  }, defaultDebounceDelay);

  useRequestTimer(debounceGetClusterServices, debounceRefreshClusterServices, 0, [clusterId, filter, paginationParams]);
};
