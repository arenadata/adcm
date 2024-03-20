import { useDispatch, useStore } from '@hooks';
import { useCallback, useEffect } from 'react';
import {
  cleanupCompareSlice,
  getLeftConfiguration,
  getRightConfiguration,
} from '@store/adcm/entityConfiguration/compareSlice';

export const useHostProviderPrimaryConfigurationsCompare = () => {
  const dispatch = useDispatch();
  const hostProvider = useStore(({ adcm }) => adcm.hostProvider.hostProvider);
  const leftConfiguration = useStore(({ adcm }) => adcm.entityConfigurationCompare.leftConfiguration);
  const rightConfiguration = useStore(({ adcm }) => adcm.entityConfigurationCompare.rightConfiguration);

  useEffect(
    () => () => {
      dispatch(cleanupCompareSlice());
    },
    [hostProvider, dispatch],
  );

  const getLeftConfig = useCallback(
    (configId: number) => {
      hostProvider?.id &&
        dispatch(
          getLeftConfiguration({
            entityType: 'host-provider',
            args: { hostProviderId: hostProvider.id, configId },
          }),
        );
    },
    [hostProvider, dispatch],
  );

  const getRightConfig = useCallback(
    (configId: number) => {
      hostProvider?.id &&
        dispatch(
          getRightConfiguration({
            entityType: 'host-provider',
            args: { hostProviderId: hostProvider.id, configId },
          }),
        );
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
