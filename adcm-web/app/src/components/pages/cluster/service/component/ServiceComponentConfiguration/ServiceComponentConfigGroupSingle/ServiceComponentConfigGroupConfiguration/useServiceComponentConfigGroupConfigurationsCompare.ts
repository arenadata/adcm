import { useDispatch, useStore } from '@hooks';
import { useCallback, useEffect } from 'react';
import {
  getLeftConfiguration,
  getRightConfiguration,
  cleanupCompareSlice,
} from '@store/adcm/cluster/services/serviceComponents/serviceComponent/configGroupSingle/serviceComponentConfigGroupConfigurationsCompareSlice';

export const useServiceComponentConfigGroupConfigurationsCompare = () => {
  const dispatch = useDispatch();
  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);
  const service = useStore(({ adcm }) => adcm.service.service);
  const component = useStore(({ adcm }) => adcm.serviceComponent.serviceComponent);
  const serviceComponentConfigGroup = useStore(
    (s) => s.adcm.serviceComponentConfigGroupSingle.serviceComponentConfigGroup,
  );
  const leftConfiguration = useStore(
    ({ adcm }) => adcm.serviceComponentConfigGroupConfigurationsCompare.leftConfiguration,
  );
  const rightConfiguration = useStore(
    ({ adcm }) => adcm.serviceComponentConfigGroupConfigurationsCompare.rightConfiguration,
  );

  useEffect(
    () => () => {
      dispatch(cleanupCompareSlice());
    },
    [cluster, service, component, dispatch],
  );

  const getLeftConfig = useCallback(
    (configId: number) => {
      if (cluster && service && component && serviceComponentConfigGroup) {
        dispatch(
          getLeftConfiguration({
            clusterId: cluster.id,
            serviceId: service.id,
            componentId: component.id,
            configGroupId: serviceComponentConfigGroup.id,
            configId,
          }),
        );
      }
    },
    [cluster, service, component, serviceComponentConfigGroup, dispatch],
  );

  const getRightConfig = useCallback(
    (configId: number) => {
      if (cluster && service && component && serviceComponentConfigGroup) {
        dispatch(
          getRightConfiguration({
            clusterId: cluster.id,
            serviceId: service.id,
            componentId: component.id,
            configGroupId: serviceComponentConfigGroup.id,
            configId,
          }),
        );
      }
    },
    [cluster, service, component, serviceComponentConfigGroup, dispatch],
  );

  return {
    leftConfiguration,
    rightConfiguration,
    getLeftConfig,
    getRightConfig,
  };
};
