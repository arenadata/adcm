import { useDispatch, useRequestTimer, useDebounce, useStore } from '@hooks';
import { defaultDebounceDelay } from '@constants';
import { useParams } from 'react-router-dom';
import { useEffect } from 'react';
import { cleanupHost, getHost, getHostComponentStates } from '@store/adcm/host/hostSlice';
import { cleanupHostDynamicActions, loadHostsDynamicActions } from '@store/adcm/hosts/hostsDynamicActionsSlice';
import { cleanupBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';

export const useRequestHost = () => {
  const dispatch = useDispatch();
  const { hostId: hostIdFromUrl } = useParams();
  const hostId = Number(hostIdFromUrl);
  const host = useStore(({ adcm }) => adcm.host.host);
  const hostComponents = useStore(({ adcm }) => adcm.host.relatedData.hostComponents);

  useEffect(() => {
    if (host) {
      dispatch(loadHostsDynamicActions([host]));
    }

    if (host?.cluster) {
      dispatch(getHostComponentStates({ hostId, clusterId: host.cluster.id }));
    }
  }, [host, dispatch, hostComponents, hostId]);

  useEffect(() => {
    return () => {
      dispatch(cleanupBreadcrumbs());
      dispatch(cleanupHost());
      dispatch(cleanupHostDynamicActions());
    };
  }, [dispatch]);

  const debounceGetHostData = useDebounce(() => {
    dispatch(getHost(hostId));
    // TODO: ADCM-4639 uncomment the line below once the host components EP is ready
    // dispatch(getRelatedHostComponents(hostId));
  }, defaultDebounceDelay);

  // eslint-disable-next-line @typescript-eslint/no-empty-function
  useRequestTimer(debounceGetHostData, () => {}, 0, [hostId]);
};
