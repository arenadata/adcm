import { useParams } from 'react-router-dom';
import { defaultDebounceDelay } from '@constants';
import { useDebounce, useDispatch, useRequestTimer, useStore } from '@hooks';
import { getClusterHosts, refreshClusterHosts } from '@store/adcm/cluster/hosts/hostsSlice';
import { cleanupRelatedData, loadRelatedData } from '@store/adcm/hosts/hostsTableSlice';
import { useEffect } from 'react';

export const useRequestClusterHosts = () => {
  const dispatch = useDispatch();
  const { clusterId: clusterIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);

  const filter = useStore((s) => s.adcm.clusterHostsTable.filter);
  const { sortParams, paginationParams, requestFrequency } = useStore((s) => s.adcm.clusterHostsTable);

  useEffect(() => {
    dispatch(loadRelatedData());

    return () => {
      dispatch(cleanupRelatedData());
    };
  }, [dispatch]);

  const debounceGetClusterHosts = useDebounce(() => {
    dispatch(getClusterHosts(clusterId));
  }, defaultDebounceDelay);

  const debounceRefreshClusterHosts = useDebounce(() => {
    dispatch(refreshClusterHosts(clusterId));
  }, defaultDebounceDelay);

  useRequestTimer(debounceGetClusterHosts, debounceRefreshClusterHosts, requestFrequency, [
    filter,
    sortParams,
    paginationParams,
  ]);
};
