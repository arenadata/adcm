import { useDispatch, useStore } from '@hooks';
import { useCallback, useEffect } from 'react';
import {
  cleanupClusterConfigurationsCompareSlice,
  getLeftConfiguration,
  getRightConfiguration,
} from '@store/adcm/cluster/configuration/clusterConfigurationsCompareSlice';

export const useClusterPrimaryConfigurationsCompare = () => {
  const dispatch = useDispatch();
  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);
  const leftConfiguration = useStore(({ adcm }) => adcm.clusterConfigurationsCompare.leftConfiguration);
  const rightConfiguration = useStore(({ adcm }) => adcm.clusterConfigurationsCompare.rightConfiguration);

  useEffect(
    () => () => {
      dispatch(cleanupClusterConfigurationsCompareSlice());
    },
    [cluster, dispatch],
  );

  const getLeftConfig = useCallback(
    (configId: number) => {
      cluster?.id && dispatch(getLeftConfiguration({ clusterId: cluster.id, configId }));
    },
    [cluster, dispatch],
  );

  const getRightConfig = useCallback(
    (configId: number) => {
      cluster?.id && dispatch(getRightConfiguration({ clusterId: cluster.id, configId }));
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
