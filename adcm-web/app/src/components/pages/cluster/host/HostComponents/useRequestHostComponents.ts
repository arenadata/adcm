import { useDispatch, useStore } from '@hooks';
import { getHostComponentStates } from '@store/adcm/host/hostSlice';
import { useEffect } from 'react';
import {
  cleanupClusterHostComponentsDynamicActions,
  loadClusterHostComponentsDynamicActions,
} from '@store/adcm/cluster/hosts/host/hostComponentsDynamicActionsSlice';
import { loadRelatedClusterHostComponents } from '@store/adcm/cluster/hosts/host/clusterHostSlice';
import { isBlockingConcernPresent } from '@utils/concernUtils';

export const useRequestHostComponents = () => {
  const dispatch = useDispatch();
  // TODO: it's very very ugly, rework in first queue
  const host = useStore(({ adcm }) => adcm.clusterHost.clusterHost ?? adcm.host.host);
  const components = useStore(({ adcm }) => adcm.clusterHost.relatedData.hostComponents);

  useEffect(() => {
    if (host?.cluster) {
      const payload = { hostId: host.id, clusterId: host.cluster.id };
      dispatch(loadRelatedClusterHostComponents(payload));
      dispatch(getHostComponentStates(payload));
    }
  }, [dispatch, host]);

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
};
