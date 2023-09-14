import { defaultDebounceDelay } from '@constants';
import { useDebounce, useDispatch, useRequestTimer, useStore } from '@hooks';
import { getServices, refreshServices } from '@store/adcm/cluster/services/servicesSlice';
import { cleanupRelatedData, loadRelatedData } from '@store/adcm/cluster/services/servicesTableSlice';
import { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { loadClusterServicesDynamicActions } from '@store/adcm/cluster/services/servicesDynamicActionsSlice';

export const useRequestClusterServices = () => {
  const dispatch = useDispatch();
  const { clusterId: clusterIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);

  const filter = useStore((s) => s.adcm.servicesTable.filter);
  const sortParams = useStore((s) => s.adcm.servicesTable.sortParams);
  const paginationParams = useStore((s) => s.adcm.servicesTable.paginationParams);

  const services = useStore((s) => s.adcm.services.services);

  useEffect(() => {
    dispatch(loadRelatedData(clusterId));

    return () => {
      dispatch(cleanupRelatedData());
    };
  }, [dispatch, clusterId]);

  useEffect(() => {
    if (services.length) {
      const servicesIds = services.map(({ id }) => id);
      dispatch(loadClusterServicesDynamicActions({ clusterId, servicesIds }));
    }
  }, [dispatch, clusterId, services]);

  const debounceGetClusters = useDebounce(() => {
    dispatch(getServices({ clusterId }));
  }, defaultDebounceDelay);

  const debounceRefreshClusters = useDebounce(() => {
    dispatch(refreshServices({ clusterId }));
  }, defaultDebounceDelay);

  useRequestTimer(debounceGetClusters, debounceRefreshClusters, 0, [filter, sortParams, paginationParams]);
};
