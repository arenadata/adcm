import { useDispatch, useRequestTimer, useDebounce, useStore } from '@hooks';
import { defaultDebounceDelay } from '@constants';
import { useParams } from 'react-router-dom';
import { cleanupHostProvider, getHostProvider } from '@store/adcm/hostProviders/hostProviderSlice';
import {
  cleanupHostProviderDynamicActions,
  loadHostProvidersDynamicActions,
} from '@store/adcm/hostProviders/hostProvidersDynamicActionsSlice';
import { useEffect } from 'react';
import { isBlockingConcernPresent } from '@utils/concernUtils';

export const useRequestHostProviderPage = () => {
  const dispatch = useDispatch();
  const { hostproviderId: hostproviderIdFromUrl } = useParams();
  const hostproviderId = Number(hostproviderIdFromUrl);
  const hostProvider = useStore(({ adcm }) => adcm.hostProvider.hostProvider);
  const accessCheckStatus = useStore(({ adcm }) => adcm.hostProvider.accessCheckStatus);

  useEffect(() => {
    if (hostProvider && !isBlockingConcernPresent(hostProvider.concerns)) {
      dispatch(loadHostProvidersDynamicActions([hostProvider]));
    }
  }, [dispatch, hostProvider, hostProvider?.concerns]);

  useEffect(
    () => () => {
      dispatch(cleanupHostProvider());
      dispatch(cleanupHostProviderDynamicActions());
    },
    [dispatch],
  );

  const debounceGetData = useDebounce(() => {
    if (!hostproviderId) return;
    dispatch(getHostProvider(hostproviderId));
  }, defaultDebounceDelay);

  const debounceRefreshData = useDebounce(() => {
    if (!hostproviderId) return;
    dispatch(getHostProvider(hostproviderId));
  }, defaultDebounceDelay);

  useRequestTimer(debounceGetData, debounceRefreshData, 0, []);

  return {
    accessCheckStatus,
  };
};
