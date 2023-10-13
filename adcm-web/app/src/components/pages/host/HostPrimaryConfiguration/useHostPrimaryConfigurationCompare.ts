import { useDispatch, useStore } from '@hooks';
import { useCallback, useEffect } from 'react';
import {
  cleanupHostsConfigurationsCompareSlice,
  getLeftConfiguration,
  getRightConfiguration,
} from '@store/adcm/host/configuration/hostsConfigurationCompareSlice';
import { useParams } from 'react-router-dom';

export const useHostsPrimaryConfigurationsCompare = () => {
  const dispatch = useDispatch();
  const { hostId: hostIdFromUrl } = useParams();
  const hostId = Number(hostIdFromUrl);
  const leftConfiguration = useStore(({ adcm }) => adcm.hostsConfigurationsCompare.leftConfiguration);
  const rightConfiguration = useStore(({ adcm }) => adcm.hostsConfigurationsCompare.rightConfiguration);

  useEffect(
    () => () => {
      dispatch(cleanupHostsConfigurationsCompareSlice());
    },
    [dispatch],
  );

  const getLeftConfig = useCallback(
    (configId: number) => {
      dispatch(getLeftConfiguration({ hostId, configId }));
    },
    [hostId, dispatch],
  );

  const getRightConfig = useCallback(
    (configId: number) => {
      dispatch(getRightConfiguration({ hostId, configId }));
    },
    [hostId, dispatch],
  );

  return {
    leftConfiguration,
    rightConfiguration,
    getLeftConfig,
    getRightConfig,
  };
};
