import { useDispatch, useRequestTimer, useDebounce } from '@hooks';
import { defaultDebounceDelay } from '@constants';
import { useParams } from 'react-router-dom';
import { cleanupService, getService } from '@store/adcm/services/serviceSlice';
import { getRelatedServiceComponentsStatuses } from '@store/adcm/services/serviceSlice';
import { useEffect } from 'react';

export const useRequestService = () => {
  const dispatch = useDispatch();
  const { clusterId: clusterIdFromUrl, serviceId: serviceIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);
  const serviceId = Number(serviceIdFromUrl);

  useEffect(() => {
    return () => {
      dispatch(cleanupService());
    };
  }, [dispatch]);

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
