import { defaultDebounceDelay } from '@constants';
import { useDebounce, useDispatch, useRequestTimer, useStore } from '@hooks';
import { loadClusterServiceComponentsDynamicActions } from '@store/adcm/cluster/services/serviceComponents/serviceComponentsDynamicActionsSlice';
import {
  cleanupServiceComponents,
  getServiceComponents,
  refreshServiceComponents,
} from '@store/adcm/cluster/services/serviceComponents/serviceComponentsSlice';
import { useEffect } from 'react';
import { useParams } from 'react-router-dom';

export const useRequestServiceComponents = () => {
  const dispatch = useDispatch();
  const { clusterId: clusterIdFromUrl, serviceId: serviceIdFromUrl } = useParams();
  const serviceComponents = useStore(({ adcm }) => adcm.serviceComponents.serviceComponents);
  const clusterId = Number(clusterIdFromUrl);
  const serviceId = Number(serviceIdFromUrl);

  const sortParams = useStore(({ adcm }) => adcm.serviceComponentsTable.sortParams);

  useEffect(() => {
    return () => {
      dispatch(cleanupServiceComponents());
    };
  }, [dispatch, clusterId, serviceId]);

  useEffect(() => {
    if (serviceComponents.length > 0) {
      const componentsIds = serviceComponents.map(({ id }) => id);
      dispatch(loadClusterServiceComponentsDynamicActions({ clusterId, serviceId, componentsIds }));
    }
  }, [dispatch, clusterId, serviceId, serviceComponents]);

  const debounceGetServiceComponents = useDebounce(() => {
    dispatch(getServiceComponents({ clusterId, serviceId }));
  }, defaultDebounceDelay);

  const debounceRefreshServiceComponents = useDebounce(() => {
    dispatch(refreshServiceComponents({ clusterId, serviceId }));
  }, defaultDebounceDelay);

  useRequestTimer(debounceGetServiceComponents, debounceRefreshServiceComponents, 0, [sortParams]);
};
