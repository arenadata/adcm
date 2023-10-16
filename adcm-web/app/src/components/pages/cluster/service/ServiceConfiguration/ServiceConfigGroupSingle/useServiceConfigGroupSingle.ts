import { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useDispatch } from '@hooks';
import {
  cleanupClusterServiceConfigGroup,
  getClusterServiceConfigGroup,
} from '@store/adcm/cluster/services/configGroupSingle/configGroupSingle';

export const useServiceConfigGroupSingle = () => {
  const { clusterId: clusterIdFromUrl, serviceId: serviceIdFromUrl, configGroupId: configGroupIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);
  const serviceId = Number(serviceIdFromUrl);
  const configGroupId = Number(configGroupIdFromUrl);
  const dispatch = useDispatch();

  useEffect(() => {
    dispatch(
      getClusterServiceConfigGroup({
        clusterId,
        serviceId,
        configGroupId,
      }),
    );

    return () => {
      dispatch(cleanupClusterServiceConfigGroup());
    };
  }, [dispatch, clusterId, serviceId, configGroupId]);
};
