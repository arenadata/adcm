import { useDispatch, useStore } from '@hooks';
import { useCallback, useEffect } from 'react';
import {
  cleanupHostsConfigurationsCompareSlice,
  getLeftConfiguration,
  getRightConfiguration,
} from '@store/adcm/host/configuration/hostsConfigurationCompareSlice';

export const useHostsPrimaryConfigurationsCompare = () => {
  const dispatch = useDispatch();
  const host = useStore(({ adcm }) => adcm.host.host);
  const leftConfiguration = useStore(({ adcm }) => adcm.hostsConfigurationsCompare.leftConfiguration);
  const rightConfiguration = useStore(({ adcm }) => adcm.hostsConfigurationsCompare.rightConfiguration);

  useEffect(
    () => () => {
      dispatch(cleanupHostsConfigurationsCompareSlice());
    },
    [host, dispatch],
  );

  const getLeftConfig = useCallback(
    (configId: number) => {
      host?.id && dispatch(getLeftConfiguration({ hostId: host.id, configId }));
    },
    [host, dispatch],
  );

  const getRightConfig = useCallback(
    (configId: number) => {
      host?.id && dispatch(getRightConfiguration({ hostId: host.id, configId }));
    },
    [host, dispatch],
  );

  return {
    leftConfiguration,
    rightConfiguration,
    getLeftConfig,
    getRightConfig,
  };
};
