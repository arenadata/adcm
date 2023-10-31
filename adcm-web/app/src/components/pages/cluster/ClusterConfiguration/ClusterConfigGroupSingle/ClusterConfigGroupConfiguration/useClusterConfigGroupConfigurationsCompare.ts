import { useDispatch, useStore } from '@hooks';
import { useCallback, useEffect } from 'react';
import {
  cleanupCompareSlice,
  getLeftConfiguration,
  getRightConfiguration,
} from '@store/adcm/cluster/configGroupSingle/configuration/clusterConfigGroupConfigurationsCompareSlice';

export const useClusterConfigGroupConfigurationsCompare = () => {
  const dispatch = useDispatch();
  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);
  const clusterConfigGroup = useStore((s) => s.adcm.clusterConfigGroup.clusterConfigGroup);
  const leftConfiguration = useStore(({ adcm }) => adcm.clusterConfigGroupConfigurationsCompare.leftConfiguration);
  const rightConfiguration = useStore(({ adcm }) => adcm.clusterConfigGroupConfigurationsCompare.rightConfiguration);

  useEffect(
    () => () => {
      dispatch(cleanupCompareSlice());
    },
    [cluster, dispatch],
  );

  const getLeftConfig = useCallback(
    (configId: number) => {
      if (cluster && clusterConfigGroup) {
        dispatch(getLeftConfiguration({ clusterId: cluster.id, configGroupId: clusterConfigGroup.id, configId }));
      }
    },
    [cluster, clusterConfigGroup, dispatch],
  );

  const getRightConfig = useCallback(
    (configId: number) => {
      if (cluster && clusterConfigGroup) {
        dispatch(getRightConfiguration({ clusterId: cluster.id, configGroupId: clusterConfigGroup.id, configId }));
      }
    },
    [cluster, clusterConfigGroup, dispatch],
  );

  return {
    leftConfiguration,
    rightConfiguration,
    getLeftConfig,
    getRightConfig,
  };
};
