import { useDispatch, useStore } from '@hooks';
import { useCallback, useEffect } from 'react';
import {
  cleanupServiceComponentConfigurationsCompareSlice,
  getLeftConfiguration,
  getRightConfiguration,
} from '@store/adcm/cluster/services/serviceComponents/serviceComponent/configuration/serviceComponentConfigurationsCompareSlice';
import { useServiceComponentParams } from '@pages/cluster/service/component/useServiceComponentParams';

export const useComponentPrimaryConfigurationsCompare = () => {
  const dispatch = useDispatch();
  const { clusterId, serviceId, componentId } = useServiceComponentParams();

  const leftConfiguration = useStore(({ adcm }) => adcm.serviceComponentsConfigurationsCompare.leftConfiguration);
  const rightConfiguration = useStore(({ adcm }) => adcm.serviceComponentsConfigurationsCompare.rightConfiguration);

  useEffect(
    () => () => {
      dispatch(cleanupServiceComponentConfigurationsCompareSlice());
    },
    [componentId, dispatch],
  );

  const getLeftConfig = useCallback(
    (configId: number) => {
      componentId && dispatch(getLeftConfiguration({ clusterId, serviceId, componentId, configId }));
    },
    [clusterId, componentId, dispatch, serviceId],
  );

  const getRightConfig = useCallback(
    (configId: number) => {
      componentId && dispatch(getRightConfiguration({ clusterId, serviceId, componentId, configId }));
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
