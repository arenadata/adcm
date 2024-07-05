import { useDebounce, useDispatch, useRequestTimer, useStore } from '@hooks';
import { useEffect } from 'react';
import {
  cleanupClusterHostComponentsDynamicActions,
  loadClusterHostComponentsDynamicActions,
} from '@store/adcm/cluster/hosts/host/hostComponentsDynamicActionsSlice';
import { isBlockingConcernPresent } from '@utils/concernUtils';
import {
  cleanupHostComponents,
  getHostComponents,
  refreshHostComponents,
} from '@store/adcm/hostComponents/hostComponentsSlice';
import { defaultDebounceDelay } from '@constants';
import { cleanupList } from '@store/adcm/hostComponents/hostComponentsTableSlice';
import { usePersistHostComponentsTableSettings } from './usePersistHostComponentsTableSettings';

export const useRequestHostComponents = () => {
  const dispatch = useDispatch();
  // TODO: it's very very ugly, rework in first queue
  const host = useStore(({ adcm }) => adcm.clusterHost.clusterHost ?? adcm.host.host);
  const components = useStore(({ adcm }) => adcm.hostComponents.hostComponents);
  const accessCheckStatus = useStore(({ adcm }) => adcm.clusterHost.accessCheckStatus);

  const filter = useStore((s) => s.adcm.hostComponentsTable.filter);
  const sortParams = useStore((s) => s.adcm.hostComponentsTable.sortParams);
  const paginationParams = useStore((s) => s.adcm.hostComponentsTable.paginationParams);
  const clusters = host?.cluster;

  useEffect(() => {
    return () => {
      dispatch(cleanupHostComponents());
      dispatch(cleanupList());
    };
  }, [dispatch]);

  usePersistHostComponentsTableSettings();

  const debounceGetClusters = useDebounce(() => {
    clusters && dispatch(getHostComponents({ clusterId: clusters.id, hostId: host.id }));
  }, defaultDebounceDelay);

  const debounceRefreshClusters = useDebounce(() => {
    clusters && dispatch(refreshHostComponents({ clusterId: clusters.id, hostId: host.id }));
  }, defaultDebounceDelay);

  useRequestTimer(debounceGetClusters, debounceRefreshClusters, 0, [filter, sortParams, paginationParams, clusters]);

  useEffect(() => {
    if (components.length > 0 && host && !isBlockingConcernPresent(host.concerns)) {
      const componentsPrototypesIds = components.map(({ prototype }) => prototype.id);
      dispatch(
        loadClusterHostComponentsDynamicActions({
          clusterId: host.cluster.id,
          hostId: host.id,
          componentsPrototypesIds,
        }),
      );
    }
  }, [dispatch, components, host, host?.concerns]);

  useEffect(() => {
    return () => {
      dispatch(cleanupClusterHostComponentsDynamicActions());
    };
  });

  return {
    accessCheckStatus,
  };
};
