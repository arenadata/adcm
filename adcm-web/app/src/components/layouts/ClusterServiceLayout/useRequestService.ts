import { useDispatch, useRequestTimer, useDebounce, useStore } from '@hooks';
import { defaultDebounceDelay } from '@constants';
import { useParams } from 'react-router-dom';
import { cleanupService, getService } from '@store/adcm/services/serviceSlice';
import { getRelatedServiceComponentsStatuses } from '@store/adcm/services/serviceSlice';
import { useEffect } from 'react';
import {
  cleanupClusterServiceDynamicActions,
  loadClusterServicesDynamicActions,
} from '@store/adcm/cluster/services/servicesDynamicActionsSlice';
import { isBlockingConcernPresent } from '@utils/concernUtils';

export const useRequestService = () => {
  const dispatch = useDispatch();
  const service = useStore(({ adcm }) => adcm.service.service);
  const { clusterId: clusterIdFromUrl, serviceId: serviceIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);
  const serviceId = Number(serviceIdFromUrl);

  useEffect(() => {
    return () => {
      dispatch(cleanupService());
      dispatch(cleanupClusterServiceDynamicActions());
    };
  }, [dispatch]);

  useEffect(() => {
    if (!Number.isNaN(clusterId) && !Number.isNaN(serviceId) && !isBlockingConcernPresent(service?.concerns ?? [])) {
      dispatch(loadClusterServicesDynamicActions({ clusterId, servicesIds: [serviceId] }));
    }
  }, [dispatch, clusterId, serviceId, service?.concerns]);

  const debounceGetCluster = useDebounce(() => {
    if (clusterId && serviceId) {
      const payload = { clusterId, serviceId };
      dispatch(getService(payload));
      dispatch(getRelatedServiceComponentsStatuses(payload));
    }
  }, defaultDebounceDelay);

  // eslint-disable-next-line @typescript-eslint/no-empty-function
  useRequestTimer(debounceGetCluster, () => {}, 0, [clusterId, serviceId]);
};
