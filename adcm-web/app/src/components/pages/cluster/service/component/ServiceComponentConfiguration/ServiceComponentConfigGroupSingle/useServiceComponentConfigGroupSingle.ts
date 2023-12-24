import { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useDispatch } from '@hooks';
import {
  getServiceComponentConfigGroup,
  cleanupServiceComponentConfigGroup,
} from '@store/adcm/cluster/services/serviceComponents/serviceComponent/configGroupSingle/serviceComponentConfigGroupSingleSlice';

export const useServiceComponentConfigGroupSingle = () => {
  const {
    clusterId: clusterIdFromUrl,
    serviceId: serviceIdFromUrl,
    componentId: componentIdFromUrl,
    configGroupId: configGroupIdFromUrl,
  } = useParams();
  const clusterId = Number(clusterIdFromUrl);
  const serviceId = Number(serviceIdFromUrl);
  const componentId = Number(componentIdFromUrl);
  const configGroupId = Number(configGroupIdFromUrl);
  const dispatch = useDispatch();

  useEffect(() => {
    dispatch(
      getServiceComponentConfigGroup({
        clusterId,
        serviceId,
        componentId,
        configGroupId,
      }),
    );

    return () => {
      dispatch(cleanupServiceComponentConfigGroup());
    };
  }, [dispatch, clusterId, serviceId, componentId, configGroupId]);
};
