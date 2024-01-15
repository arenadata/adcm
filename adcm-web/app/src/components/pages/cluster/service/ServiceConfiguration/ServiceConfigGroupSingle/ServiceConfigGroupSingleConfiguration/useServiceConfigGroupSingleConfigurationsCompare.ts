import { useDispatch, useStore } from '@hooks';
import { useCallback, useEffect } from 'react';
import {
  getLeftConfiguration,
  cleanupCompareSlice,
  getRightConfiguration,
} from '@store/adcm/entityConfiguration/compareSlice';

export const useServiceConfigGroupSingleConfigurationsCompare = () => {
  const dispatch = useDispatch();
  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);
  const service = useStore(({ adcm }) => adcm.service.service);
  const serviceConfigGroup = useStore((s) => s.adcm.serviceConfigGroup.serviceConfigGroup);
  const leftConfiguration = useStore(({ adcm }) => adcm.entityConfigurationCompare.leftConfiguration);
  const rightConfiguration = useStore(({ adcm }) => adcm.entityConfigurationCompare.rightConfiguration);

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
            entityType: 'service-config-group',
            args: {
              clusterId: cluster.id,
              serviceId: service.id,
              configGroupId: serviceConfigGroup.id,
              configId,
            },
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
            entityType: 'service-config-group',
            args: {
              clusterId: cluster.id,
              serviceId: service.id,
              configGroupId: serviceConfigGroup.id,
              configId,
            },
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
