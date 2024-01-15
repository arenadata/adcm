import { useDispatch, useStore } from '@hooks';
import { useCallback, useEffect } from 'react';
import {
  cleanupCompareSlice,
  getLeftConfiguration,
  getRightConfiguration,
} from '@store/adcm/entityConfiguration/compareSlice';

export const useSettingsConfigurationsCompare = () => {
  const dispatch = useDispatch();
  const leftConfiguration = useStore(({ adcm }) => adcm.entityConfigurationCompare.leftConfiguration);
  const rightConfiguration = useStore(({ adcm }) => adcm.entityConfigurationCompare.rightConfiguration);

  useEffect(
    () => () => {
      dispatch(cleanupCompareSlice());
    },
    [dispatch],
  );

  const getLeftConfig = useCallback(
    (configId: number) => {
      dispatch(
        getLeftConfiguration({
          entityType: 'settings',
          args: { configId },
        }),
      );
    },
    [dispatch],
  );

  const getRightConfig = useCallback(
    (configId: number) => {
      dispatch(
        getRightConfiguration({
          entityType: 'settings',
          args: { configId },
        }),
      );
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
