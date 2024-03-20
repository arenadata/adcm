import { useDispatch, useStore } from '@hooks';
import { useCallback, useEffect } from 'react';
import {
  cleanupCompareSlice,
  getLeftConfiguration,
  getRightConfiguration,
} from '@store/adcm/entityConfiguration/compareSlice';
import { useServiceComponentParams } from '@pages/cluster/service/component/useServiceComponentParams';

export const useComponentPrimaryConfigurationsCompare = () => {
  const dispatch = useDispatch();
  const { clusterId, serviceId, componentId } = useServiceComponentParams();

  const leftConfiguration = useStore(({ adcm }) => adcm.entityConfigurationCompare.leftConfiguration);
  const rightConfiguration = useStore(({ adcm }) => adcm.entityConfigurationCompare.rightConfiguration);

  useEffect(
    () => () => {
      dispatch(cleanupCompareSlice());
    },
    [componentId, dispatch],
  );

  const getLeftConfig = useCallback(
    (configId: number) => {
      componentId &&
        dispatch(
          getLeftConfiguration({
            entityType: 'service-component',
            args: { clusterId, serviceId, componentId, configId },
          }),
        );
    },
    [clusterId, componentId, dispatch, serviceId],
  );

  const getRightConfig = useCallback(
    (configId: number) => {
      componentId &&
        dispatch(
          getRightConfiguration({
            entityType: 'service-component',
            args: { clusterId, serviceId, componentId, configId },
          }),
        );
    },
    [clusterId, componentId, dispatch, serviceId],
  );

  return {
    leftConfiguration,
    rightConfiguration,
    getLeftConfig,
    getRightConfig,
  };
};
