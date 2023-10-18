import { useDispatch, useStore } from '@hooks';
import { useCallback, useEffect } from 'react';
import {
  cleanupCompareSlice,
  getLeftConfiguration,
  getRightConfiguration,
} from '@store/adcm/hostProvider/configurationGroupSingle/configuration/hostProviderConfigGroupConfigurationsCompareSlice.ts';

export const useHostProviderConfigGroupConfigurationsCompare = () => {
  const dispatch = useDispatch();
  const hostProvider = useStore(({ adcm }) => adcm.hostProvider.hostProvider);
  const hostProviderConfigGroup = useStore((s) => s.adcm.hostProviderConfigGroup.hostProviderConfigGroup);
  const leftConfiguration = useStore(({ adcm }) => adcm.hostProviderConfigGroupConfigurationsCompare.leftConfiguration);
  const rightConfiguration = useStore(
    ({ adcm }) => adcm.hostProviderConfigGroupConfigurationsCompare.rightConfiguration,
  );

  useEffect(
    () => () => {
      dispatch(cleanupCompareSlice());
    },
    [hostProvider, dispatch],
  );

  const getLeftConfig = useCallback(
    (configId: number) => {
      if (hostProvider && hostProviderConfigGroup) {
        dispatch(
          getLeftConfiguration({
            hostProviderId: hostProvider.id,
            configGroupId: hostProviderConfigGroup.id,
            configId,
          }),
        );
      }
    },
    [hostProvider, hostProviderConfigGroup, dispatch],
  );

  const getRightConfig = useCallback(
    (configId: number) => {
      if (hostProvider && hostProviderConfigGroup) {
        dispatch(
          getRightConfiguration({
            hostProviderId: hostProvider.id,
            configGroupId: hostProviderConfigGroup.id,
            configId,
          }),
        );
      }
    },
    [hostProvider, hostProviderConfigGroup, dispatch],
  );

  return {
    leftConfiguration,
    rightConfiguration,
    getLeftConfig,
    getRightConfig,
  };
};
