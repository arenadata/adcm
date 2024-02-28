import { useDispatch, useRequestTimer, useDebounce, useStore } from '@hooks';
import { defaultDebounceDelay } from '@constants';
import { useParams } from 'react-router-dom';
import { useEffect } from 'react';
import { cleanupHost, getHost, getHostComponentStates } from '@store/adcm/host/hostSlice';
import { cleanupHostDynamicActions, loadHostsDynamicActions } from '@store/adcm/hosts/hostsDynamicActionsSlice';
import { cleanupBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';
import { isBlockingConcernPresent } from '@utils/concernUtils';

export const useRequestHost = () => {
  const dispatch = useDispatch();
  const { hostId: hostIdFromUrl } = useParams();
  const hostId = Number(hostIdFromUrl);
  const host = useStore(({ adcm }) => adcm.host.host);

  useEffect(() => {
    if (host && !isBlockingConcernPresent(host.concerns)) {
      dispatch(loadHostsDynamicActions([host]));
    }
  }, [host, dispatch, hostId, host?.concerns]);

  useEffect(() => {
    if (host?.cluster) {
      const payload = { hostId: host.id, clusterId: host.cluster.id };
      dispatch(getHostComponentStates(payload));
    }
  }, [dispatch, host]);

  useEffect(() => {
    return () => {
      dispatch(cleanupBreadcrumbs());
      dispatch(cleanupHost());
      dispatch(cleanupHostDynamicActions());
    };
  }, [dispatch]);

  const debounceGetHostData = useDebounce(() => {
    dispatch(getHost(hostId));
  }, defaultDebounceDelay);

  useRequestTimer(debounceGetHostData, () => {}, 0, [hostId]);
};
