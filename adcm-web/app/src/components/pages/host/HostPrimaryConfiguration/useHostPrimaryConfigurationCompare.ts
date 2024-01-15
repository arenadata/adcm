import { useDispatch, useStore } from '@hooks';
import { useCallback, useEffect } from 'react';
import {
  cleanupCompareSlice,
  getLeftConfiguration,
  getRightConfiguration,
} from '@store/adcm/entityConfiguration/compareSlice';
import { useParams } from 'react-router-dom';

export const useHostsPrimaryConfigurationsCompare = () => {
  const dispatch = useDispatch();
  const { hostId: hostIdFromUrl } = useParams();
  const hostId = Number(hostIdFromUrl);
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
          entityType: 'host',
          args: { hostId, configId },
        }),
      );
    },
    [hostId, dispatch],
  );

  const getRightConfig = useCallback(
    (configId: number) => {
      dispatch(
        getRightConfiguration({
          entityType: 'host',
          args: { hostId, configId },
        }),
      );
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
