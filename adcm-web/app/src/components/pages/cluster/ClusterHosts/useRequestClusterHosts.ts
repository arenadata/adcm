import { useParams } from 'react-router-dom';
import { defaultDebounceDelay } from '@constants';
import { useDebounce, useDispatch, useRequestTimer, useStore } from '@hooks';
import { cleanupClusterHosts, getClusterHosts, refreshClusterHosts } from '@store/adcm/cluster/hosts/hostsSlice';
import { cleanupList, loadHostProviders } from '@store/adcm/cluster/hosts/hostsTableSlice';
import { useEffect } from 'react';
import { loadClusterHostsDynamicActions } from '@store/adcm/cluster/hosts/hostsDynamicActionsSlice';
import { usePersistClusterHostsTableSettings } from './usePersistClusterHostsTableSettings';

export const useRequestClusterHosts = () => {
  const dispatch = useDispatch();
  const { clusterId: clusterIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);

  const filter = useStore((s) => s.adcm.clusterHostsTable.filter);
  const { sortParams, paginationParams, requestFrequency } = useStore((s) => s.adcm.clusterHostsTable);
  const hosts = useStore(({ adcm }) => adcm.clusterHosts.hosts);

  usePersistClusterHostsTableSettings();

  useEffect(() => {
    dispatch(loadHostProviders());

    return () => {
      dispatch(cleanupList());
      dispatch(cleanupClusterHosts());
    };
  }, [dispatch]);

  useEffect(() => {
    if (hosts.length) {
      dispatch(loadClusterHostsDynamicActions({ clusterId, hosts }));
    }
  }, [dispatch, clusterId, hosts]);

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
