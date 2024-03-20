import { useDispatch, useStore } from '@hooks';
import { useCallback, useEffect } from 'react';
import {
  cleanupCompareSlice,
  getLeftConfiguration,
  getRightConfiguration,
} from '@store/adcm/entityConfiguration/compareSlice';

export const useClusterConfigGroupConfigurationsCompare = () => {
  const dispatch = useDispatch();
  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);
  const clusterConfigGroup = useStore((s) => s.adcm.clusterConfigGroup.clusterConfigGroup);
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
      if (cluster && clusterConfigGroup) {
        dispatch(
          getLeftConfiguration({
            entityType: 'cluster-config-group',
            args: { clusterId: cluster.id, configGroupId: clusterConfigGroup.id, configId },
          }),
        );
      }
    },
    [cluster, clusterConfigGroup, dispatch],
  );

  const getRightConfig = useCallback(
    (configId: number) => {
      if (cluster && clusterConfigGroup) {
        dispatch(
          getRightConfiguration({
            entityType: 'cluster-config-group',
            args: { clusterId: cluster.id, configGroupId: clusterConfigGroup.id, configId },
          }),
        );
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
