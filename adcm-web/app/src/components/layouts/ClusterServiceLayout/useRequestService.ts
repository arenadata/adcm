import { useDispatch, useRequestTimer, useDebounce } from '@hooks';
import { defaultDebounceDelay } from '@constants';
import { useParams } from 'react-router-dom';
import { getService } from '@store/adcm/services/serviceSlice';

export const useRequestService = () => {
  const dispatch = useDispatch();
  const { clusterId: clusterIdFromUrl, serviceId: serviceIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);
  const serviceId = Number(serviceIdFromUrl);

  const debounceGetCluster = useDebounce(() => {
    if (clusterId && serviceId) {
      dispatch(
        getService({
          clusterId,
          serviceId,
        }),
      );
    }
  }, defaultDebounceDelay);

  // eslint-disable-next-line @typescript-eslint/no-empty-function
  useRequestTimer(debounceGetCluster, () => {}, 0, [clusterId, serviceId]);
};
