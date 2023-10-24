import { useDispatch, useStore } from '@hooks';
import { useCallback, useEffect } from 'react';
import {
  cleanupHostProviderConfigurationsCompareSlice,
  getLeftConfiguration,
  getRightConfiguration,
} from '@store/adcm/hostProvider/configuration/hostProviderConfigurationsCompareSlice';

export const useHostProviderPrimaryConfigurationsCompare = () => {
  const dispatch = useDispatch();
  const hostProvider = useStore(({ adcm }) => adcm.hostProvider.hostProvider);
  const leftConfiguration = useStore(({ adcm }) => adcm.hostProviderConfigurationsCompare.leftConfiguration);
  const rightConfiguration = useStore(({ adcm }) => adcm.hostProviderConfigurationsCompare.rightConfiguration);

  useEffect(
    () => () => {
      dispatch(cleanupHostProviderConfigurationsCompareSlice());
    },
    [hostProvider, dispatch],
  );

  const getLeftConfig = useCallback(
    (configId: number) => {
      hostProvider?.id && dispatch(getLeftConfiguration({ hostProviderId: hostProvider.id, configId }));
    },
    [hostProvider, dispatch],
  );

  const getRightConfig = useCallback(
    (configId: number) => {
      hostProvider?.id && dispatch(getRightConfiguration({ hostProviderId: hostProvider.id, configId }));
    },
    [hostProvider, dispatch],
  );

  return {
    leftConfiguration,
    rightConfiguration,
    getLeftConfig,
    getRightConfig,
  };
};
