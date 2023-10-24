import { defaultDebounceDelay } from '@constants';
import { useDebounce, useDispatch, useRequestTimer, useStore } from '@hooks';
import {
  cleanupServiceComponent,
  getServiceComponent,
} from '@store/adcm/cluster/services/serviceComponents/serviceComponent/serviceComponentSlice';
import {
  cleanupClusterServiceComponentsDynamicActions,
  loadClusterServiceComponentsDynamicActions,
} from '@store/adcm/cluster/services/serviceComponents/serviceComponentsDynamicActionsSlice';
import { useEffect } from 'react';
import { useServiceComponentParams } from '@pages/cluster/service/component/useServiceComponentParams';

export const useRequestServiceComponent = () => {
  const dispatch = useDispatch();
  const component = useStore(({ adcm }) => adcm.serviceComponent.serviceComponent);
  const { clusterId, serviceId, componentId } = useServiceComponentParams();

  useEffect(() => {
    return () => {
      dispatch(cleanupServiceComponent());
      dispatch(cleanupClusterServiceComponentsDynamicActions());
    };
  }, [dispatch, clusterId, serviceId, componentId]);

  useEffect(() => {
    if (component) {
      dispatch(loadClusterServiceComponentsDynamicActions({ components: [component], isHostOwnAction: false }));
    }
  }, [dispatch, component]);

  const debounceGetServiceComponent = useDebounce(() => {
    dispatch(getServiceComponent({ clusterId, serviceId, componentId }));
  }, defaultDebounceDelay);

  // eslint-disable-next-line @typescript-eslint/no-empty-function
  useRequestTimer(debounceGetServiceComponent, () => {}, 0, [clusterId, serviceId, componentId]);
};
