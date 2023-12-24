import { useDispatch, useStore } from '@hooks';
import { useCallback, useEffect } from 'react';
import {
  getLeftConfiguration,
  cleanupCompareSlice,
  getRightConfiguration,
} from '@store/adcm/cluster/services/configGroupSingle/configuration/serviceConfigGroupConfigurationsCompareSlice';

export const useServiceConfigGroupSingleConfigurationsCompare = () => {
  const dispatch = useDispatch();
  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);
  const service = useStore(({ adcm }) => adcm.service.service);
  const serviceConfigGroup = useStore((s) => s.adcm.serviceConfigGroup.serviceConfigGroup);
  const leftConfiguration = useStore(({ adcm }) => adcm.serviceConfigGroupConfigurationsCompare.leftConfiguration);
  const rightConfiguration = useStore(({ adcm }) => adcm.serviceConfigGroupConfigurationsCompare.rightConfiguration);

  useEffect(
    () => () => {
      dispatch(cleanupCompareSlice());
    },
    [cluster, service, dispatch],
  );

  const getLeftConfig = useCallback(
    (configId: number) => {
      if (cluster && service && serviceConfigGroup) {
        dispatch(
          getLeftConfiguration({
            clusterId: cluster.id,
            serviceId: service.id,
            configGroupId: serviceConfigGroup.id,
            configId,
          }),
        );
      }
    },
    [cluster, service, serviceConfigGroup, dispatch],
  );

  const getRightConfig = useCallback(
    (configId: number) => {
      if (cluster && service && serviceConfigGroup) {
        dispatch(
          getRightConfiguration({
            clusterId: cluster.id,
            serviceId: service.id,
            configGroupId: serviceConfigGroup.id,
            configId,
          }),
        );
      }
    },
    [cluster, service, serviceConfigGroup, dispatch],
  );

  return {
    leftConfiguration,
    rightConfiguration,
    getLeftConfig,
    getRightConfig,
  };
};
