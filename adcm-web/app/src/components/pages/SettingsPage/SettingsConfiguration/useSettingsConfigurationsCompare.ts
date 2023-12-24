import { useDispatch, useStore } from '@hooks';
import { useCallback, useEffect } from 'react';
import {
  cleanupSettingsConfigurationsCompareSlice,
  getLeftConfiguration,
  getRightConfiguration,
} from '@store/adcm/settings/configuration/settingsConfigurationsCompareSlice';

export const useSettingsConfigurationsCompare = () => {
  const dispatch = useDispatch();
  const leftConfiguration = useStore(({ adcm }) => adcm.settingsConfigurationsCompare.leftConfiguration);
  const rightConfiguration = useStore(({ adcm }) => adcm.settingsConfigurationsCompare.rightConfiguration);

  useEffect(
    () => () => {
      dispatch(cleanupSettingsConfigurationsCompareSlice());
    },
    [dispatch],
  );

  const getLeftConfig = useCallback(
    (configId: number) => {
      dispatch(getLeftConfiguration({ configId }));
    },
    [dispatch],
  );

  const getRightConfig = useCallback(
    (configId: number) => {
      dispatch(getRightConfiguration({ configId }));
    },
    [dispatch],
  );

  return {
    leftConfiguration,
    rightConfiguration,
    getLeftConfig,
    getRightConfig,
  };
};
