import { useDispatch, useRequestTimer, useDebounce } from '@hooks';
import { defaultDebounceDelay } from '@constants';
import { useParams } from 'react-router-dom';
import { useEffect } from 'react';
import {
  cleanupClusterHost,
  getClusterHostComponentsStates,
  getRelatedClusterHostComponents,
} from '@store/adcm/cluster/hosts/host/clusterHostSlice';
import { getClusterHost } from '@store/adcm/cluster/hosts/host/clusterHostSlice';

export const useRequestClusterHost = () => {
  const dispatch = useDispatch();
  const { clusterId: clusterIdFromUrl, hostId: hostIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);
  const hostId = Number(hostIdFromUrl);

  useEffect(() => {
    return () => {
      dispatch(cleanupClusterHost());
    };
  }, [dispatch]);

  const debounceGetClusterHostData = useDebounce(() => {
    if (clusterId && hostId) {
      const payload = { clusterId, hostId };
      dispatch(getClusterHost(payload));
      dispatch(getRelatedClusterHostComponents(payload));
      dispatch(getClusterHostComponentsStates(payload));
    }
  }, defaultDebounceDelay);

  // eslint-disable-next-line @typescript-eslint/no-empty-function
  useRequestTimer(debounceGetClusterHostData, () => {}, 0, [clusterId, hostId]);
};
