import { useDispatch, useStore } from '@hooks';
import { useCallback, useEffect } from 'react';
import {
  cleanupCompareSlice,
  getLeftConfiguration,
  getRightConfiguration,
} from '@store/adcm/entityConfiguration/compareSlice';

export const useServicesPrimaryConfigurationsCompare = () => {
  const dispatch = useDispatch();
  const service = useStore(({ adcm }) => adcm.service.service);
  const leftConfiguration = useStore(({ adcm }) => adcm.entityConfigurationCompare.leftConfiguration);
  const rightConfiguration = useStore(({ adcm }) => adcm.entityConfigurationCompare.rightConfiguration);

  useEffect(
    () => () => {
      dispatch(cleanupCompareSlice());
    },
    [service, dispatch],
  );

  const getLeftConfig = useCallback(
    (configId: number) => {
      service?.id &&
        dispatch(
          getLeftConfiguration({
            entityType: 'service',
            args: { clusterId: service.cluster.id, serviceId: service.id, configId },
          }),
        );
    },
    [service, dispatch],
  );

  const getRightConfig = useCallback(
    (configId: number) => {
      service?.id &&
        dispatch(
          getRightConfiguration({
            entityType: 'service',
            args: { clusterId: service.cluster.id, serviceId: service.id, configId },
          }),
        );
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
