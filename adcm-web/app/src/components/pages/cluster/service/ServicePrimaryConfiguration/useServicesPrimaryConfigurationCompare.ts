import { useDispatch, useStore } from '@hooks';
import { useCallback, useEffect } from 'react';
import {
  cleanupClusterServicesConfigurationsCompareSlice,
  getLeftConfiguration,
  getRightConfiguration,
} from '@store/adcm/cluster/services/servicesPrymaryConfiguration/servicesConfigurationsCompareSlice.ts';

export const useServicesPrimaryConfigurationsCompare = () => {
  const dispatch = useDispatch();
  const service = useStore(({ adcm }) => adcm.service.service);
  const leftConfiguration = useStore(({ adcm }) => adcm.clusterServicesConfigurationsCompare.leftConfiguration);
  const rightConfiguration = useStore(({ adcm }) => adcm.clusterServicesConfigurationsCompare.rightConfiguration);

  useEffect(
    () => () => {
      dispatch(cleanupClusterServicesConfigurationsCompareSlice());
    },
    [service, dispatch],
  );

  const getLeftConfig = useCallback(
    (configId: number) => {
      service?.id && dispatch(getLeftConfiguration({ clusterId: service.cluster.id, serviceId: service.id, configId }));
    },
    [service, dispatch],
  );

  const getRightConfig = useCallback(
    (configId: number) => {
      service?.id &&
        dispatch(getRightConfiguration({ clusterId: service.cluster.id, serviceId: service.id, configId }));
    },
    [service, dispatch],
  );

  return {
    leftConfiguration,
    rightConfiguration,
    getLeftConfig,
    getRightConfig,
  };
};
