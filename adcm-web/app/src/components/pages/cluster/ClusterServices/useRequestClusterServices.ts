import { defaultDebounceDelay } from '@constants';
import { useDebounce, useDispatch, useRequestTimer, useStore } from '@hooks';
import { getServices, refreshServices } from '@store/adcm/cluster/services/servicesSlice';
import { cleanupRelatedData, loadRelatedData } from '@store/adcm/cluster/services/servicesTableSlice';
import { useEffect } from 'react';
import { useParams } from 'react-router-dom';

export const useRequestClusterServices = () => {
  const dispatch = useDispatch();
  const { clusterId: clusterIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);

  const filter = useStore((s) => s.adcm.servicesTable.filter);
  const sortParams = useStore((s) => s.adcm.servicesTable.sortParams);
  const paginationParams = useStore((s) => s.adcm.servicesTable.paginationParams);

  useEffect(() => {
    dispatch(loadRelatedData(clusterId));

    return () => {
      dispatch(cleanupRelatedData());
    };
  }, [dispatch, clusterId]);

  const debounceGetClusters = useDebounce(() => {
    dispatch(getServices({ clusterId }));
  }, defaultDebounceDelay);

  const debounceRefreshClusters = useDebounce(() => {
    dispatch(refreshServices({ clusterId }));
  }, defaultDebounceDelay);

  useRequestTimer(debounceGetClusters, debounceRefreshClusters, 0, [filter, sortParams, paginationParams]);
};
