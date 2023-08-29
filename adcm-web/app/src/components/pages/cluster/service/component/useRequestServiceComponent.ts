import { defaultDebounceDelay } from '@constants';
import { useDebounce, useDispatch, useRequestTimer } from '@hooks';
import {
  cleanupServiceComponent,
  getServiceComponent,
} from '@store/adcm/cluster/services/serviceComponents/serviceComponent/serviceComponentSlice';
import { useEffect } from 'react';
import { useParams } from 'react-router-dom';

export const useRequestServiceComponent = () => {
  const dispatch = useDispatch();
  const { clusterId: clusterIdFromUrl, serviceId: serviceIdFromUrl, componentId: componentIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);
  const serviceId = Number(serviceIdFromUrl);
  const componentId = Number(componentIdFromUrl);

  useEffect(() => {
    return () => {
      dispatch(cleanupServiceComponent());
    };
  }, [dispatch, clusterId, serviceId, componentId]);

  const debounceGetServiceComponent = useDebounce(() => {
    dispatch(getServiceComponent({ clusterId, serviceId, componentId }));
  }, defaultDebounceDelay);

  // eslint-disable-next-line @typescript-eslint/no-empty-function
  useRequestTimer(debounceGetServiceComponent, () => {}, 0, [clusterId, serviceId, componentId]);
};
