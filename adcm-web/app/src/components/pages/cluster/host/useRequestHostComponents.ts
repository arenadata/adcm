import { useDispatch, useStore } from '@hooks';
import { loadRelatedClusterHostComponents } from '@store/adcm/cluster/hosts/host/clusterHostSlice';
import {
  cleanupClusterServiceComponentsDynamicActions,
  loadClusterServiceComponentsDynamicActions,
} from '@store/adcm/cluster/services/serviceComponents/serviceComponentsDynamicActionsSlice';
import { getHostComponentStates } from '@store/adcm/host/hostSlice';
import { useEffect } from 'react';

export const useRequestHostComponents = () => {
  const dispatch = useDispatch();
  const host = useStore(({ adcm }) => adcm.host.host);
  const components = useStore(({ adcm }) => adcm.clusterHost.relatedData.hostComponents);

  useEffect(() => {
    if (host?.cluster) {
      const payload = { hostId: host.id, clusterId: host.cluster.id };
      dispatch(loadRelatedClusterHostComponents(payload));
      dispatch(getHostComponentStates(payload));
    }
  }, [dispatch, host]);

  useEffect(() => {
    if (components.length > 0) {
      dispatch(loadClusterServiceComponentsDynamicActions({ components, isHostOwnAction: true }));
    }
  }, [dispatch, components]);

  useEffect(() => {
    return () => {
      dispatch(cleanupClusterServiceComponentsDynamicActions());
    };
  });
};
