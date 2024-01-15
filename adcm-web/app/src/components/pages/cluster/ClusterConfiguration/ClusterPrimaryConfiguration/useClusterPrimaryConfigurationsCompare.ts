import { useDispatch, useStore } from '@hooks';
import { useCallback, useEffect } from 'react';
import {
  cleanupCompareSlice,
  getLeftConfiguration,
  getRightConfiguration,
} from '@store/adcm/entityConfiguration/compareSlice';

export const useClusterPrimaryConfigurationsCompare = () => {
  const dispatch = useDispatch();
  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);
  const leftConfiguration = useStore(({ adcm }) => adcm.entityConfigurationCompare.leftConfiguration);
  const rightConfiguration = useStore(({ adcm }) => adcm.entityConfigurationCompare.rightConfiguration);

  useEffect(
    () => () => {
      dispatch(cleanupCompareSlice());
    },
    [cluster, dispatch],
  );

  const getLeftConfig = useCallback(
    (configId: number) => {
      cluster?.id &&
        dispatch(
          getLeftConfiguration({
            entityType: 'cluster',
            args: { clusterId: cluster.id, configId },
          }),
        );
    },
    [cluster, dispatch],
  );

  const getRightConfig = useCallback(
    (configId: number) => {
      cluster?.id &&
        dispatch(
          getRightConfiguration({
            entityType: 'cluster',
            args: { clusterId: cluster.id, configId },
          }),
        );
    },
    [cluster, dispatch],
  );

  return {
    leftConfiguration,
    rightConfiguration,
    getLeftConfig,
    getRightConfig,
  };
};
