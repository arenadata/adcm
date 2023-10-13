import { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useDispatch } from '@hooks';
import {
  cleanupClusterConfigGroup,
  getClusterConfigGroup,
} from '@store/adcm/cluster/configGroupSingle/clusterConfigGroup';

export const useClusterConfigGroupSingle = () => {
  const { clusterId: clusterIdFromUrl, configGroupId: configGroupIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);
  const configGroupId = Number(configGroupIdFromUrl);
  const dispatch = useDispatch();

  useEffect(() => {
    dispatch(
      getClusterConfigGroup({
        clusterId,
        configGroupId,
      }),
    );
    return () => {
      dispatch(cleanupClusterConfigGroup());
    };
  }, [dispatch, clusterId, configGroupId]);
};
